# TestGenFlow Setup Summary

## Completed Setup Steps

1. **TestGenEval Repository**: Cloned and set up
   - Repository cloned to `gitrepo/`
   - Checked out commit: `67ea3ff37643b3078413d6e4fadaae00ce8d9e5d`
   - Applied patches from `src/runner/changes.patch`

2. **Conda Environment**: Created and configured
   - Environment name: `testgeneval`
   - Created from `src/runner/environment-mac.yaml`
   - Upgraded datasets to >=2.19.0
   - Python version: 3.9

3. **Main Project Dependencies**: Installed via venv
   - Created virtual environment in `.venv/`
   - Installed project in editable mode: `pip install -e .`
   - Dependencies: pydantic, pyyaml, requests

## Running the Server

### Prerequisites
- Docker must be running (the testbed runner uses Docker containers)
- Start Docker Desktop or the Docker daemon before running tests

### Start the Runner Server

Option 1: Use the provided script
```bash
./start_runner.sh
```

Option 2: Manual start
```bash
cd src/runner
export PYTHONPATH="$(pwd)/../../gitrepo:$PYTHONPATH"
export SWEBENCH_DOCKER_FORK_DIR="$(pwd)/../../gitrepo"
/opt/anaconda3/envs/testgeneval/bin/python server.py
```

The server will start on `http://localhost:3000`

## Running Tests

### Test the runner setup
```bash
cd src/runner
export PYTHONPATH="$(pwd)/../../gitrepo:$PYTHONPATH"
export SWEBENCH_DOCKER_FORK_DIR="$(pwd)/../../gitrepo"
/opt/anaconda3/envs/testgeneval/bin/python test.py
```

Note: This requires Docker to be running as it needs to pull and run testbed images.

### Run the pipeline

With the runner server running (in a separate terminal), you can run:

```bash
# Activate the venv
source .venv/bin/activate

# Run once
python -m src.pipeline.run_once --repo django/django --version 4.1 --code-file django/views/static.py

# Or run with iteration
python -m src.pipeline.iterate --repo django/django --version 4.1 --code-file django/views/static.py --max-iters 2

# Or use the orchestrator
python -m src.orchestrator.engine --repo django/django --version 4.1 --code-file django/views/static.py --max-iters 2
```

## Important Notes

1. **Docker Requirement**: The runner requires Docker to be running to execute tests in isolated testbed containers.

2. **Environment Variables**: The runner needs:
   - `PYTHONPATH`: Must include the `gitrepo/` directory
   - `SWEBENCH_DOCKER_FORK_DIR`: Must point to the `gitrepo/` directory

3. **Python Environments**:
   - Main project uses: `.venv` (Python 3.10+)
   - Runner uses: `testgeneval` conda environment (Python 3.9)

4. **Configuration**: Default configuration is in `configs/default.yaml`
   - Runner URL: `http://localhost:3000/runner`
   - LLM provider: OpenAI (requires `OPENAI_API_KEY` environment variable if using LLM features)

## Verification

The setup was verified:
- TestGenEval repository cloned and patched successfully
- Conda environment created with all dependencies
- Main project dependencies installed
- Test script runs (requires Docker for full execution)

