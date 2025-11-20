# testgenflow (v0)

Minimal pipeline that generates a pytest module, sends it to the TestGenEval/SWE-bench runner via HTTP (`POST /runner`), and stores the response. The runner is served by the Flask app in `src/runner/server.py`.

## Quick start

1. `pip install -e .` (or `pip install -r requirements.txt` if you export one)
2. Start the runner server in `src/runner`. See `src/runner/README.md` for full details.
3. `python -m src.pipeline.run_once --repo django/django --version 4.1 --code-file django/views/static.py`

Artifacts and metrics land in `artifacts/runs/<run_id>/`.

## Offline usage (no internet)

- Set dry run: `export DRY_RUN=1` (or keep `runner_url: dryrun://runner` in configs).
- Skip installs: just run `pytest -q` and the pipeline.
- Optional runtime validation (requires pydantic): `export ENABLE_VALIDATION=1`

## Using OpenAI (LLM Enhancer)

Install the OpenAI client:

```bash
pip install openai
```

Export your key (no .env required, but you can source one if you like):

```bash
export OPENAI_API_KEY="sk-...your-key..."
unset DRY_LLM    # ensure LLM usage is enabled
export LLM_COLLECT_LOGPROBS=true  # request token logprobs where the model supports them
```

Run iterate with OpenAI:

```bash
python -m src.pipeline.iterate --repo django/django --version 4.1 --code-file django/views/static.py --max-iters 2
```

Offline fallback (no network):

```bash
export DRY_RUN=1
export DRY_LLM=1
python -m src.pipeline.iterate --repo django/django --version 4.1 --code-file django/views/static.py --max-iters 2
```

## Quick checks

```bash
# OpenAI path
pip install openai
export OPENAI_API_KEY="sk-..."; unset DRY_LLM
python -m src.pipeline.iterate --repo django/django --version 4.1 --code-file django/views/static.py --max-iters 1

# Offline path
export DRY_RUN=1; export DRY_LLM=1
python -m src.pipeline.iterate --repo django/django --version 4.1 --code-file django/views/static.py --max-iters 1
```

## Orchestrator (v2 backbone)

Offline (synthetic Runner + rule-based LLM):

```bash
export DRY_RUN=1
export DRY_LLM=1
python -m src.orchestrator.engine --repo django/django --version 4.1 --code-file django/views/static.py --max-iters 2
```

With OpenAI:

```bash
pip install openai
export OPENAI_API_KEY="sk-..."; unset DRY_LLM
python -m src.orchestrator.engine --repo django/django --version 4.1 --code-file django/views/static.py --max-iters 2
```

Context miner reads the local file (default `--repo-root=.`) to build a compact ContextPack passed to the Generator. Artifacts per attempt are in `artifacts/runs/<run_id>/`.

### Static analysis (pylint / mypy)

Static checks (syntax, complexity, basic lint) are always run when `static_analysis.enable: true` in `configs/default.yaml`. To enable external lint/type tools:

```bash
pip install pylint mypy
```

With `pylint` and `mypy` on `PATH`, each `attempt_X.static.json` and reliability block will include real lint issue counts instead of `"available": false`.

### Batch runs on TestGenEval Lite (django/django)

To run the orchestrator over a subset of `kjain14/testgenevallite` for `django/django` and collect metrics:

```bash
# 1. Run orchestrator on first 5 django/django rows from the test split
python scripts/run_django_batch.py --split test --limit 5 --max-iters 2

# 2. Aggregate attempt-level and run-level stats (coverage, mutation, LLM cost, etc.)
python scripts/collect_run_stats.py \
  --runs-dir artifacts/runs \
  --attempt-csv artifacts/attempt_stats.csv \
  --run-csv artifacts/run_summary_stats.csv \
  --coverage-plot artifacts/run_coverage.png

# 3. Re-run with dataset metadata to attach baseline coverage from TestGenEval Lite
python scripts/collect_run_stats.py \
  --runs-dir artifacts/runs \
  --dataset kjain14/testgenevallite \
  --split test

# 4. Summarize how often the orchestrator beats the dataset baselines (first/last/last_minus_one)
python scripts/analyze_run_stats.py \
  --input artifacts/run_summary_stats.csv \
  --output artifacts/run_vs_baseline.csv

# 5. Export per-attempt metrics (entropy, avg_logprob, mutation_score) vs. baselines
python scripts/analyze_attempt_stats.py \
  --attempt-csv artifacts/attempt_stats.csv \
  --output artifacts/attempt_vs_baseline.csv
```

The `run_vs_baseline.csv` file gives one row per run with max coverage and whether it beat the dataset baselines; `attempt_vs_baseline.csv` gives one row per attempt with coverage, mutation score, and any available LLM entropy/logprob summaries.

## Live dashboard (Streamlit)

Visualize runs, LLM calls, coverage/mutation trends, lint findings, and router events in real time:

```bash
pip install streamlit
streamlit run streamlit_app.py
```

- Uses `artifacts/runs/` by default (override with `TESTGENEVAL_RUNS_DIR=/path/to/runs`).
- Sidebar lets you filter run types, adjust refresh cadence, and pick a focused run.
- Each iteration shows requests/responses, reliability scores, static analysis, LLM entropy/logprobs, and test source.
- The “LLM feed” tab surfaces the most recent completions across all runs for quick health checks.

## TestGenEval Integration

- Clone the dataset locally (kept out of version control):

  ```bash
  mkdir -p external
  git clone https://github.com/facebookresearch/testgeneval.git external/testgeneval
  ```

- Follow `src/runner/README.md` to provision the conda env, patch/pull Docker images, and verify `python src/runner/test.py` works.
- Launch the runner Flask server (see Quick start). This exposes the HTTP API consumed by the pipeline/orchestrator.
- Run the orchestrator against any TestGenEval task once the runner server is up. Responses and critiques appear under `artifacts/runs/<run_id>/`.
