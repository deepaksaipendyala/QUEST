# End-to-End Pipeline Guide

## System Status: RESEARCH-READY ✅

The QUEST system is now fully integrated with all major components working together.

## Quick Start

### 1. Start the Runner Server
```bash
./start_runner.sh
```
This starts the Flask server at `http://localhost:3000` that executes tests in Docker.

### 2. (Optional) Start the Dashboard
```bash
source .venv/bin/activate
streamlit run streamlit_app.py
```
Then open `http://localhost:8501` to view real-time metrics.

### 3. Run the Full Orchestrator Pipeline

The orchestrator runs the complete multi-agent loop:
- **Generator**: Creates initial test
- **Supervisor**: Analyzes results (coverage, mutation, lint, static analysis)
- **Enhancer**: Improves tests based on critique
- **Router**: Decides whether to continue or stop

```bash
source .venv/bin/activate
python -m src.orchestrator.engine \
  --repo django/django \
  --version 4.1 \
  --code-file django/views/static.py \
  --max-iters 3
```

## What Gets Tracked

### Per Attempt:
- Test source code
- Runner request/response
- Coverage and mutation scores
- Static analysis metrics (pylint, mypy, complexity)
- Pre-execution reliability score (entropy, static metrics)
- Post-execution reliability score (coverage, mutation, success)
- Supervisor critique (instructions, missing lines)
- LLM metadata (entropy, tokens, cost, duration)
- Timing metrics (runner, static analysis, LLM)

### Run Summary:
- Total LLM cost
- Total tokens (input/output)
- Total duration (LLM, runner, static analysis)
- Number of iterations
- Final coverage and mutation scores

## Output Structure

```
artifacts/runs/run_<timestamp>_<id>/
├── context.json                    # Mined context from source file
├── run_summary.json                # Aggregated metrics
├── events.log                      # Event timeline
├── attempt_0.*                     # Initial generation
│   ├── request.json
│   ├── test_src.py
│   ├── response.json
│   ├── static.json
│   ├── pre_reliability.json
│   ├── post_reliability.json
│   ├── critique.json
│   └── metrics.json
├── attempt_1.*                     # First enhancement
│   ├── request.json
│   ├── test_src.py
│   ├── llm_metadata.json          # LLM call details
│   ├── response.json
│   ├── static.json
│   ├── pre_reliability.json
│   ├── post_reliability.json
│   ├── critique.json
│   └── metrics.json
└── ...
```

## Key Features

### 1. Reliability Prediction
- **Pre-execution**: Uses LLM entropy + static analysis
- **Post-execution**: Combines coverage, mutation, success status
- **Labels**: Trusted / Needs Review / Discard

### 2. Cost Tracking
- Tracks token usage per LLM call
- Calculates estimated cost based on model pricing
- Aggregates total cost per run

### 3. Static Analysis
- Runs pylint (error/fatal detection)
- Runs mypy (type checking)
- Calculates complexity metrics
- Feeds into reliability prediction

### 4. Mutation Testing
- Enabled by default (set `SKIP_MUTATION=false`)
- Mutation scores used in:
  - Supervisor critiques
  - Router decisions
  - Reliability prediction
  - Progress tracking

### 5. Routing Intelligence
- Stops on coverage target met
- Stops on stagnation (no progress for 2 iterations)
- Stops on max iterations
- Uses mutation scores in decisions

## Exporting Results

### Export Run Summaries
```bash
python -m src.scripts.export_runs --format csv --output runs.csv --limit 50
python -m src.scripts.export_runs --format json --output runs.json --limit 50
```

### Export Specific Run Detail
```bash
python -m src.scripts.export_runs --run-id run_1763343184984_84af8baa --output detail.json
```

## Configuration

Edit `configs/default.yaml`:
```yaml
runner_url: "http://localhost:3000/runner"
targets:
  coverage: 60.0
  mutation: 50.0
static_analysis:
  enable: true
llm:
  collect_logprobs: true  # Required for entropy
```

## Environment Variables

```bash
export OPENAI_API_KEY="sk-..."      # Required for LLM
export SKIP_MUTATION="false"         # Enable mutation testing
export LLM_COLLECT_LOGPROBS="true"  # Enable entropy tracking
```

## Example Output

```
[run_1763343184984_84af8baa] coverage=42.86% target met in attempt 2
[run_1763343184984_84af8baa] Run complete: total_cost=$0.000234 total_duration=45.32s
```

## Next Steps

1. Run experiments across TestGenEval dataset
2. Export results for analysis
3. Compare against baselines
4. Analyze RQ1, RQ2, RQ3
5. Generate figures and tables

The system is ready for research experiments!

