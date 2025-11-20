# Mutation Testing Implementation

This document explains how mutation testing was integrated into the TestGenEval runner system.

## Overview

Mutation testing measures test quality by introducing small changes (mutations) to the source code and checking if the tests detect these changes. A high mutation score indicates that tests are effective at catching bugs.

## Architecture

### 1. **Tool: Cosmic Ray**

We use [Cosmic Ray](https://cosmic-ray.readthedocs.io/) as the mutation testing framework. It's a Python mutation testing tool that:
- Generates mutants by applying mutation operators (e.g., changing `+` to `-`, `>` to `>=`, etc.)
- Runs tests against each mutant
- Reports how many mutants were "killed" (detected by tests) vs "survived"

### 2. **Integration Points**

#### A. Docker Container Execution (`gitrepo/swebench_docker/context_manager.py`)

The mutation testing happens **inside the Docker container** where the testbed code lives:

```python
def run_mutation_testing(self, instance, specifications, test_time, test_cmd):
    # 1. Create mutation.toml configuration file
    with open("mutation.toml", "w") as mutant_file:
        formatted_content = MUTATION_TEMPLATE.format(
            source_fp=instance["code_file"],  # Target file to mutate
            timeout=max(10, 1.5 * test_time),  # Timeout per mutant
            test_cmd=test_cmd,  # Command to run tests
        )
        mutant_file.write(formatted_content)
    
    # 2. Initialize mutation database
    self.exec("cosmic-ray init mutation.toml mutation.sqlite".split(), ...)
    
    # 3. Execute mutation testing (runs all mutants)
    self.exec("cosmic-ray exec mutation.toml mutation.sqlite".split(), ...)
    
    # 4. Calculate mutation score
    output = self.exec("cr-rate mutation.sqlite --estimate --confidence 95.0".split(), ...)
    
    # 5. Get total number of mutants
    num_output = self.exec("cr-report mutation.sqlite".split(), ...)
    
    # 6. Parse and log results
    # Mutation score = 100 - (surviving_mutants / total_mutants * 100)
    mutation_score = 100 - val
    self.log.write(f"\nMutationLOG: {mutation_score}%")
    self.log.write(f"\nMutationNum: {num_mutants}")
    self.log.write(f"\nMutationUncertainty: {confidence_range}")
```

**Key Configuration** (`MUTATION_TEMPLATE` in `gitrepo/swebench_docker/constants.py`):
```toml
[cosmic-ray]
module-path = "{source_fp}"  # File to mutate
timeout = {timeout}           # Per-mutant timeout
excluded-modules = []
test-command = "{test_cmd}"   # Command to run tests

[cosmic-ray.distributor]
name = "local"
```

#### B. Log Parsing (`gitrepo/swebench_docker/swebench_utils.py`)

After mutation testing completes, the runner logs are parsed to extract metrics:

```python
if "MutationLOG" in config:
    mutation_score = float(config.split("MutationLOG: ")[1].split("%")[0])
else:
    mutation_score = -1  # Not available

if "MutationUncertainty" in config:
    mutation_uncertainty = float(config.split("MutationUncertainty: ")[1].split("\n")[0])
else:
    mutation_uncertainty = -1

if "MutationNum" in config:
    mutation_num = float(config.split("MutationNum: ")[1].split("\n")[0])
else:
    mutation_num = -1
```

#### C. Result Extraction (`src/runner/single_runner.py`)

The parsed metrics are extracted from the log and returned in `CustomRunResult`:

```python
log_metrics = get_logs_eval(log_path)
full_metrics = log_metrics.get("full", {})

mutation_score_values = full_metrics.get("mutation_score", [])
mutation_score = mutation_score_values[0] if mutation_score_values else None

mutation_uncertainty_values = full_metrics.get("mutation_uncertainty", [])
mutation_uncertainty = mutation_uncertainty_values[0] if mutation_uncertainty_values else None

mutation_num_values = full_metrics.get("mutation_num", [])
mutation_num = mutation_num_values[0] if mutation_num_values else None

return CustomRunResult(
    ...
    mutation_score=mutation_score,
    mutation_uncertainty=mutation_uncertainty,
    mutation_num=mutation_num,
)
```

#### D. API Response (`src/runner/server.py`)

The mutation metrics are included in the HTTP response:

```python
api_response = {
    ...
    "mutation_score": result.mutation_score,
    "mutation_uncertainty": result.mutation_uncertainty,
    "mutation_num": result.mutation_num,
}
```

### 3. **Control Flow**

```
1. Pipeline/Orchestrator sends test to runner server
   ↓
2. Runner server calls run_custom_test()
   ↓
3. Docker container is launched with testbed code
   ↓
4. Tests are run and coverage is measured
   ↓
5. If SKIP_MUTATION=false, run_mutation_testing() is called:
   a. Create mutation.toml config
   b. cosmic-ray init (create mutation database)
   c. cosmic-ray exec (run all mutants)
   d. cr-rate (calculate mutation score)
   e. cr-report (get total mutant count)
   f. Log results to eval.log
   ↓
6. Logs are parsed to extract mutation metrics
   ↓
7. Metrics are returned in HTTP response
   ↓
8. Pipeline/Orchestrator stores metrics in artifacts
```

### 4. **Environment Control**

Mutation testing can be disabled via environment variable:

```bash
export SKIP_MUTATION=true  # Disable mutation testing
```

This is checked in `src/runner/server.py`:
```python
skip_mutation = os.getenv("SKIP_MUTATION", "false").lower() == "true"
result = run_custom_test(..., skip_mutation=skip_mutation, ...)
```

### 5. **Docker Image Requirements**

Cosmic Ray must be installed in the Docker container. This is handled by:
- **Python images**: Cosmic Ray is installed via `pip install cosmic-ray` in the Dockerfile
- **Conda images**: Cosmic Ray is installed in the conda environment (see `gitrepo/testgeneval.yaml`)

Example from a Dockerfile:
```dockerfile
RUN pip install coverage cosmic-ray
```

### 6. **Metrics Explained**

- **`mutation_score`**: Percentage of mutants killed by tests (0-100). Higher is better.
  - Formula: `100 - (surviving_mutants / total_mutants * 100)`
  - Example: 50 mutants total, 20 survive → score = 100 - (20/50 * 100) = 60%

- **`mutation_num`**: Total number of mutants generated

- **`mutation_uncertainty`**: Confidence interval range (from `cr-rate --estimate --confidence 95.0`)

### 7. **Integration with Reliability Predictor**

Mutation scores are used in the reliability predictor (`src/reliability/predictor.py`):

```python
def score_post_execution(pre_score, runner_response, target_coverage, target_mutation):
    mutation_score = float(runner_response.get("mutation_score", -1.0))
    
    if target_mutation > 0.0:
        if mutation_score < target_mutation:
            reasons.append("Mutation score below target.")
        elif mutation_score < 0.0:
            reasons.append("Mutation score unavailable; rerun mutation testing.")
```

### 8. **Supervisor Integration**

The supervisor agent (`src/llm/supervisor.py`) uses mutation scores to generate critiques:

```python
low_mutation = (
    mutation_target > 0.0
    and (
        mutation_score < mutation_target
        if mutation_score >= 0.0
        else True
    )
)

if low_mutation:
    instructions.append(f"Improve mutation score from {mutation_score:.2f}% toward {mutation_target:.2f}%.")
```

## Example Output

From a successful run:
```
MutationNum: 69
MutationLOG: 27.54%
MutationUncertainty: 0.0
```

This means:
- 69 mutants were generated
- 27.54% mutation score (about 19 mutants were killed, 50 survived)
- 0.0 uncertainty (high confidence in the estimate)

## Troubleshooting

1. **Mutation score is -1**: 
   - Check if `SKIP_MUTATION=true` was set
   - Verify Cosmic Ray is installed in the Docker container
   - Check runner logs for "MutationFAIL" or timeout errors

2. **Mutation testing is slow**:
   - Each mutant runs the full test suite
   - Timeout is set to `1.5 * test_time` per mutant
   - Consider reducing timeout or skipping mutation for quick iterations

3. **No mutants generated**:
   - Verify the target file path is correct
   - Check that Cosmic Ray can parse the source file
   - Ensure the file is Python (Cosmic Ray only works with Python)

## References

- Cosmic Ray documentation: https://cosmic-ray.readthedocs.io/
- TestGenEval mutation integration: `gitrepo/swebench_docker/context_manager.py`
- Log parsing: `gitrepo/swebench_docker/swebench_utils.py`
- Result extraction: `src/runner/single_runner.py`

