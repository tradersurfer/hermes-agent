# GitHub Remote Verification Guide

## The Problem

When deploying a project to GitHub, the `gh` CLI may create or reference a repo under a different username than intended. This causes code to push to the wrong repository, and the user sees no code on their expected GitHub page.

## Verification Steps (Always Do Before Pushing)

### 1. Check the Authenticated User
```bash
gh api user --jq '.login'
# Returns the username the gh CLI is authenticated as
# This may differ from the intended repo owner
```

### 2. Check the Remote URL
```bash
git remote -v
# Must show the EXACT URL from the GitHub UI
# Example: https://github.com/tradersurfer93/dreamz-dc.git
# NOT: https://github.com/tradersurfer/dreamz-dc.git (wrong user!)
```

### 3. Verify the Repo Exists on the Correct Account
```bash
gh api repos/correct-user/correct-repo --jq '.fullName'
# Returns the full name if the repo exists on that account
# Returns 404 if the repo doesn't exist or belongs to a different user
```

### 4. List Repos on the Target Account
```bash
gh repo list correct-user --json name --jq '.[].name'
# Shows all repos under the correct username
# Compare against what you expect
```

## Fixing a Wrong Remote

```bash
# Remove the incorrect remote
git remote remove origin

# Add the correct remote (URL from GitHub UI)
git remote add origin https://github.com/correct-user/correct-repo.git

# Verify
git remote -v

# Push
git push -u origin main
```

## Common Scenarios

### `gh repo create` Creates Under Wrong User
- `gh` CLI authenticates as `tradersurfer` but user wants `tradersurfer93`
- `gh repo create dreamz-dc` creates under `tradersurfer/dreamz-dc`
- Fix: manually create repo on `tradersurfer93` via GitHub UI, then set remote to `https://github.com/tradersurfer93/dreamz-dc.git`

### Repo URL Has Wrong Username
- Remote shows `tradersurfer/dreamz-dc` but should be `tradersurfer93/dreamz-dc`
- Fix: `git remote remove origin && git remote add origin https://github.com/tradersurfer93/dreamz-dc.git`

### `gh repo list` Shows Repos Under Authenticated User Only
- `gh repo list` only shows repos for the authenticated user
- Repos owned by another user (e.g., `tradersurfer93`) won't appear
- Fix: `gh api repos/tradersurfer93/dreamz-dc` to check if a specific repo exists

## Session Notes (September 6, 2026)

- `gh` CLI authenticated as `tradersurfer` but repo intended for `tradersurfer93`
- `gh repo list` showed `dreamz-dc` under `tradersurfer` (wrong account)
- `gh api repos/tradersurfer93/dreamz-dc` returned 404 (repo didn't exist yet)
- Fix: `git remote remove origin && git remote add origin https://github.com/tradersurfer/dreamz-dc.git` (push to correct existing repo)
- Always verify `git remote -v` matches the GitHub repo URL shown in the UI