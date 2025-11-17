from pydantic import BaseModel, Field, ConfigDict
from typing import List, Literal

Status = Literal["passed", "failed", "no_tests_collected", "error"]


class RunnerRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    repo: str = Field(min_length=3)
    version: str = Field(min_length=1)
    code_file: str = Field(min_length=1)
    test_src: str = Field(min_length=1)


class CoverageDetailsModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    covered_lines: int
    num_statements: int
    missing_lines: List[int]
    excluded_lines: List[int]


class RunnerResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Status
    success: bool
    exitCode: int
    executionTime: float
    coverage: float
    coverageDetails: CoverageDetailsModel
    stdout: str
    stderr: str
    repoPath: str
    code_file: str
    test_error: str
    task_id: str
    instance_id: str
    log_path: str
    mutation_score: float
    mutation_uncertainty: float
    mutation_num: float
