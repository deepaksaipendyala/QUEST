from __future__ import annotations
import os
import pathlib
import yaml
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    runner_url: str
    target_coverage: float
    target_mutation: float
    static_analysis_enabled: bool


def load_config() -> AppConfig:
    cfg_path = pathlib.Path("configs/default.yaml")
    if not cfg_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {cfg_path}\n"
            "Please ensure configs/default.yaml exists or create it with:\n"
            "  runner_url: http://localhost:3000/runner\n"
            "  targets:\n"
            "    coverage: 60.0"
        )
    with cfg_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid configuration: expected YAML dict, got {type(raw)}")
    runner_url = os.getenv("RUNNER_URL", raw.get("runner_url", "http://localhost:3000/runner"))
    targets = raw.get("targets", {}) or {}
    sa_cfg = raw.get("static_analysis", {}) or {}
    target_coverage = float(targets.get("coverage", 60.0))
    target_mutation = float(targets.get("mutation", 0.0))
    static_analysis_enabled = bool(
        os.getenv(
            "STATIC_ANALYSIS_ENABLED",
            sa_cfg.get("enable", False),
        )
    )

    return AppConfig(
        runner_url=runner_url,
        target_coverage=target_coverage,
        target_mutation=target_mutation,
        static_analysis_enabled=static_analysis_enabled,
    )
