import os
import subprocess
import shutil
from pathlib import Path
from gitrepo.swebench_docker.utils import get_eval_refs


def local_repo_checkout(dataset, repo, version, results_root):
    """
    Clone repo locally (NOT inside Docker) and checkout the exact dataset version.
    Returns a path to the local repo clone.
    """

    # Load dataset references
    dataset_refs = get_eval_refs(dataset)

    # Find the matching task (first match only)
    match_task = None
    for task_id, task in dataset_refs.items():
        if task["repo"] == repo and task["version"] == version:
            match_task = task
            break

    if match_task is None:
        raise ValueError(f"No matching dataset entry for {repo} {version}")

    # Where to clone the repo
    repo_sanitized = repo.replace("/", "__")
    target_dir = Path(results_root) / repo_sanitized / version / "repo"
    task_repo_dir = target_dir / f"{repo_sanitized}-{match_task['instance_id']}"

    if task_repo_dir.exists():
        shutil.rmtree(task_repo_dir)

    task_repo_dir.mkdir(parents=True, exist_ok=True)

    # Run git clone
    print(f"Cloning {repo} into {task_repo_dir}")
    subprocess.run(
        ["git", "clone", f"https://github.com/{repo}.git", str(task_repo_dir)],
        check=True,
    )

    # Checkout version
    print(f"Checking out version {version}")
    subprocess.run(
        ["git", "checkout", version],
        cwd=str(task_repo_dir),
        check=True,
    )

    return str(task_repo_dir)
