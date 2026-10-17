# Branch Sync — Main/Master Merge Pattern

## Problem

When a GitHub repo has both `master` and `main` branches, the default branch (`master`) is connected to the custom domain, but code is pushed to `main`. This causes the website to show stale content.

## Solution

Always merge `main` INTO `master` and force-push `master`:

```bash
# 1. Switch to master
git checkout master

# 2. Merge main into master (main has newer code)
git merge main --no-edit

# 3. Push master (may need --force since master history is rewritten)
git push origin master --force

# 4. Also push main to keep it in sync
git checkout main
git push origin main

# 5. Verify both branches are identical
git log --oneline master
git log --oneline main
git diff master..main --stat  # Should show no differences
```

## Key Insight

- `master` is the DEFAULT branch connected to the domain `www.dreamzdccompound.shop`
- `main` is where new code is pushed
- Merging `main` into `master` ensures the domain shows the latest code
- After merging, both branches should have identical commit history

## Verification

```bash
# Check both branches have same commits
git branch -a
git log --oneline -3 master
git log --oneline -3 main

# Verify GitHub
gh api repos/OWNER/REPO/branches/master --jq '.name'
gh api repos/OWNER/REPO/branches/main --jq '.name'
```

## Common Pitfalls

- **Push rejected on master**: `git push origin master --force` — master history was rewritten by the merge
- **Already up to date but still behind**: `git pull origin master --force --allow-unrelated-histories` then merge again
- **Accidentally resetting main to an old commit**: Always `git reset --hard master` before force-pushing main
