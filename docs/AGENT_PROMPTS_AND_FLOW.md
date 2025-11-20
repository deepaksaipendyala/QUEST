# Agent Prompts and System Flow

This document describes all agent prompts and the complete orchestration flow.

## System Flow Overview

```
1. Attempt 0 (Initial Generation)
   ├─ Generator Agent (LLM) → generates initial test suite
   ├─ Static Analysis → syntax, lint, complexity checks
   ├─ Pre-execution Reliability → entropy + static metrics → HIGH/MED/LOW
   ├─ Runner → executes tests, measures coverage & mutation
   ├─ Post-execution Reliability → coverage + mutation + success → trusted/needs_review/discard
   └─ Supervisor Agent → analyzes results, generates critique + instructions

2. Attempt 1+ (Enhancement Loop)
   ├─ Router → decides ENHANCE or FINISH based on critique
   ├─ Enhancer Agent (LLM) → refines test suite using supervisor instructions
   ├─ Static Analysis → re-checks syntax, lint, complexity
   ├─ Pre-execution Reliability → updated entropy + static metrics
   ├─ Runner → re-executes tests, measures new coverage & mutation
   ├─ Post-execution Reliability → updated reliability score
   └─ Supervisor Agent → generates new critique + instructions
   
3. Termination Conditions
   ├─ Coverage target met
   ├─ Max iterations reached
   ├─ Router decides FINISH (no progress, targets unreachable)
   └─ Early exit on critical errors
```

---

## Agent 1: Generator (Attempt 0)

**Location**: `src/orchestrator/engine.py` (lines 243-333)

**When**: Only for attempt 0, if LLM is enabled

**Prompt Template**:

```python
"""
You are an expert Python test generator.
Your goal is to maximise BRANCH COVERAGE and MUTATION SCORE for the target file.

Repository: {repo}
Version: {version}
Target file: {code_file}

Here is the full source code of the file under test:
----------------
{code_src}
----------------

Follow these framework rules:
{test_style_instructions}

Global requirements for ALL repos:
- Maximise branch coverage
- Use real filesystem operations where possible (tempfile.TemporaryDirectory())
- Avoid network or database calls
- Imports must be correct for the target repo
- Output ONLY Python test code (no markdown, no comments, no headings)
"""
```

**Framework-Specific Instructions** (Django):

```python
"""
You MUST generate tests using Django's unittest framework.

Strict requirements:
- Use: from django.test import SimpleTestCase or TestCase
- DO NOT import pytest anywhere
- DO NOT use pytest-style asserts or fixtures
- Use unittest assertions: self.assertEqual, self.assertTrue, self.assertRaises, etc.
- Use unittest.mock instead of pytest.mock
- Maximise coverage by using real filesystem:
    * use tempfile.TemporaryDirectory()
    * create real files/directories using pathlib.Path
    * exercise actual Path.exists(), Path.is_dir(), Path.stat(), Path.iterdir()
    * exercise serve(), directory_index(), and was_modified_since()
- Test branches:
    * directory with show_indexes=True → HTML response
    * directory with show_indexes=False → Http404
    * missing file → Http404
    * valid file → FileResponse (validate headers)
    * If-Modified-Since → HttpResponseNotModified
- Avoid Django test client; call the functions directly.
"""
```

**Framework-Specific Instructions** (Non-Django):

```python
"""
You MUST generate tests using Python's built-in unittest framework.

Strict requirements:
- DO NOT import pytest
- DO NOT use pytest-style asserts
- DO NOT use fixtures or parametrize
- Use: import unittest
- Test classes must subclass unittest.TestCase
- Use unittest assertions:
    * self.assertEqual
    * self.assertTrue
    * self.assertFalse
    * self.assertRaises
- Use unittest.mock for mocking
- Use tempfile.TemporaryDirectory() for real filesystem testing
- Use real pathlib.Path operations, avoid mocking whenever possible
- Maximise branch coverage and mutation score
- Imports must match the repo's internal structure
"""
```

**LLM Config**:
- Model: `gpt-4o-sciAI` (from config) or `gpt-4o-mini` (fallback)
- Temperature: 0.2
- Top-p: 0.95
- Collect logprobs: if `LLM_COLLECT_LOGPROBS=true`

