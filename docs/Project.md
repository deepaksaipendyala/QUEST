# QUEST (QUality-Enhanced Supervised Testing)
## Description

You are building **TestGen**: a **multi-agent, metric-driven LLM test generation system** that automatically produces, validates, and labels unit tests for real-world Python code, aiming to beat single-LLM baselines on coverage and reliability. 

---

## 2. Problem and motivation

**Problem:**
Current LLM-generated unit tests:

* Have **low and unstable coverage** on real repositories (e.g., GPT-4o ~35% coverage on TestGenEval).
* Often contain **style, type, or logical errors** that only show up when running tests.
* Provide **no reliability signal** – developers cannot easily tell which tests to trust without manual review.

**Why this matters:**

* QA and code-review teams spend time **debugging and filtering bad LLM tests**.
* CI/CD pipelines get slowed by **flaky or low-value tests**.
* Researchers and teams lack a **systematic framework** for improving test quality beyond “ask the LLM again”.

Your project aims to make LLM-generated tests **trustworthy, measurable, and self-improving**, not just “more tests from a bigger model”.

---

## 3. High-level idea

You design a **multi-agent loop** wrapped around a **sandboxed test runner** and a **reliability predictor**:

1. An **Orchestrator** keeps global state, budget, and routing decisions.
2. A team of **agents**:

   * **Generator** drafts initial pytest tests.
   * **Supervisor** analyzes them with static and dynamic tools.
   * **Enhancer** focuses only on uncovered lines, surviving mutants, or uncertain cases.
3. A **Sandboxed Runner** executes tests safely (coverage + mutation).
4. A **Reliability Predictor** combines **LLM uncertainty, static metrics, and runtime metrics** to assign a reliability label to each test suite.
5. An **Observability & Storage** layer logs metrics, artifacts, and traces for analysis and ablations.

The loop continues until quality criteria are met or the budget is exhausted.

---

## 4. System components (by box in the diagram)

### 4.1 Orchestrator

Responsibilities:

* **Start / Load Target Code**
  Takes a target Python file or module from the **TestGenEval** dataset and prepares it for analysis.
* **Initialize State and Budgets**
  Sets budgets like:

  * max LLM calls
  * max number of refinement iterations
  * time and cost limits.
* **Enforce Budgets and Thresholds**
  Tracks coverage, mutation scores, entropy thresholds, and iteration counts.
* **Decide Routing**
  Based on metrics from the Supervisor and Runner, decides whether to:

  * call the **Enhancer** again, or
  * stop and move to **Collect Results**.

Essentially, the Orchestrator is the **control tower** that keeps the whole pipeline bounded and goal-driven.

---

### 4.2 Agents

These live in the big purple box: **Generator, Supervisor, Enhancer**, plus a **Routing Decision** node.

#### 4.2.1 Generator Agent

* Input: code under test, docstrings, signatures, uncovered lines/branches, and possibly previous failed tests.
* Output: **focused pytest test cases**.
* Uses prompt strategies guided by:

  * uncovered branches
  * function semantics
  * examples from the dataset.

Think of it as the **first draft writer** for tests.

#### 4.2.2 Supervisor Agent

* Receives tests from the Generator (and later the Enhancer).

* Runs or uses outputs from static and dynamic tools:

  * **Linting / style** (pylint, flake8, etc.).
  * **Type checks** (mypy).
  * Basic static metrics: cyclomatic complexity, insecure patterns, etc.
  * Interacts with the **Sandboxed Runner** to get:

    * coverage metrics
    * mutation test results
    * execution errors / logs.

* Returns a **machine-readable summary of issues and metrics** to the Orchestrator and Routing Decision.

This agent is your **quality gate and analyst**.

#### 4.2.3 Enhancer Agent

Triggered **only when needed** based on routing conditions:

> Coverage < target OR
> Mutation score < target OR
> Entropy > threshold OR
> Errors exist AND iterations < max

When these hold, the Orchestrator calls the Enhancer to:

* Repair failing or low-quality tests.
* Generate new tests specifically targeting:

  * uncovered lines/branches,
  * surviving mutants,
  * high-uncertainty regions of the code.

This makes the loop **coverage and uncertainty aware**, instead of blindly generating more random tests.

#### 4.2.4 Routing Decision Node

* Combines metrics from the Supervisor and uncertainty scores from the LLM.
* Decides between:

  * sending things back to **Enhancer**, or
  * finishing and sending final test suites to **Collect Results**.

This is the **brain of the coordination logic**.

---

### 4.3 Sandboxed Runner

The grey horizontal block executes tests in an isolated environment:

