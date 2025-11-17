from __future__ import annotations
import pathlib, sys


def _ensure_src_on_path() -> None:
    root = pathlib.Path(__file__).resolve().parents[1]
    src_path = root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))


_ensure_src_on_path()
