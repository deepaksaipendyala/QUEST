from datasets import load_dataset
from single_runner import run_custom_test

ds = load_dataset("kjain14/testgenevallite", split="test")

code_file = "django/views/static.py"
version = "4.1"
repo = "django/django"

row = ds.filter(
    lambda x: x["repo"] == repo and x["version"] == version and x["code_file"] == code_file
)[-1]

test_snippet = row["test_src"]

# test_snippet = f"""
# # Dummy false test to check response
# assert False
# """

# test_snippet = f"""
# # Dummy true test to check response
# assert True
# """


if __name__ == "__main__":
    result = run_custom_test(
        repo=repo,
        version=version,
        code_file=code_file,
        test_src=test_snippet,
        dataset="kjain14/testgenevallite",
        namespace="kdjain",
        results_root="results/custom",
        timeout=300,
        skip_mutation=True,
        apply_dataset_patch=True,
    )

    print("Passed:", result.passed)
    print("Coverage:", result.coverage)
    print("Baseline Coverage:", result.baseline_coverage)
    print("Log Path:", result.log_path)
    print("Test Error:", result.test_error)
    print("Log snippet:\n", result.log_text.splitlines()[:20])
