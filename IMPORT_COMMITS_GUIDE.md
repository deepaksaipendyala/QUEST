# Guide to Import Commits from all_commits.txt

This guide explains how to import the commits listed in `all_commits.txt` into the current repository.

## Option 1: Using the Import Script (Recommended)

If you have access to the source repository, use the provided script:

```bash
# Make sure you have the correct repository URL
# Update the SOURCE_REPO_URL in import_commits.sh if needed

# Run the import script
./import_commits.sh [SOURCE_REPO_URL]
```

The script will:
1. Add the source repository as a remote
2. Fetch all commits
3. Cherry-pick each commit from `all_commits.txt` in chronological order
4. Create a new branch with all imported commits

## Option 2: Manual Import with Remote Access

If you have SSH or HTTPS access to the source repository:

```bash
# Add the source repository as a remote
git remote add source-repo <REPOSITORY_URL>

# Fetch commits
git fetch source-repo

# Cherry-pick commits in order (oldest to newest)
# Extract commit hashes from all_commits.txt and cherry-pick each one
git cherry-pick 5b22e50844a355efab90442106437e9f5b67ce7b
git cherry-pick 66d03d931e9ff72703b4e7a3e1e53d07bc402842
git cherry-pick 958b91bea007004fbd2656c65656d8b7ada5deed
# ... continue for all commits
```

## Option 3: Import from Local Repository

If you have the source repository cloned locally:

```bash
# Add local repository as remote
git remote add source-repo /path/to/source/repository

# Fetch commits
git fetch source-repo

# Cherry-pick commits (same as Option 2)
```

## Option 4: GitHub Enterprise (gh-ncsu)

If the repository is on GitHub Enterprise (gh-ncsu), you'll need to:

1. Update the repository URL in `import_commits.sh` to use the Enterprise URL
2. Ensure you have proper authentication set up
3. Use SSH if available: `git@gh-ncsu:hbharat2_ncstate/CSC591-GenerativeAIforSE_TestgenEval.git`

## Commit List from all_commits.txt

The commits to import (in chronological order, oldest first):

1. `5b22e50844a355efab90442106437e9f5b67ce7b` - chore: initial commit
2. `66d03d931e9ff72703b4e7a3e1e53d07bc402842` - feat: add runner
3. `958b91bea007004fbd2656c65656d8b7ada5deed` - 🚿
4. `1c29db3fc5c185addba8aca994169a846c84feac` - feat: TestgenEval integration
5. `a03acda1a35262211f3eb4217f5222ba956378cc` - feat(runner): add POST /lint endpoint
6. `9cf00ac72415209616e35a5d0e9ded725f200aee` - chore(runner): use .venv as folder
7. `81d55f2c976a21d8e29b3374702e26320185028d` - chore(runner): add lint example w/ issues
8. `b498c2f9464bcfd0e0d3c2113aaad6f58e08134c` - Merge branch 'main' of gh-ncsu:hbharat2_ncstate/CSC591-GenerativeAIforSE_TestgenEval
9. `a50c0332350457e7c10df28b58d409889d9c17dd` - 🚿
10. `512e395c744e790e61df5553d80468f7d286878c` - fix(llm): fix toy test_src
11. `8888e4202a130bf947b97cb1faed7026b4c4d671` - init
12. `8fb874d6262778d8e1faa16158df19abfd6a8756` - 🚿
13. `a49f294964aa7ba398e03b4be3972d761098c6b7` - feat(runner): flask app + changes
14. `06302a65e188f49399517355d6b1fea80dc769e3` - 🚿

## Troubleshooting

### Authentication Issues

If you get authentication errors:
- For HTTPS: Use a personal access token or update your credentials
- For SSH: Ensure your SSH key is added to the GitHub account
- For Enterprise: Contact your organization admin for access

### Commit Already Exists

If a commit already exists in your repository, cherry-pick will skip it. This is normal if you're re-running the import.

### Merge Conflicts

If you encounter merge conflicts during cherry-pick:
1. Resolve conflicts manually
2. `git add <resolved-files>`
3. `git cherry-pick --continue`

### Repository Not Found

If the repository URL is incorrect or the repository is private:
1. Verify you have access to the repository
2. Check the repository URL format
3. Update the URL in `import_commits.sh` or use the manual method

## After Import

Once commits are imported:

```bash
# Review the imported commits
git log --oneline

# If you created a branch, merge it to main
git checkout main
git merge import-commits-<timestamp>

# Or rebase if you prefer
git checkout main
git rebase import-commits-<timestamp>
```

