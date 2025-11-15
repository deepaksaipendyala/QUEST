"""Utilities for running custom TestGenEval-lite evaluations with bespoke tests."""

from __future__ import annotations

import asyncio
import glob
import os
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, Optional

from gitrepo.swebench_docker.constants import (
    KEY_ID,
    KEY_INSTANCE_ID,
    KEY_MODEL,
    KEY_PREDICTIONS,
    MAP_REPO_TO_TEST_FRAMEWORK,
    MAP_VERSION_TO_INSTALL,
)
from gitrepo.swebench_docker.run_docker import run_docker_evaluation
from gitrepo.swebench_docker.swebench_utils import get_logs_eval, get_test_directives
from gitrepo.swebench_docker.utils import get_eval_refs

DEFAULT_DATASET = "kjain14/testgenevallite"
DEFAULT_NAMESPACE = "kdjain"
DEFAULT_RESULTS_ROOT = "results/runner"
DEFAULT_MODEL_NAME = "custom-runner"


@dataclass
class CustomRunResult:
    """Structured results for a single custom evaluation."""

    task_id: str
    instance_id: str
    repo: str
    version: str
    code_file: str
    log_path: str
    coverage: Optional[float]
    passed: bool
    test_error: str
    log_text: str
    baseline_coverage: Optional[float]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "instance_id": self.instance_id,
            "repo": self.repo,
            "version": self.version,
            "code_file": self.code_file,
            "log_path": self.log_path,
            "coverage": self.coverage,
            "passed": self.passed,
            "test_error": self.test_error,
            "baseline_coverage": self.baseline_coverage,
            "log_text": self.log_text,
        }


class TaskLookupError(ValueError):
    """Raised when the requested repo/version/code_file tuple has no dataset match."""


def _select_task(
    dataset_refs: Dict[str, Dict[str, Any]],
    repo: str,
    version: str,
    code_file: str,
) -> Dict[str, Any]:
    matches = []
    for task in dataset_refs.values():
        task_dict = dict(task)
        if (
            task_dict.get("repo") == repo
            and task_dict.get("version") == version
            and task_dict.get("code_file") == code_file
        ):
            matches.append(task_dict)
    if not matches:
        raise TaskLookupError(
            f"No dataset row found for repo={repo}, version={version}, code_file={code_file}."
        )
    if len(matches) > 1:
        # Prefer the first match but alert the caller so they can disambiguate later.
        print("[runner] Warning: multiple matching tasks found; defaulting to the first entry.")
    return matches[0]


def _prepare_task_instance(
    task: Dict[str, Any],
    test_src: str,
    model_name: str,
) -> Dict[str, Any]:
    task_instance = dict(task)
    task_instance[KEY_MODEL] = model_name
    task_instance[KEY_PREDICTIONS] = {"full": [test_src]}

    test_type = MAP_REPO_TO_TEST_FRAMEWORK[task_instance["repo"]]
    test_directives = get_test_directives(task_instance)
    task_instance["test_directives"] = test_directives
    task_instance["test_cmd"] = f"{test_type} {' '.join(test_directives)}"
    return task_instance


def _resolve_image(namespace: str, task_instance: Dict[str, Any]) -> str:
    repo_name = task_instance["repo"].replace("/", "_")
    specifications = MAP_VERSION_TO_INSTALL[task_instance["repo"]][task_instance["version"]]
    image_prefix = "swe-bench"
    if specifications.get("instance_image", False):
        return (
            f"{namespace}/{image_prefix}-{repo_name}-instance:" f"{task_instance[KEY_INSTANCE_ID]}"
        )
    return f"{namespace}/{image_prefix}-{repo_name}-testbed:{task_instance['version']}"


