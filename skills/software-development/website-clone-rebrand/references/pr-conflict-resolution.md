# PR Conflict Resolution: Master vs Main Branches

## Problem

A repo has both `master` and `main` branches. A PR targets `master` but all new code is pushed to `main`. GitHub shows the PR as `CONFLICTING` or `UNSTABLE` with `mergeable: CONFLICTING`.

## Diagnosis

```bash
# Check PR status
gh pr view <PR_NUMBER> --repo OWNER/REPO --json mergeStateStatus,mergeable,headRefName,baseRefName
# Returns: {"baseRefName":"master","headRefName":"main","mergeStateStatus":"UNSTABLE","mergeable":"CONFLICTING"}

# Check local branches
git branch -a
# Shows remotes/origin/main and remotes/origin/master
```

## Fix Sequence

```bash
# 1. Fetch all remote branches to discover both master and main
git fetch --all

# 2. Create local master branch tracking origin/master
git branch master origin/master

# 3. Switch to master and merge main into it
#    This brings main's new content into master
git checkout master
git merge main --no-edit

# 4. Resolve any merge conflicts
#    For conflicted files where main has the newer structure:
git checkout --theirs <conflicted-file>
git add <conflicted-file>
# Repeat for each conflicted file, then:
git commit --no-edit

# 5. Force push master (history rewritten by merge commit)
git push origin master --force

# 6. Switch back to main and push (should be fast-forward)
git checkout main
git push origin main

# 7. Close the stale PR
gh pr close <PR_NUMBER> --repo OWNER/REPO -c "Resolved - merged main into master branch"
```

## Key Lessons

- **Never rebase or force-push `main` to `master`** — merge locally to preserve both branches' history
- **`git checkout --theirs`** resolves conflicts where `main` (the newer branch) has the correct content
- **Always `git fetch --all` first** — without this, `git branch master origin/master` fails because the remote ref isn't known locally
- **Force-push `master`** because the merge commit rewrites its history
- **Close the PR** to clean up the GitHub UI after the merge

## Real Session Example (September 14, 2026)

- Repo: `tradersurfer/dreamz-dc`
- PR #2 targeted `master` but code was on `main`
- Conflict files: `public/about.html`, `public/blog.html`, `public/brands.html`, `public/checkout.html`, `public/delivery.html`, `public/faq.html`, `public/index.html`, `public/js/products.js`, `public/js/site.js`, `public/med-reg.html`, `public/product.html`, `public/shop.html`, `server/index.js`, `vercel.json`
- Fix: `git checkout --theirs` for all conflicted files (main had the newer multi-page structure)
- Result: Master pushed with all new files, PR #2 closed
