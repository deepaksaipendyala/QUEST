from __future__ import annotations
import json, time, uuid, pathlib
from typing import Any


def new_run_id() -> str:
    return f"run_{int(time.time()*1000)}_{uuid.uuid4().hex[:8]}"


def run_dir(run_id: str) -> pathlib.Path:
    p = pathlib.Path("artifacts") / "runs" / run_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_json(path: pathlib.Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def write_text(path: pathlib.Path, s: str) -> None:
    path.write_text(s, encoding="utf-8")
