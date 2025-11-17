import tempfile, pathlib
from src.context.miner import mine_python_context

def test_miner_symbols():
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "m.py"
        p.write_text("def foo():\n    pass\n", encoding="utf-8")
        c = mine_python_context(pathlib.Path(d), "m.py")
        assert "foo" in c["symbols"]
