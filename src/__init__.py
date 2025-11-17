from __future__ import annotations
import importlib.util
import sys
import types
from typing import Any, Dict, List, NoReturn, Tuple

def _ensure_requests_stub() -> None:
    if "requests" in sys.modules:
        return
    if importlib.util.find_spec("requests") is not None:
        return
    stub = types.SimpleNamespace()

    def _unavailable(*args: object, **kwargs: object) -> NoReturn:
        raise RuntimeError("requests module not available")

    stub.post = _unavailable  # type: ignore[attr-defined]
    sys.modules["requests"] = stub

def _ensure_yaml_stub() -> None:
    if "yaml" in sys.modules:
        return
    if importlib.util.find_spec("yaml") is not None:
        return

    yaml_module = types.ModuleType("yaml")

    def _parse_scalar(value: str) -> object:
        if not value:
            return ""
        if value.startswith('"') and value.endswith('"'):
            return value[1:-1]
        normalized = value.replace("-", "", 1)
        numeric = normalized.replace(".", "", 1)
        if numeric.isdigit():
            return float(value) if "." in value else int(value)
        return value

    def safe_load(source: Any) -> Dict[str, object]:
        if isinstance(source, str):
            text = source
        else:
            read_method = getattr(source, "read", None)
            if read_method is None or not callable(read_method):
                raise TypeError("yaml.safe_load expects a string or file-like object")
            text = read_method()
        if not isinstance(text, str):
            raise TypeError("yaml.safe_load expected string content")
        result: Dict[str, object] = {}
        stack: List[Tuple[int, Dict[str, object]]] = [(-1, result)]
        for raw_line in text.splitlines():
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(raw_line) - len(raw_line.lstrip(" "))
            level = indent // 2
            if ":" not in stripped:
                continue
            key, value_part = stripped.split(":", 1)
            key = key.strip()
            value_part = value_part.strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            parent = stack[-1][1] if stack else result
            if value_part:
                parent[key] = _parse_scalar(value_part)
            else:
                nested: Dict[str, object] = {}
                parent[key] = nested
                stack.append((level, nested))
        return result

    yaml_module.safe_load = safe_load  # type: ignore[attr-defined]
    sys.modules["yaml"] = yaml_module

_ensure_requests_stub()
_ensure_yaml_stub()