def _ensure_image(namespace: str, task_instance: Dict[str, Any]) -> str:
    image_name = _resolve_image(namespace, task_instance)
    inspect = subprocess.run(
        ["docker", "image", "inspect", image_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        text=True,
    )
    if inspect.returncode != 0:
        pull = subprocess.run(["docker", "pull", image_name], check=False)
        if pull.returncode != 0:
            raise RuntimeError(f"Failed to pull Docker image: {image_name}")
    return image_name


async def _run_evaluation_async(
    task_instance: Dict[str, Any],
    namespace: str,
    log_dir: str,
    timeout: int,
    skip_mutation: bool,
    apply_dataset_patch: bool,
) -> None:
    # Always overwrite the specific log file before running to avoid stale parsing.
    log_pattern = os.path.join(
        log_dir, f"{task_instance[KEY_ID]}.{task_instance[KEY_MODEL]}.*.eval.log"
    )
    for stale_log in glob.glob(log_pattern):
        os.remove(stale_log)

    await run_docker_evaluation(
        task_instance=task_instance,
        namespace=namespace,
        log_dir=log_dir,
        setting="full",
        ind=0,
        timeout=timeout,
        only_baseline=False,
        skip_mutation=skip_mutation,
        skip_dataset_patch=not apply_dataset_patch,
    )


def run_custom_test(
    repo: str,
    version: str,
    code_file: str,
    test_src: str,
    *,
    dataset: str = DEFAULT_DATASET,
    namespace: str = DEFAULT_NAMESPACE,
    results_root: str = DEFAULT_RESULTS_ROOT,
    model_name: str = DEFAULT_MODEL_NAME,
    timeout: int = 900,
    skip_mutation: bool = True,
    apply_dataset_patch: bool = False,
) -> CustomRunResult:
    """Run a single custom full-file test inside the appropriate SWE-bench container."""

    dataset_refs = get_eval_refs(dataset)
    task = _select_task(dataset_refs, repo, version, code_file)
    task_instance = _prepare_task_instance(task, test_src, model_name)
    _ensure_image(namespace, task_instance)

    repo_sanitized = repo.replace("/", "__")
    log_dir = os.path.abspath(os.path.join(results_root, repo_sanitized, version, "logs"))
    os.makedirs(log_dir, exist_ok=True)
    os.chmod(log_dir, 0o777)

    try:
        asyncio.run(
            _run_evaluation_async(
                task_instance,
                namespace=namespace,
                log_dir=log_dir,
                timeout=timeout,
                skip_mutation=skip_mutation,
                apply_dataset_patch=apply_dataset_patch,
            )
        )
    except RuntimeError as exc:
        if "event loop" in str(exc):
            raise RuntimeError(
                "run_custom_test must be invoked from a synchronous context."
            ) from exc
        raise

    log_path = os.path.join(
        log_dir,
        f"{task_instance[KEY_ID]}.{task_instance[KEY_MODEL]}.full.eval.log",
    )
    if not os.path.exists(log_path):
        raise RuntimeError("Evaluation did not produce a log file. Check docker output for errors.")

    log_metrics = get_logs_eval(log_path)
    full_metrics = log_metrics.get("full", {})
    coverage = None
    passed = False
    test_error = "Unknown"
    if full_metrics:
        coverage_values = full_metrics.get("coverage", [])
        coverage = coverage_values[0] if coverage_values else None
        passed_values = full_metrics.get("tests_passed", [])
        passed = passed_values[0] if passed_values else False
        test_error_values = full_metrics.get("test_error", [])
        test_error = test_error_values[0] if test_error_values else "Unknown"

    with open(log_path, "r", encoding="utf-8") as log_file:
        log_text = log_file.read()

    baseline_cov = None
    if isinstance(task.get("baseline_covs"), dict):
        baseline_cov = task["baseline_covs"].get("full")

    return CustomRunResult(
        task_id=task[KEY_ID],
        instance_id=task[KEY_INSTANCE_ID],
        repo=repo,
        version=version,
        code_file=code_file,
        log_path=log_path,
        coverage=coverage,
        passed=passed,
        test_error=test_error,
        log_text=log_text,
        baseline_coverage=baseline_cov,
    )