**Output**: Raw Python test code (no markdown formatting)

---

## Agent 2: Supervisor (All Attempts)

**Location**: `src/llm/supervisor.py`

**Type**: Rule-based (no LLM call)

**Input**: Runner response + static metrics + reliability scores + targets

**Logic**:

1. **Extract metrics**:
   - Coverage, mutation score, success status
   - Missing lines from coverage details
   - Lint/type issue counts from static analysis
   - Pre/post reliability levels

2. **Detect issues**:
   - `compile_error`: syntax errors or runner failures
   - `no_tests`: no tests collected
   - `low_coverage`: coverage < target
   - `low_mutation`: mutation score < target (or unavailable)

3. **Generate instructions** (ordered by priority):

```python
# Priority 1: Syntax/Compilation
if not syntax_ok:
    "Static analyzer found syntax issues; fix parser errors first."

if lint_issue_count > 0:
    f"Resolve {lint_issue_count} lint/type errors reported by available tools."

if compile_error and syntax_ok:
    "Resolve Runner errors and ensure tests execute successfully."

# Priority 2: Test Collection
if no_tests:
    "Add at least one pytest/unittest case so tests are collected."

# Priority 3: Coverage
if low_coverage:
    if missing_lines:
        f"Add coverage for lines: {missing_lines[:10]}."
    else:
        "Increase test coverage with more assertions."

# Priority 4: Mutation
if low_mutation:
    if mutation_score >= 0.0:
        f"Improve mutation score from {mutation_score:.2f}% toward {target:.2f}%."
    else:
        "Mutation score unavailable; ensure mutation testing runs and improves surviving mutants."

# Priority 5: Reliability Guidance
if post_reliability["level"] not in ("trusted", "pass"):
    "Reliability blockers: {reasons from post_reliability}."

if lint_issues > 0:
    f"Fix {lint_issues} lint/type issues noted in reliability analysis."

if test_error:
    f"Address runner error reported: {test_error}."
```

**Output**: `Critique` dict with:
- Boolean flags: `compile_error`, `no_tests`, `low_coverage`, `low_mutation`
- Metrics: `mutation_score`, `lint_issue_count`, `coverage_delta`, `mutation_delta`
- Action items: `instructions` (list of strings), `missing_lines` (list of ints)

---

## Agent 3: Enhancer (Attempts 1+)

**Location**: `src/llm/enhancer.py`

**When**: After supervisor critique, if router decides `ENHANCE`

**Prompt Template**:

```python
"""
You are an expert Python test engineer improving an existing test module.
Repository: {repo}
Version: {version}
Target file: {code_file}
Follow these guardrails:
{guardrails}

Current test suite:
{current_test_src}

Rewrite the suite by applying the instructions below while preserving the existing framework/style.

Instructions:
{instruction_block}

Return only the revised Python test module (plain code, no markdown).
"""
```

**Guardrails** (framework-aware):

```python
# For unittest-based tests:
guardrails = [
    "Use unittest-style classes/tests (unittest.TestCase or django.test.SimpleTestCase). "
    "Do NOT import pytest or use pytest fixtures/decorators.",
    "Keep the existing imports unless a new helper is strictly required.",
    "Avoid filesystem or network dependencies; prefer in-memory values/mocks.",
    "Do not add `if __name__ == '__main__':` or call unittest.main/pytest.main.",
]

# For Django repos:
if "django" in repo.lower():
    guardrails.append(
        "When interacting with Django utilities, use django.test helpers and avoid touching real files."
    )

# For pytest-based tests:
if framework == "pytest":
    guardrails[0] = (
        "Pytest-style functions and fixtures are acceptable, but keep the current style consistent."
    )
```

**Instruction Block** (from supervisor):

```python
instruction_block = "\n".join(f"- {item}" for item in instructions if item)

if missing_lines:
    line_targets = ", ".join(str(m) for m in missing_lines[:10])
    instruction_block += f"\n- Increase coverage for lines: {line_targets}."

if not instruction_block.strip():
    instruction_block = "- Improve coverage and robustness without breaking existing passing tests."
```

