## QUEST Runner + UI Setup Guide

This document is meant to get teammates productive on the TestGenEval runner + QUEST orchestrator stack. Follow the sections in order the first time. After that you can use it as a checklist.

---

### 0. Prerequisites

- macOS 14+ (Apple Silicon works) with at least 80 GB free disk space.
- **Docker Desktop** installed and running (`docker info` should succeed). The TestGenEval runner spawns containers per task.
- **Python 3.10** on the host (the repo uses a `.venv`).
- **conda/miniconda** for the runner sandbox.
- An OpenAI key if you want live LLM refinement (`export OPENAI_API_KEY=...`). Dry mode works without it.

---

### 1. Clone repos & base layout

```bash
git clone git@github.com:<org>/CSC591-GenerativeAIforSE_TestgenEval-runner-rewrite.git
cd CSC591-GenerativeAIforSE_TestgenEval-runner-rewrite

# The SWE-bench/TestGenEval fork lives in ./gitrepo
git clone https://github.com/facebookresearch/testgeneval.git gitrepo
cd gitrepo && git checkout 67ea3ff37643b3078413d6e4fadaae00ce8d9e5d && cd ..
```

If we drop patch files in the repo root (e.g. the ones provided by SWE-bench), apply them before continuing:

```bash
cp patches/*.patch gitrepo/
cd gitrepo && git apply *.patch && rm *.patch && cd ..
```

---

### 2. Project virtual environment (`.venv`)

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .

# Optional extras for the dashboard/LLM
pip install streamlit openai pylint mypy
```

Capture the exact dependency set so teammates can replicate it:

```bash
pip freeze > requirements.lock
```

Keep the `.venv` active whenever you run `python -m src.*` or `streamlit`.

---

### 3. Runner conda environment (TestGenEval sandbox)

The runner invokes SWE-bench workloads inside Docker, but it expects its own conda env (`testgeneval`) for orchestration scripts.

```bash
conda env create -f environment-mac.yaml  # provided by SWE-bench
conda run -n testgeneval python -m pip install --upgrade "datasets>=2.19.0"
```

Environment variables required by the runner:

```bash
export PYTHONPATH="$PWD/gitrepo:$PYTHONPATH"
export SWEBENCH_DOCKER_FORK_DIR="$PWD/gitrepo"
```

(Add the two exports to your shell profile so they persist.)

Freeze the runner env as well for auditability:

```bash
conda run -n testgeneval python -m pip freeze > runner-requirements.lock
```

---

### 4. Docker baseline

1. Start Docker Desktop and ensure `docker ps` works.
2. Pull the base images once (they’re referenced by SWE-bench configs):

```bash
docker pull ghcr.io/swe-bench/swe-bench-runner:latest
docker pull ghcr.io/swe-bench/swe-bench-gold:latest
```

3. (Optional) prune old images/containers before large batches: `docker system prune -f`.

---

### 5. Start the TestGenEval runner server

There are two ways:

**A. Using the helper script**

```bash
# From repo root
./start_runner.sh
```

The script exports `PYTHONPATH`, `SWEBENCH_DOCKER_FORK_DIR`, and `SKIP_MUTATION=false`, then invokes the Flask server under the `testgeneval` conda env.

**B. Manual command**

```bash
cd src/runner
PYTHONPATH="$PWD/../../gitrepo" \
SWEBENCH_DOCKER_FORK_DIR="$PWD/../../gitrepo" \
conda run -n testgeneval python server.py
```

The server listens on `http://localhost:3000/runner`. Use `./stop_runner.sh` (or `pkill -f server.py`) to cleanly stop it.

> Verify with `curl -X POST http://localhost:3000/runner -d '{}'` (should return a JSON error instead of timing out).

---

### 6. Running the QUEST orchestrator/pipeline

With the runner online and `.venv` activated:

```bash
# Single pass baseline
python -m src.pipeline.run_once --repo django/django --version 4.1 --code-file django/views/static.py

# Iterative generator (dry LLM)
export DRY_LLM=1   # drop this if OPENAI_API_KEY is set and you want live calls
python -m src.pipeline.iterate --repo django/django --version 4.1 --code-file django/views/static.py --max-iters 3

# Full orchestrator (generator + supervisor + enhancer)
python -m src.orchestrator.engine --repo django/django --version 4.1 --code-file django/views/static.py --max-iters 4
```

Artifacts land under `artifacts/runs/<run_id>`:

- `attempt_X.request/response` – payloads sent to the runner.
- `attempt_X.test_src.py` – generated tests.
- `attempt_X.static.json` – lint/type results.
- `attempt_X.pre/post_reliability.json` – uncertainty + outcome labels.
- `attempt_X.metrics.json` – durations/costs per stage.
- `events.log` – router decisions and runner status.

---

### 7. Streamlit live dashboard

From the project `.venv`:

```bash
streamlit run streamlit_app.py
```

Key tips:

- Default data root is `artifacts/runs/`. To point at shared storage: `TESTGENEVAL_RUNS_DIR=/path/to/runs streamlit run streamlit_app.py`.
- Each iteration expander now shows:
  - Generator/Enhancer → Runner requests & code
  - Supervisor critique + instructions handed to the next enhancer
  - Reliability (pre/post), static analysis, lint counts
  - LLM metadata (entropy, tokens, cost) when not in dry mode
- Tabs provide coverage/mutation trend, reliability snapshot table, LLM feed, and the raw event log.

---

### 8. Capturing environment state for peers

Whenever you change dependencies:

```bash
# Project venv
source .venv/bin/activate
pip install <new-package>
pip freeze > requirements.lock

# Runner conda env
conda run -n testgeneval python -m pip install <new-package>
conda run -n testgeneval python -m pip freeze > runner-requirements.lock
```

Commit the lock files (they are small) so others can recreate the exact setup by running:

```bash
pip install -r requirements.lock
conda run -n testgeneval python -m pip install -r runner-requirements.lock
```

---

### 9. Troubleshooting checklist

- **Runner won’t start / ModuleNotFoundError** – confirm `PYTHONPATH`/`SWEBENCH_DOCKER_FORK_DIR` point to the `gitrepo` checkout and that conda env `testgeneval` is active.
- **“Address already in use” on port 3000** – run `lsof -i :3000` and kill the old server (or use `./stop_runner.sh`).
- **Mutation score stays `-1.0`** – ensure `SKIP_MUTATION=false` in `start_runner.sh`, restart the runner, and let Docker finish pulling the `cosmic-ray` images.
- **LLM entropy is `null`** – you’re in dry mode (`DRY_LLM=1`). Export a real `OPENAI_API_KEY` and unset `DRY_LLM`.
- **Streamlit not showing new runs** – refresh (`R` hotkey) or confirm `TESTGENEVAL_RUNS_DIR` matches the artifact location.

---

### 10. Reference commands

```bash
# Restart everything quickly
./stop_runner.sh || true
./start_runner.sh &
source .venv/bin/activate
python -m src.orchestrator.engine --repo django/django --version 4.1 --code-file django/views/static.py --max-iters 3

# Export artifacts for analysis
python -m src.scripts.export_runs --limit 5 --format csv --output /tmp/latest.csv
```

Keep Docker running, keep both environments (`.venv` + `testgeneval`) healthy, and always capture `pip freeze` after touching dependencies so the rest of the team stays in sync.

