#!/bin/bash
# Simple bulk run script for orchestrator
# Usage: ./scripts/run_bulk_simple.sh

set -e

# Configuration
MAX_ITERS=2
LLM_SUPERVISOR=true

# Export environment variables
export LLM_SUPERVISOR=$LLM_SUPERVISOR

# Array of test cases: repo version code_file
test_cases=(
    "django/django 4.0 django/db/models/query_utils.py"
    "django/django 4.1 django/views/static.py"
    "django/django 4.2 django/utils/numberformat.py"
    "django/django 3.0 django/utils/autoreload.py"
    "django/django 3.1 django/db/models/lookups.py"
    "django/django 3.2 django/db/models/base.py"
    "django/django 4.0 django/contrib/auth/forms.py"
    "django/django 4.1 django/utils/decorators.py"
    "django/django 4.2 django/core/management/base.py"
    "django/django 4.0 django/contrib/admin/sites.py"
)

total=${#test_cases[@]}
success=0
failures=0

echo "Starting bulk run: $total test cases"
echo "Max iterations: $MAX_ITERS"
echo "LLM Supervisor: $LLM_SUPERVISOR"
echo ""

for i in "${!test_cases[@]}"; do
    test_case="${test_cases[$i]}"
    read -r repo version code_file <<< "$test_case"
    
    num=$((i + 1))
    echo ">>> [$num/$total] repo=$repo version=$version code_file=$code_file"
    
    if python -m src.orchestrator.engine --repo "$repo" --version "$version" --code-file "$code_file" --max-iters "$MAX_ITERS"; then
        ((success++))
        echo "[OK] Test case $num completed successfully"
    else
        ((failures++))
        echo "[FAIL] Test case $num failed"
    fi
    echo ""
done

echo "=========================================="
echo "Bulk run completed:"
echo "  Total: $total"
echo "  Success: $success"
echo "  Failures: $failures"
echo "=========================================="

exit $failures

