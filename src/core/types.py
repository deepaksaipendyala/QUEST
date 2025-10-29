from typing import List, Literal, TypedDict

Status = Literal["passed", "failed", "no_tests_collected", "error"]


class RunnerRequest(TypedDict):
    repo: str
    version: str
    code_file: str
    test_src: str


class CoverageDetails(TypedDict):
    covered_lines: int
    num_statements: int
    missing_lines: List[int]
    excluded_lines: List[int]


class RunnerResponse(TypedDict):
    status: Status
    success: bool
    exitCode: int
    executionTime: float
    coverage: float
    coverageDetails: CoverageDetails
    stdout: str
    stderr: str
    repoPath: str
    code_file: str
