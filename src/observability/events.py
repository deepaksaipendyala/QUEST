from __future__ import annotations
import time, pathlib

def append_event(path: pathlib.Path, msg: str) -> None:
    line = f"t={int(time.time()*1000)} {msg}\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line)
