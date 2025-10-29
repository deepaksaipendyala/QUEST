from __future__ import annotations
import os
import pathlib
import yaml
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    runner_url: str
    target_coverage: float


def load_config() -> AppConfig:
    cfg_path = pathlib.Path("configs/default.yaml")
    with cfg_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    runner_url = os.getenv("RUNNER_URL", raw.get("runner_url", "http://localhost:3000/runner"))
    target_coverage = float(raw.get("targets", {}).get("coverage", 60.0))
    return AppConfig(runner_url=runner_url, target_coverage=target_coverage)
