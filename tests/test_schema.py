import pytest
pytest.importorskip("pydantic")  # offline envs without pydantic will skip

from src.core.schema import RunnerRequestModel, CoverageDetailsModel  # type: ignore

def test_request_model_ok():
    RunnerRequestModel(repo="o/r", version="v", code_file="x.py", test_src="def test_x(): pass")

def test_response_model_ok():
    CoverageDetailsModel(
        covered_lines=1, num_statements=1, missing_lines=[], excluded_lines=[]
    )
