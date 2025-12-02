# QUEST (Quality-Enhanced Supervised Testing)

A multi-agent pipeline that drafts test suites, executes them, analyzes coverage and reliability, and iteratively refines tests using LLMs.

## Setup
1. **Project venv** – install main deps.
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```
2. **Runner conda env** - Run these commands from `src/runner` directory in a new terminal.
   ```bash
   conda env create -f environment-mac.yaml -n testgeneval
   conda activate testgeneval
   conda run -n testgeneval python -m pip install --upgrade "datasets>=2.19.0"
  
   ```
4. **Environment variables**
   ```bash
   export PYTHONPATH="$(pwd)/gitrepo:${PYTHONPATH}" # Can also replace pwd with absolute path
   export SWEBENCH_DOCKER_FORK_DIR="$(pwd)/gitrepo" # Can also replace pwd with absolute path
   export OPENAI_API_KEY="sk-..."
   export LLM_COLLECT_LOGPROBS=true
   ```

## Starting the Runner
1. **Start (script)**
   ```bash
   ./start_runner.sh
   ```
2. **Start (manual)**.
   ```bash
   cd src/runner
   export PYTHONPATH="$(pwd)/../../gitrepo:${PYTHONPATH}"
   export SWEBENCH_DOCKER_FORK_DIR="$(pwd)/../../gitrepo"
   conda run -n testgeneval python server.py
   ```

## Core Pipeline Commands
All commands expect the runner at `http://localhost:3000/runner` (see `configs/default.yaml`). Activate `.venv` first.

| Goal | Command | Notes |
| --- | --- | --- |
| Single attempt (baseline) | `python -m src.pipeline.run_once --repo django/django --version 4.1 --code-file django/views/static.py` | Fast covering smoke test |
| Iterative generator + enhancer | `python -m src.pipeline.iterate --repo django/django --version 4.1 --code-file django/views/static.py --max-iters 2` | Requires LLM unless `DRY_LLM=1` |
| Full orchestrator loop | `python -m src.orchestrator.engine --repo django/django --version 4.1 --code-file django/views/static.py --max-iters 3` | Runs generator → supervisor → enhancer with routing |

- Note: Above pipeline commands only run on a single row from the dataset. To run on multiple rows, you can make use of the helper script `scripts/run_django_batch.py` which will iterate over multiple code files in the Django dataset.

## Configuration
- Many configuration options are available in `configs/default.yaml`
- Mutation can be skipped with `export SKIP_MUTATION=true`; keep it `false` for research-quality runs so supervisor + router use score deltas.

## Live Dashboard
```bash
source .venv/bin/activate
pip install streamlit
TESTGENEVAL_RUNS_DIR=/path/to/runs streamlit run streamlit_app.py
```
- Shows latest LLM calls, reliability labels, coverage/mutation trends, router decisions, and static analysis warnings.

## Artifact Layout
```
artifacts/runs/run_<ts>_<id>/
├── context.json            # mined repo slice
├── run_summary.json        # cost, coverage, mutation, tokens
├── events.log              # orchestrator timeline
├── attempt_0/…attempt_N/   # request, response, test_src.py, static.json,
│                           # reliability (pre/post), execution metrics, critique
└── streamlit_cache/…       # dashboard scratch data (optional)
```
