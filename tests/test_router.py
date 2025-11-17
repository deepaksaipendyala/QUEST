from src.orchestrator.router import decide

def test_router_enhance_then_finish():
    c = {"compile_error": False, "no_tests": True, "low_coverage": True, "missing_lines":[1], "instructions":["x"]}
    assert decide(c, 0, 2) == "ENHANCE"
    assert decide(c, 2, 2) == "FINISH"