1. **Setup Docker Environment**

   * Spins up a container with Python, pytest, pytest-cov, Cosmic Ray, linters, etc.
   * Ensures test execution is **isolated, reproducible, and safe**.

2. **Run Pytest Coverage**

   * Produces line/branch/function coverage via `pytest-cov`.

3. **Run Mutation Testing**

   * Uses **Cosmic Ray** to mutate the code under test.
   * Measures how many mutants are killed by the generated tests.

4. **Enforce Resource Limits**

   * Timeouts, CPU, and memory caps so LLM-generated tests cannot hang or crash the system.

5. **Capture Logs**

   * Aggregates stdout, stderr, coverage reports, mutation diffs, and error traces.
   * These logs feed into both the **Supervisor** and the **Reliability Predictor**.

This runner is your **ground-truth oracle** for how good the tests actually are.

---

### 4.4 Observability and Storage

The pink block at the bottom:

* **Store Metrics**

  * Run-level metrics: coverage (line, branch, function), mutation score, runtime, number of retries, number of LLM calls.
* **Store Artifacts**

  * Test files, HTML coverage reports, mutation diff reports, logs.
* **Store Traces**

  * Prompts, model responses, routing decisions, and intermediate metrics for each iteration.
* **Export Reports**

  * Aggregated dashboards or CSV/JSON for analysis, ablation studies, and paper figures.

This layer turns your system into a **research platform**, not just a one-off script.

---

### 4.5 Reliability Predictor

The yellow block on the right is a **two-stage reliability classifier**.

1. **Pre-Execution Scoring**

   * Before tests are run, it uses:

     * LLM **entropy / uncertainty** (from token logprobs).
     * Static complexity metrics.
     * Lint and type-check results.
   * Outputs a coarse label like **High / Medium / Low expected reliability**.

   This enables early triage: some test suites may be skipped, down-weighted, or targeted for extra enhancement.

2. **Post-Execution Scoring**

   * After the Sandboxed Runner executes tests, it adds:

     * coverage metrics,
     * mutation scores,
     * flakiness or error statistics.
   * Computes a refined reliability score.

3. **Assign Reliability Label**

   * Assigns final labels (e.g., **Trusted / Needs Review / Discard**) to test suites or individual tests.
   * These labels can be surfaced to developers or used for automatic filtering in CI.

This component is what lets you **annotate LLM tests with reliability**, reducing manual judgment effort.

---

## 5. Project goals and research questions

According to your proposal, the main questions are:

1. **Coverage and performance**

   * Does **confidence-driven multi-agent coordination** (using entropy + metrics) achieve higher coverage than a single LLM that just generates tests once?
2. **Metric-driven refinement**

   * Does feeding **real-time coverage and mutation feedback** into the loop improve coverage and mutation scores compared to non-feedback baselines?
3. **Reliability prediction**

   * Can you **predict which tests are reliable before execution** by combining LLM confidence, static analysis, and complexity metrics?
   * And how much does adding post-execution metrics improve that prediction?

---

## 6. Dataset and evaluation

* **Dataset:**

  * **TestGenEval (ICLR 2025)**: 1,210 Python code–test file pairs from 11 real-world open-source repositories with ~68k human-written tests.
  * Baselines (e.g., GPT-4o) achieve only ~35% coverage, highlighting the difficulty of the problem.

* **Evaluation Metrics:**

  * **Coverage:** line, branch, function coverage via `pytest-cov`.
  * **Mutation Score:** killed mutants / total mutants × 100 using Cosmic Ray.
  * **Efficiency:**

    * number of LLM calls per suite,
    * number of Enhancer calls,
    * test execution overhead.
  * **Static Quality Signals:** lint errors, type errors, complexity, insecure patterns.
  * **Pass@K / success rates** across different sampling strategies.

* **Limitations you acknowledge:**

  * Python-only and 11 repos may bias results.
  * Coverage/mutation are imperfect proxies for semantic quality, even with extra signals.
  * Multi-agent loops add computational overhead.

---

## 7. Expected contributions

By the end of the project, you aim to deliver:

1. A **working multi-agent test generation framework** with:

   * Orchestrator, Generator, Supervisor, Enhancer.
   * Sandboxed Runner with coverage + mutation.
   * Reliability Predictor and observability stack.

2. A **systematic study** showing:

   * Coverage and mutation improvements over single-agent LLM baselines.
   * The effect of **uncertainty-driven routing** vs naive routing.
   * How well **pre- vs post-execution reliability scores** correlate with actual test usefulness.

3. A **dataset of test suites with reliability labels** and traces that can be reused for future research in GenAI for SE.
