#!/bin/bash
# Manual bulk run - edit the commands below to add your test cases
# Usage: ./scripts/run_bulk_manual.sh

set -e

export LLM_SUPERVISOR=true

# Edit these commands to add your test cases
# Each line is a separate orchestrator run

python -m src.orchestrator.engine --repo django/django --version 4.0 --code-file django/db/models/query_utils.py --max-iters 2

python -m src.orchestrator.engine --repo django/django --version 4.1 --code-file django/views/static.py --max-iters 2

python -m src.orchestrator.engine --repo django/django --version 4.2 --code-file django/utils/numberformat.py --max-iters 2

python -m src.orchestrator.engine --repo django/django --version 3.0 --code-file django/utils/autoreload.py --max-iters 2

python -m src.orchestrator.engine --repo django/django --version 3.1 --code-file django/db/models/lookups.py --max-iters 2

# Add more commands as needed...

