# Git Commands for Retrieving Commits

This document contains useful Git commands for viewing and retrieving commit information.

## Basic Commit History

### View commit history
```bash
# Show full commit history with details
git log

# Show one-line summary of commits
git log --oneline

# Show last N commits (replace N with number)
git log -n 5

# Show commits in a specific date range
git log --since="2025-11-01" --until="2025-11-30"

# Show commits by a specific author
git log --author="deepaksaipendyala"
```

### Custom formatted commit history
```bash
# Show commits with hash, author, email, date, and message
git log --pretty=format:"%H|%an|%ae|%ad|%s" --date=iso

# Show commits with hash and message only
git log --pretty=format:"%h - %s"

# Show commits with full details
git log --format=fuller

# Show commits with graph visualization
git log --graph --oneline --all
```

## Viewing Specific Commits

### View latest commit
```bash
# Show latest commit with full diff
git show HEAD

# Show latest commit with file statistics
git show --stat HEAD

# Show latest commit message only
git show --no-patch --format="%s" HEAD
```

### View specific commit by hash
```bash
# Replace <commit-hash> with actual commit hash (e.g., 0e43d42c6c9f44c98257fcd0b29576be2b88f0ff)
git show <commit-hash>

# Show specific commit with statistics
git show --stat <commit-hash>

# Show specific commit message only
git show --no-patch <commit-hash>
```

### View previous commits
```bash
# Show parent commit (one commit before HEAD)
git show HEAD~1

# Show grandparent commit (two commits before HEAD)
git show HEAD~2

# Show commit N steps before HEAD
git show HEAD~N
```

## Viewing Commit Objects Directly

### Access raw commit objects
```bash
# View raw commit object content
git cat-file -p HEAD

# View raw commit object by hash
git cat-file -p <commit-hash>

# Get object type (commit, tree, or blob)
git cat-file -t <commit-hash>

# Get object size
git cat-file -s <commit-hash>
```

## Viewing Files in Commits

### List files changed in a commit
```bash
# List files changed in latest commit
git show --name-only HEAD

# List files with status (Added, Modified, Deleted)
git show --name-status HEAD

# List files with statistics
git show --stat HEAD

# List files changed in specific commit
git show --name-only <commit-hash>
```

### View file contents at specific commit
```bash
# View a file as it was in a specific commit
git show <commit-hash>:<file-path>

# View a file as it was in HEAD
git show HEAD:<file-path>

# Compare file between two commits
git diff <commit-hash-1> <commit-hash-2> -- <file-path>
```

## Comparing Commits

### Compare commits
```bash
# Compare two commits
git diff <commit-hash-1> <commit-hash-2>

# Compare current HEAD with previous commit
git diff HEAD~1 HEAD

# Compare with statistics
git diff --stat <commit-hash-1> <commit-hash-2>

# Show what changed between commits
git log <commit-hash-1>..<commit-hash-2>
```

## Finding Commits

### Search commits
```bash
# Search commits by message content
git log --grep="search term"

# Search commits that changed a specific file
git log -- <file-path>

# Search commits that changed specific text in code
git log -S "search text" --source --all

# Find commits that introduced or removed a string
git log -p -S "function_name"
```

### Find commit by message
```bash
# Find commit with specific message pattern
git log --all --grep="Initial commit"

# Case-insensitive search
git log -i --grep="initial commit"
```

## Git Repository Structure

### View Git internal files
```bash
# View current branch reference
cat .git/refs/heads/main

# View HEAD reference
cat .git/HEAD

# List all objects in Git database
find .git/objects/ -type f

# Count total objects
find .git/objects/ -type f | wc -l
```

## Save All Commits

### Save all commits to files
```bash
# Save all commits in pipe-delimited format (hash|author|email|date|message)
git log --pretty=format:"%H|%an|%ae|%ad|%s" --date=iso > all_commits.txt

# Save all commits in JSON format (one JSON object per line)
git log --pretty=format:'{"hash":"%H","author":"%an","email":"%ae","date":"%ad","message":"%s"}' --date=iso > all_commits.json

# Save all commits with detailed information including parent commits
git log --all --pretty=format:"%H|%an|%ae|%ad|%s|%P" --date=iso --decorate > all_commits_detailed.txt

# Save all commits with full diff information
git log -p > all_commits_with_diffs.txt

# Save all commits with file statistics
git log --stat > all_commits_with_stats.txt
```

### Save commits with additional information
```bash
# Save commits with branch and tag information
git log --all --pretty=format:"%H|%an|%ae|%ad|%s|%D" --date=iso > all_commits_with_refs.txt

# Save commits with tree hash
git log --pretty=format:"%H|%T|%an|%ae|%ad|%s" --date=iso > all_commits_with_tree.txt

# Save commits in a format suitable for CSV import
git log --pretty=format:"%H,%an,%ae,%ad,%s" --date=iso > all_commits.csv
```

## Export Commit Information

### Export commit history to file
```bash
# Export commit log to text file
git log > commit_history.txt

# Export with custom format
git log --pretty=format:"%H|%an|%ae|%ad|%s" --date=iso > commits.csv

# Export as JSON (requires jq or custom script)
git log --pretty=format:'{"hash":"%H","author":"%an","email":"%ae","date":"%ad","message":"%s"}' > commits.json
```

## Useful Aliases (Optional)

You can add these to your `~/.gitconfig` file for convenience:

```bash
# Add aliases
git config --global alias.lg "log --oneline --graph --all"
git config --global alias.ls "log --stat"
git config --global alias.ll "log --pretty=format:'%C(yellow)%h%Creset - %s %C(green)(%cr)%Creset %C(blue)<%an>%Creset'"

# Then use:
git lg    # Pretty graph view
git ls    # Log with stats
git ll    # Custom formatted log
```

## Examples

### Example 1: View last 3 commits with details
```bash
git log -3 --pretty=format:"%h - %an, %ar : %s"
```

### Example 2: Find all commits that modified a specific file
```bash
git log --follow -- <file-path>
```

### Example 3: View commit and all changed files
```bash
git show HEAD --stat --name-status
```

### Example 4: Get commit hash of latest commit
```bash
git rev-parse HEAD
```

### Example 5: View commit tree structure
```bash
git ls-tree -r HEAD
```

