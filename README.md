# testgenflow (v0)
Minimal pipeline that generates a pytest module, sends it to an external Runner (`POST /runner`), and stores the response.

## Quick start
1) `pip install -e .` (or `pip install -r requirements.txt` if you export one)
2) Ensure Runner is available at `$RUNNER_URL` (default `http://localhost:3000/runner`)
3) `python -m src.pipeline.run_once --repo encode/httpx --version 0.24.0 --code-file httpx/_client.py`

Artifacts and metrics land in `artifacts/runs/<run_id>/`.

## Offline usage (no internet)
- Set dry run: `export DRY_RUN=1` (or keep `runner_url: dryrun://runner` in configs).
- Skip installs: just run `pytest -q` and the pipeline.
- Optional runtime validation (requires pydantic): `export ENABLE_VALIDATION=1`

## Using OpenAI (LLM Enhancer)
Install the OpenAI client:
```
pip install openai
```

Export your key (no .env required, but you can source one if you like):
```
export OPENAI_API_KEY="sk-...your-key..."
unset DRY_LLM    # ensure LLM usage is enabled
```

Run iterate with OpenAI:
```
python -m src.pipeline.iterate --repo encode/httpx --version 0.24.0 --code-file httpx/_client.py --max-iters 2
```

Offline fallback (no network):
```
export DRY_RUN=1
export DRY_LLM=1
python -m src.pipeline.iterate --repo encode/httpx --version 0.24.0 --code-file httpx/_client.py --max-iters 2
```

## Quick checks
```
# OpenAI path
pip install openai
export OPENAI_API_KEY="sk-..."; unset DRY_LLM
python -m src.pipeline.iterate --repo encode/httpx --version 0.24.0 --code-file httpx/_client.py --max-iters 1

# Offline path
export DRY_RUN=1; export DRY_LLM=1
python -m src.pipeline.iterate --repo encode/httpx --version 0.24.0 --code-file httpx/_client.py --max-iters 1
```

## Orchestrator (v2 backbone)
Offline (synthetic Runner + rule-based LLM):
```
export DRY_RUN=1
export DRY_LLM=1
python -m src.orchestrator.engine --repo encode/httpx --version 0.24.0 --code-file httpx/_client.py --max-iters 2
```

With OpenAI:
```
pip install openai
export OPENAI_API_KEY="sk-..."; unset DRY_LLM
python -m src.orchestrator.engine --repo encode/httpx --version 0.24.0 --code-file httpx/_client.py --max-iters 2
```

Context miner reads the local file (default --repo-root=.) to build a compact ContextPack passed to the Generator.
Artifacts per attempt are in artifacts/runs/<run_id>/.
