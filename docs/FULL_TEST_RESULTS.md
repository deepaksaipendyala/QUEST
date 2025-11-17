# Full Test Results with Docker

## ✅ Complete End-to-End Test Successful!

### Test Execution Summary

**Test Run**: `run_1763333943388_69ac5e08`
- **Status**: ✅ Success
- **Coverage**: 38.10%
- **Task ID**: `django__django-15498-90`
- **Test Passed**: Yes

### What Was Tested

1. **Pipeline Execution** ✅
   - Generated test code automatically
   - Sent request to runner server
   - Received response with results

2. **Runner Server** ✅
   - Successfully received POST request
   - Executed test in Docker container
   - Calculated coverage metrics
   - Returned structured response

3. **Docker Integration** ✅
   - Docker daemon running
   - Testbed container executed successfully
   - Test execution completed

### Generated Artifacts

The pipeline created the following files in `artifacts/runs/run_1763333943388_69ac5e08/`:
- `request.json` - The request sent to the runner
- `response.json` - The response from the runner
- `test_src.py` - The generated test code

### System Status

- ✅ Runner server: Running on http://localhost:3000
- ✅ Docker: Running and functional
- ✅ Pipeline: Working end-to-end
- ✅ Test execution: Successful
- ✅ Coverage calculation: Working (38.10%)

### Next Steps

You can now:

1. **Run single test**:
   ```bash
   source .venv/bin/activate
   python -m src.pipeline.run_once --repo django/django --version 4.1 --code-file django/views/static.py
   ```

2. **Run with iteration** (requires OpenAI API key):
   ```bash
   export OPENAI_API_KEY="sk-..."
   python -m src.pipeline.iterate --repo django/django --version 4.1 --code-file django/views/static.py --max-iters 2
   ```

3. **Use orchestrator**:
   ```bash
   python -m src.orchestrator.engine --repo django/django --version 4.1 --code-file django/views/static.py --max-iters 2
   ```

### Configuration

Default configuration is in `configs/default.yaml`:
- Runner URL: `http://localhost:3000/runner`
- Target coverage: 60.0%
- Max iterations: 2

