from flask import Flask, request, jsonify
from single_runner import run_custom_test
import os
import uuid
from repo_checkout import local_repo_checkout
import subprocess
from datasets import load_dataset




app = Flask(__name__)

DATASET = load_dataset("kjain14/testgenevallite", split="test")

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
        print("DEBUG RESULT:", result.__dict__)

    except Exception as e:
        print("🔥 RUNNER ERROR:", e)         # <--- ADD THIS

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

# @app.route("/code", methods=["POST"])
# def get_code():
#     if not request.is_json:
#         return jsonify({"error": "Expected application/json"}), 400

#     payload = request.get_json()
#     required = {"repo", "version", "code_file"}
#     missing = required - payload.keys()
#     if missing:
#         return jsonify({"error": f"Missing fields: {', '.join(sorted(missing))}"}), 400

#     repo = payload["repo"]
#     version = payload["version"]
#     code_file = payload["code_file"]

#     # Use swebench_docker to read the file INSIDE the docker image
#     cmd = [
#         "python",
#         "-m",
#         "swebench_docker.run_docker",
#         "--repo",
#         repo,
#         "--version",
#         version,
#         "--mode",
#         "cat_file",
#         "--file",
#         code_file
#     ]

#     result = subprocess.run(cmd, capture_output=True, text=True)

#     if result.returncode != 0:
#         return jsonify({
#             "error": "Failed to fetch file",
#             "stderr": result.stderr,
#             "status": "error"
#         }), 500

#     return jsonify({"contents": result.stdout}), 200


@app.route("/code", methods=["POST"])
def get_code():
    if not request.is_json:
        return jsonify({"error": "Expected application/json"}), 400

    payload = request.get_json()
    required = {"repo", "version", "code_file"}
    missing = required - payload.keys()
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(sorted(missing))}"}), 400

    repo = payload["repo"]
    version = payload["version"]
    code_file = payload["code_file"]

    # Filter dataset
    rows = DATASET.filter(
        lambda x: x["repo"] == repo and
                  x["version"] == version and
                  x["code_file"] == code_file
    )

    if len(rows) == 0:
        return jsonify({
            "error": "No matching entry found in dataset",
            "repo": repo,
            "version": version,
            "code_file": code_file
        }), 404

    row = rows[0]

    return jsonify({
        "status": "ok",
        "repo": repo,
        "version": version,
        "code_file": code_file,
        "contents": row["code_src"]
    }), 200
# @app.route("/code", methods=["POST"])
# def get_code_file():
#     """
#     Return the contents of a file in the target repo using LOCAL checkout.
#     """
#     from repo_checkout import local_repo_checkout  # NEW IMPORT

#     if not request.is_json:
#         return jsonify({"error": "Expected application/json"}), 400

#     payload = request.get_json()
#     required = {"repo", "version", "code_file"}
#     missing = required - payload.keys()
#     if missing:
#         return jsonify({"error": f"Missing fields: {', '.join(sorted(missing))}"}), 400

#     repo = payload["repo"]
#     version = payload["version"]
#     code_file = payload["code_file"]

#     try:
#         repo_path = local_repo_checkout(
#             dataset="kjain14/testgenevallite",
#             repo=repo,
#             version=version,
#             results_root="results"
#         )

#         full_path = os.path.join(repo_path, code_file)
#         if not os.path.exists(full_path):
#             return jsonify({
#                 "error": f"File not found inside checkout: {full_path}",
#                 "repo_path": repo_path
#             }), 404

#         with open(full_path, "r", encoding="utf-8") as f:
#             contents = f.read()

#         return jsonify({
#             "status": "ok",
#             "repo_path": repo_path,
#             "code_file": code_file,
#             "contents": contents,
#         })

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500




if __name__ == "__main__":
    # Host on localhost:3000
    print("Starting runner server on http://localhost:3000")
    app.run(host="127.0.0.1", port=3000, debug=True)
