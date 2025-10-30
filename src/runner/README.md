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
- `POST /runner` - Runs tests and calculates coverage for a specific repository

### POST /runner

Runs tests against a GitHub repository and calculates code coverage for a specific source file.

#### Request Body

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

#### Response

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

## Sample Request
```bash
curl --location 'http://localhost:3000/runner' \
--header 'Content-Type: application/json' \
--data '{
  "repo": "encode/httpx",
  "version": "0.24.0",
  "code_file": "httpx/_client.py",
  "test_src": "import httpx\n\ndef test_client_creation():\n    client = httpx.Client()\n    assert client is not None\n\ndef test_async_client():\n    client = httpx.AsyncClient()\n    assert client is not None\n"
}'
```

## Features

- **Repository Caching**: Cloned repositories are cached in `/tmp/gai4se/` to speed up subsequent requests
- **Coverage Analysis**: Uses `pytest-cov` to calculate line coverage for specific source files
- **Virtual Environment**: Each repository has its own isolated Python virtual environment
- **Dependency Management**: Automatically installs dependencies from `requirements.txt` and the package itself in editable mode
- **Multiple Test Cases**: Supports running multiple test cases in a single request