**LLM Config**:
- Model: `gpt-4o-mini`
- Temperature: 0.2
- Top-p: 0.95
- Collect logprobs: if `LLM_COLLECT_LOGPROBS=true`

**Output**: Revised Python test code (preserving framework style)

---

## Router (Decision Logic)

**Location**: `src/orchestrator/router.py`

**Decision Function**:

```python
def decide(critique: Critique, iterations_done: int, max_iterations: int) -> str:
    if iterations_done >= max_iterations:
        return "FINISH"
    
    if critique.get("no_progress", False):
        return "FINISH"
    
    if critique.get("compile_error", False):
        return "ENHANCE"  # Try to fix compilation
    
    if not critique.get("low_coverage", False) and not critique.get("low_mutation", False):
        return "FINISH"  # Targets met
    
    return "ENHANCE"
```

**Progress Tracking**:
- `coverage_delta >= 1.0%` OR `mutation_delta >= 2.0%` → progress detected
- If no progress AND (`low_coverage` OR `low_mutation`) → increment stagnation counter
- `stagnation_count >= 2` → `no_progress = True` → FINISH

---

## Complete Flow Example

### Attempt 0

1. **Generator** receives:
   - Repo: `django/django`
   - Version: `4.1`
   - Code file: `django/views/static.py`
   - Full source code (fetched from runner)

2. **Generator** produces initial test suite (via LLM)

3. **Static Analysis** runs:
   - Syntax check
   - Pylint (if available)
   - Mypy (if available)
   - Complexity metrics

4. **Pre-execution Reliability**:
   - Entropy from LLM: `0.1028` (medium confidence)
   - Lint issues: 16
   - Level: `medium` (downgraded from high due to lint)

5. **Runner** executes:
   - Coverage: `44.44%`
   - Mutation: `37.68%`
   - Success: `true`

6. **Post-execution Reliability**:
   - Coverage below target (60%)
   - Mutation below target (50%)
   - Level: `needs_review`

7. **Supervisor** generates critique:
   ```json
   {
     "low_coverage": true,
     "low_mutation": true,
     "mutation_score": 37.68,
     "instructions": [
       "Add coverage for lines: 45, 67, 89.",
       "Improve mutation score from 37.68% toward 50.00%."
     ],
     "missing_lines": [45, 67, 89]
   }
   ```

### Attempt 1

1. **Router** decides: `ENHANCE` (coverage/mutation below targets)

2. **Enhancer** receives:
   - Current test suite (from attempt 0)
   - Instructions: `["Add coverage for lines: 45, 67, 89.", "Improve mutation score..."]`
   - Missing lines: `[45, 67, 89]`
   - Context: `{repo, version, code_file}`

3. **Enhancer** produces revised test suite (adds tests for missing lines)

4. **Static Analysis** re-runs (checks for new lint issues)

5. **Pre-execution Reliability** (updated with new entropy)

6. **Runner** re-executes:
   - Coverage: `52.11%` (improved)
   - Mutation: `41.23%` (improved)
   - Success: `true`

7. **Post-execution Reliability** (updated)

8. **Supervisor** generates new critique:
   ```json
   {
     "low_coverage": true,
     "low_mutation": true,
     "coverage_delta": 7.67,
     "mutation_delta": 3.55,
     "instructions": [
       "Add coverage for lines: 89, 112.",
       "Improve mutation score from 41.23% toward 50.00%."
     ]
   }
   ```

### Attempt 2

1. **Router** decides: `ENHANCE` (still below targets, progress detected)

2. **Enhancer** refines further

3. ... (continues until target met, max iterations, or no progress)

---

## Key Design Decisions

1. **Generator uses full source code**: Fetches actual file contents from runner to ensure accurate test generation.

2. **Supervisor is rule-based**: No LLM call, deterministic analysis based on metrics.

3. **Enhancer preserves framework**: Detects existing framework (unittest vs pytest) and enforces consistency.

4. **Reliability drives routing**: Pre-exec reliability downgrades risky tests; post-exec reliability informs supervisor instructions.

5. **Progress tracking prevents loops**: Stagnation detection (no improvement for 2 attempts) triggers FINISH.

6. **Cost tracking**: All LLM calls (generator + enhancer) accumulate in `total_llm_cost` for observability.

