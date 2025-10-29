from __future__ import annotations
import pathlib, ast
from typing import List
from src.contracts.messages import ContextPack

def read_file(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")

def mine_python_context(repo_root: pathlib.Path, relative_code_file: str) -> ContextPack:
    p = (repo_root / relative_code_file).resolve()
    if not p.exists():
        return {"summary": "", "symbols": [], "docstrings": []}
    text = read_file(p)
    try_ast = ast.parse(text)
    symbols: List[str] = []
    docstrings: List[str] = []
    for node in try_ast.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.append(node.name)
            ds = ast.get_docstring(node)
            if ds:
                docstrings.append(ds.splitlines()[0][:120])
    summary = (ast.get_docstring(try_ast) or "").splitlines()[0][:160] if ast.get_docstring(try_ast) else ""
    return {"summary": summary, "symbols": symbols, "docstrings": docstrings}
