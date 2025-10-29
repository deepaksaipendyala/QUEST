from __future__ import annotations
import pathlib, sys

root = pathlib.Path(__file__).resolve().parent.parent
src_path = root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
