#!/bin/bash
# Start the TestGenEval runner server
# This script sets up the environment variables and starts the Flask server

# Get the absolute path of the script's directory (project root)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Set up environment variables using absolute paths
# PYTHONPATH needs both:
# 1. Parent directory of gitrepo (for 'from gitrepo.swebench_docker' imports)
# 2. gitrepo itself (for 'from swebench_docker' imports inside gitrepo files)
export PYTHONPATH="$SCRIPT_DIR:$SCRIPT_DIR/gitrepo:$PYTHONPATH"
export SWEBENCH_DOCKER_FORK_DIR="$SCRIPT_DIR/gitrepo"
export SKIP_MUTATION="${SKIP_MUTATION:-false}"

# Navigate to runner directory
cd "$SCRIPT_DIR/src/runner"

# Use conda Python to run the server
/opt/anaconda3/envs/testgeneval/bin/python server.py

