Here is a comprehensive architectural document for the QUEST project, structured for technical documentation or a research paper system overview.

-----

# QUEST: System Architecture & Design Specification

**Quality-Enhanced Supervised Testing**
*A Multi-Agent LLM Framework for Automated Test Generation*

## 1\. Architectural Overview

QUEST is designed as a closed-loop, multi-agent system that iteratively generates, executes, evaluates, and refines unit tests. Unlike single-pass LLM approaches, QUEST employs a "Coordinator-Worker-Critic" pattern to ensure semantic correctness and high coverage.

The system is composed of four primary layers:

1.  **Orchestration Layer:** Manages state, budgets, and routing.
2.  **Agentic Layer:** Specialized LLMs for generation, supervision, and enhancement.
3.  **Execution Layer:** A Dockerized, sandboxed environment for running tests and gathering metrics.
4.  **Reliability & Analysis Layer:** Computes confidence scores using entropy and static analysis.

-----

## 2\. Core Components

### 2.1 The Orchestrator (Control Plane)

The Orchestrator (`src/orchestrator/engine.py`) serves as the central nervous system. It does not generate code but manages the lifecycle of a test generation run.

  * **Context Mining:** Extracts relevant class/function signatures and docstrings from the target repository (`src/orchestrator/context_miner.py`).
  * **State Management:** Tracks the current iteration, global budget (tokens/cost), and history of attempted tests.
  * **Routing Logic:** Determines the next step (Generate $\to$ Execute $\to$ Supervise $\to$ Enhance) based on the **Uncertainty-Driven Routing** mechanism.
  * **Stagnation Detection:** Implements early exit logic if coverage or mutation scores plateau over $N$ iterations.

### 2.2 The Agentic Layer

QUEST utilizes three specialized agent roles, primarily powered by `gpt-4o-mini` for cost efficiency, with optional `gpt-4o` capabilities for complex supervision.

| Agent | Role | Input | Output |
| :--- | :--- | :--- | :--- |
| **Generator** | **Cold Start** | Repo context, Target file path | Initial `unittest` or `pytest` suite |
| **Supervisor** | **Critic** | Execution logs, Coverage report, Mutation score | Structured JSON critique + Strategic instructions |
| **Enhancer** | **Refiner** | Previous test code, Supervisor instructions | Optimized test suite (New iteration) |

### 2.3 Sandboxed Execution Runner

To prevent malicious code execution and ensure environment consistency, tests are executed in an isolated Docker container.

  * **Infrastructure:** Based on TestGenEval/SWE-bench forks.
  * **Interface:** Exposes a Flask API (`src/runner/server.py`) accepting source code and test code.
  * **Instrumentation:**
      * **Coverage:** `pytest-cov` calculates line/branch coverage.
      * **Mutation Testing:** Integrated with **Cosmic Ray**. It injects faults (mutants) into the code to verify if the tests catch them, providing a "Quality Signal" beyond simple line coverage.
      * **Resource Limits:** Enforces CPU/Memory caps to prevent infinite loops.

### 2.4 Reliability Predictor

A distinct module (`src/reliability/predictor.py`) that assigns a trust score to tests before and after execution to filter out "flaky" or "hallucinated" tests.

  * **Pre-Execution Scoring:**
      * **LLM Entropy:** High token entropy indicates low model confidence.
      * **Static Analysis:** AST parsing checks for syntax errors, undefined variables, and linting issues.
      * **Output:** `HIGH`, `MEDIUM`, or `LOW` confidence label.
  * **Post-Execution Scoring:**
      * Evaluates runtime success, coverage delta, and mutation kill rate.
      * **Output:** `TRUSTED`, `NEEDS_REVIEW`, or `DISCARD`.

-----

## 3\. Algorithmic Workflow (The Loop)

The system follows a cyclic process defined in the Orchestrator:

1.  **Initialization:** The Context Miner retrieves the target code and dependencies.
2.  **Generation (Attempt 0):** The **Generator Agent** creates the initial test suite adapted to the repo's framework (e.g., Django `SimpleTestCase` vs standard `unittest`).
3.  **Reliability Check (Pre):** The Reliability Predictor scans the code for syntax validity and entropy spikes.
4.  **Execution:** Code is sent to the Docker Runner.
      * *Dry Run:* If configured, returns deterministic mock data.
      * *Live Run:* Executes tests, captures `stdout/stderr`, computes coverage $\%$, and runs mutation analysis.
5.  **Supervision:** The **Supervisor Agent** analyzes the execution artifacts. It identifies missing coverage regions and surviving mutants.
6.  **Enhancement:** The **Enhancer Agent** receives the critique and rewrites the test suite.
7.  **Loop/Termination:** The loop continues until:
      * Targets are met (e.g., Coverage $> 90\%$, Mutation $> 50\%$).
      * Budget is exhausted (Max iterations or Cost cap).
      * Stagnation is detected (No improvement for 2+ turns).

-----

## 4\. Key Technical Innovations

### 4.1 Uncertainty-Driven Routing

Instead of a linear chain, QUEST uses LLM token entropy as a branching signal.

  * **High Entropy (Low Confidence):** The Router may trigger a more expensive "Deep Reflection" or ask the Supervisor for more granular step-by-step instructions.
  * **Low Entropy (High Confidence):** The system proceeds directly to execution.

### 4.2 Framework-Aware Adaptation

The prompt templates dynamically adjust based on the repository structure.

  * *Example:* If a Django `settings.py` is detected, the agents inject Django-specific test harnesses (`django.test.Client`) rather than generic mocks, significantly reducing setup errors.

### 4.3 Multi-Modal Quality Signal

QUEST moves beyond simple line coverage (which can be gamed) by integrating **Mutation Scoring**. A test suite is only considered "High Quality" if it kills a significant percentage of generated mutants, ensuring the tests actually verify logic, not just execute lines.

-----

## 5\. Observability & Data Architecture

The system maintains a rigorous audit trail for research evaluation (`artifacts/runs/`).

  * **Structure:**
    ```text
    artifacts/runs/<run_id>/
    ├── context.json            # Mined repo context
    ├── events.log              # Chronological system events
    ├── run_summary.json        # High-level metrics (Cost, Time, Status)
    ├── attempt_0/
    │   ├── request.json        # Prompt sent to LLM
    │   ├── response.json       # Raw LLM output + Logprobs
    │   ├── test_code.py        # Extracted source
    │   ├── execution.json      # Runner results (Coverage/Mutation)
    │   └── reliability.json    # Reliability labels
    └── ... (subsequent attempts)
    ```
  * **Dashboard:** A real-time Streamlit app visualizes coverage trends, entropy heatmaps, and supervisor critiques.

-----

## 6\. Implementation Stack

  * **Language:** Python 3.10+
  * **LLM Provider:** OpenAI API (Models: `gpt-4o`, `gpt-4o-mini`).
  * **Containerization:** Docker (Custom images compatible with TestGenEval).
  * **Testing Libraries:** `pytest`, `unittest`, `coverage.py`, `cosmic-ray`.
  * **Static Analysis:** `ast`, `pylint`, `mypy`.
  * **Evaluation:** Benchmarked against the TestGenEval dataset (ICLR 2025).