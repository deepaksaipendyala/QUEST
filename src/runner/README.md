# Runner - Bun HTTP Server

A lightweight HTTP server built with Bun and TypeScript.

## Prerequisites

- [Bun](https://bun.sh) installed on your system

## Installation

```bash
bun install
```

## Development

Run the server in development mode with hot reload:

```bash
bun run dev
```

## Production

Run the server in production mode:

```bash
bun run start
```

## API Endpoints

- `GET /` - Returns a welcome message
- `GET /health` - Returns server health status
- `POST /lint` - Lints provided test source code with Ruff
- `POST /runner` - Runs tests and calculates coverage for a specific repository

### POST /lint

Runs Ruff linting against the provided test source code inside the repository's virtual environment.

#### Request Body (Lint)

```json
{
  "repo": "owner/repository",
  "version": "version-tag",
  "test_src": "test source code as string"
}
```

**Parameters:**

- `repo` (string, required): GitHub repository in format "owner/repo"
- `version` (string, required): Git tag/branch version to checkout
- `test_src` (string, required): Python test code to lint

#### Response (Lint)

```json
{
  "status": "clean" | "violations" | "error",
  "success": true | false,
  "exitCode": 0,
  "executionTime": 0.42,
  "issueCount": 0,
  "issues": [
    {
      "code": "F401",
      "message": "`pytest` imported but unused",
      "filename": "temp_lint_1699999999999.py",
      "location": { "row": 3, "column": 1 }
    }
  ],
  "stdout": "...raw Ruff output...",
  "stderr": "...",
  "repoPath": "/tmp/gai4se/owner__repo_version",
  "parseError": "optional parse warning"
}
```

**Response Fields:**

- `status`: Lint outcome (`clean` when no violations, `violations` when issues are found)
- `success`: Whether Ruff exited with code 0
- `exitCode`: Ruff exit code (0 clean, 1 violations, >1 errors)
- `executionTime`: Time taken to lint (in seconds)
- `issueCount`: Number of reported lint violations (null if output parsing failed)
- `issues`: Array of Ruff issues (empty when clean)
- `stdout` / `stderr`: Raw outputs from Ruff
- `repoPath`: Absolute path to cloned repository
- `parseError`: Present only when the Ruff JSON output could not be parsed

### POST /runner

Runs tests against a GitHub repository and calculates code coverage for a specific source file.

#### Request Body (Runner)

```json
{
    "repo": "owner/repository",
    "version": "version-tag",
    "test_src": "test source code as string",
    "code_file": "path/to/source/file.py"
}
```

**Parameters:**

- `repo` (string, required): GitHub repository in format "owner/repo"
- `version` (string, required): Git tag/branch version to checkout
- `test_src` (string, required): Python test code (can contain multiple test cases)
- `code_file` (string, required): Path to the source file to calculate coverage for (relative to repo root)

#### Response (Runner)

```json
{
    "status": "passed" | "failed" | "no_tests_collected" | "error",
    "success": true | false,
    "exitCode": 0,
    "executionTime": 1.23,
    "coverage": 85.5,
    "coverageDetails": {
        "covered_lines": 100,
        "num_statements": 117,
        "missing_lines": [10, 15, 20],
        "excluded_lines": []
    },
    "stdout": "test output...",
    "stderr": "error output...",
    "repoPath": "/tmp/gai4se/owner__repo_version",
    "code_file": "path/to/source/file.py"
}
```

**Response Fields:**

- `status`: Test execution status
- `success`: Whether tests passed
- `exitCode`: Pytest exit code
- `executionTime`: Time taken to run tests (in seconds)
- `coverage`: Percentage of lines covered in the specified code file (0-100)
- `coverageDetails`: Detailed coverage information
  - `covered_lines`: Number of lines executed
  - `num_statements`: Total number of executable statements
  - `missing_lines`: Line numbers not covered by tests
  - `excluded_lines`: Lines excluded from coverage
- `stdout`: Standard output from test execution
- `stderr`: Standard error output
- `repoPath`: Absolute path to cloned repository
- `code_file`: The code file that coverage was calculated for

The server runs on `http://localhost:3000` by default.

## Sample Requests

```bash
curl --location 'http://localhost:3000/runner' \
--header 'Content-Type: application/json' \
--data '{
  "repo": "encode/httpx",
  "version": "0.24.0",
  "code_file": "httpx/_client.py",
  "test_src": "import httpx\n\ndef test_client_creation():\n    client = httpx.Client()\n    assert client is not None\n\ndef test_async_client():\n    client = httpx.AsyncClient()\n    assert client is not None\n"
}'

curl --location 'http://localhost:3000/lint' \
--header 'Content-Type: application/json' \
--data '{
  "repo": "encode/httpx",
  "version": "0.24.0",
  "test_src": "import httpx\n\n\ndef test_client_creation():\n    client = httpx.Client()\n    assert client is not None\n"
}'
```

## Features

- **Repository Caching**: Cloned repositories are cached in `/tmp/gai4se/` to speed up subsequent requests
- **Linting Support**: Uses `ruff` to lint generated tests prior to execution
- **Coverage Analysis**: Uses `coverage` to calculate line coverage for specific source files
- **Virtual Environment**: Each repository has its own isolated Python virtual environment
- **Dependency Management**: Automatically installs dependencies from `requirements.txt` and the package itself in editable mode
- **Multiple Test Cases**: Supports running multiple test cases in a single request
