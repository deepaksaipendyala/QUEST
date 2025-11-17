from flask import Flask, request, jsonify
from single_runner import run_custom_test
import os
import uuid

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    return jsonify({"message": "TestGenEval Runner API"}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/runner", methods=["POST"])
def runner():
    if not request.is_json:
        return jsonify({"error": "Expected application/json"}), 400

    payload = request.get_json()
    required = {"repo", "version", "test_src", "code_file"}
    missing = required - payload.keys()
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(sorted(missing))}"}), 400

    repo = payload["repo"]
    version = payload["version"]
    test_src = payload["test_src"]
    code_file = payload["code_file"]

    results_root = f"results/{uuid.uuid4()}"
    skip_mutation = os.getenv("SKIP_MUTATION", "false").lower() == "true"

    try:
        result = run_custom_test(
            repo=repo,
            version=version,
            code_file=code_file,
            test_src=test_src,
            dataset="kjain14/testgenevallite",
            namespace="kdjain",
            results_root=results_root,
            timeout=300,
            skip_mutation=skip_mutation,
            apply_dataset_patch=True,
        )
    except Exception as e:
        error_response = {
            "error": str(e),
            "error_type": type(e).__name__,
            "status": "error",
            "success": False,
            "coverage": -1,
            "code_file": code_file,
        }
        return jsonify(error_response), 500

    api_response = {
        "status": "success" if result.passed else "failed",
        "success": result.passed,
        "exitCode": -1,
        "executionTime": 0.0,  # seconds
        "coverage": result.coverage if result.coverage is not None else -1,
        "coverageDetails": {},  # per-file or per-line coverage info
        "stdout": result.log_text,  # captured stdout from test run
        "stderr": "",
        "repoPath": "/dev/null",  # path to the repo in the runner env
        "code_file": code_file,
        "test_error": result.test_error,
        "task_id": result.task_id,
        "instance_id": result.instance_id,
        "log_path": result.log_path,
        "mutation_score": result.mutation_score,
        "mutation_uncertainty": result.mutation_uncertainty,
        "mutation_num": result.mutation_num,
    }

    return jsonify(api_response), 200


if __name__ == "__main__":
    # Host on localhost:3000
    print("Starting runner server on http://localhost:3000")
    app.run(host="127.0.0.1", port=3000)
