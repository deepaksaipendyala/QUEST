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

## TestGenEval Integration

- Clone the dataset locally (kept out of version control):

  ```bash
  mkdir -p external
  git clone https://github.com/facebookresearch/testgeneval.git external/testgeneval
  ```

- Follow `src/runner/README.md` to provision the conda env, patch/pull Docker images, and verify `python src/runner/test.py` works.
- Launch the runner Flask server (see Quick start). This exposes the HTTP API consumed by the pipeline/orchestrator.
- Run the orchestrator against any TestGenEval task once the runner server is up. Responses and critiques appear under `artifacts/runs/<run_id>/`.
