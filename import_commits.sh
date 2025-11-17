#!/bin/bash

# Script to import commits from all_commits.txt into the current repository
# This script assumes you have access to the source repository

set -e

SOURCE_REPO_URL="${1:-https://github.com/hbharat2_ncstate/CSC591-GenerativeAIforSE_TestgenEval.git}"
COMMITS_FILE="all_commits.txt"

echo "Importing commits from $COMMITS_FILE"
echo "Source repository: $SOURCE_REPO_URL"
echo ""

# Check if commits file exists
if [ ! -f "$COMMITS_FILE" ]; then
    echo "Error: $COMMITS_FILE not found"
    exit 1
fi

# Add source repository as remote if it doesn't exist
if ! git remote | grep -q "^source-repo$"; then
    echo "Adding source repository as remote..."
    git remote add source-repo "$SOURCE_REPO_URL" || {
        echo "Note: Remote might already exist or URL needs to be updated"
        echo "Please update the SOURCE_REPO_URL in this script with the correct repository URL"
        exit 1
    }
fi

# Fetch commits from source repository
echo "Fetching commits from source repository..."
if ! git fetch source-repo; then
    echo ""
    echo "Error: Could not fetch from source repository."
    echo "Possible reasons:"
    echo "  1. Repository is private and requires authentication"
    echo "  2. Repository URL is incorrect"
    echo "  3. Repository is on GitHub Enterprise (gh-ncsu)"
    echo ""
    echo "If the repository is on GitHub Enterprise, update the URL in this script."
    echo "If you have the commits locally, you can:"
    echo "  1. Add the local repository as a remote: git remote add source-repo /path/to/repo"
    echo "  2. Or manually cherry-pick commits using: git cherry-pick <commit-hash>"
    exit 1
fi

# Extract commit hashes from all_commits.txt (first column, pipe-delimited)
echo "Extracting commit hashes from $COMMITS_FILE..."
COMMIT_HASHES=$(awk -F'|' '{print $1}' "$COMMITS_FILE" | tac)

# Check if we're on a clean working directory
if ! git diff-index --quiet HEAD --; then
    echo "Warning: You have uncommitted changes. Please commit or stash them first."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create a new branch for importing commits
BRANCH_NAME="import-commits-$(date +%Y%m%d-%H%M%S)"
echo "Creating branch: $BRANCH_NAME"
git checkout -b "$BRANCH_NAME"

# Cherry-pick each commit in reverse order (oldest first)
echo ""
echo "Cherry-picking commits..."
FAILED_COMMITS=()

for HASH in $COMMIT_HASHES; do
    # Skip empty lines
    [ -z "$HASH" ] && continue
    
    echo -n "Cherry-picking $HASH... "
    
    if git cherry-pick "$HASH" 2>/dev/null; then
        echo "✓"
    else
        echo "✗ (failed or already exists)"
        FAILED_COMMITS+=("$HASH")
        # Continue with next commit
        git cherry-pick --abort 2>/dev/null || true
    fi
done

echo ""
echo "Import complete!"
echo ""

if [ ${#FAILED_COMMITS[@]} -gt 0 ]; then
    echo "Failed commits (may already exist or have conflicts):"
    for HASH in "${FAILED_COMMITS[@]}"; do
        echo "  - $HASH"
    done
    echo ""
fi

echo "Current branch: $BRANCH_NAME"
echo ""
echo "Next steps:"
echo "  1. Review the commits: git log --oneline"
echo "  2. If everything looks good, merge to main:"
echo "     git checkout main"
echo "     git merge $BRANCH_NAME"
echo "  3. Or if you want to rebase instead:"
echo "     git checkout main"
echo "     git rebase $BRANCH_NAME"

