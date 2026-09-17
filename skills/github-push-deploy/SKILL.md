---
name: github-push-deploy
description: "Push to GitHub and deploy on Railway/Vercel."
version: 1.3.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, Deployment, Railway, Vercel, WSL2, PowerShell, React, Vite]
    related_skills: [github-repo-management, github-pr-workflow]
---

# GitHub Push & Deployment

Push code to GitHub and deploy on Railway or Vercel. This skill captures the universal push sequence and common WSL2/PowerShell pitfalls encountered on Windows.

## Prerequisites

- Authenticated with GitHub (see `github-auth` skill)
- Inside a git repository with a GitHub remote
- `gh` CLI available (recommended) or `git` + `curl`

## Universal Push Sequence

When pushing to an existing remote, always use this sequence:

```bash
cd /path/to/repo
git remote -v                          # Verify remote URL is correct
git branch -M main                     # Ensure branch is named 'main' (not 'master')
git push -u origin main                # Push and set upstream
```

If the remote URL is wrong, fix it first:
```bash
git remote remove origin
git remote add origin https://github.com/OWNER/REPO.git
git push -u origin main
```

**Verification after push:**
```bash
gh repo view OWNER/REPO --jq '.fullName'    # Confirm repo exists on GitHub
gh api repos/OWNER/REPO/contents --jq '.[].name'  # Verify files are on GitHub
```

## Creating a New Repo and Pushing

```bash
cd /path/to/repo
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/OWNER/REPO.git
git push -u origin main
**Full details:** See `references/windows-git-pitfalls.md` for deep-dive on each pitfall with reproduction steps and exact error messages.

> **Reference:** `references/windows-git-pitfalls.md` — detailed reproduction recipes, exact error messages, and fix sequences for each Windows/WSL2 git pitfall encountered in production sessions.

> **Reference:** `references/react-vite-build-notes.md` — React + Vite project scaffolding notes, component patterns, Iconify integration, and Excel-to-product-data extraction recipes encountered in production sessions.

---

> **Reference:** `references/branch-sync.md` — Branch sync pattern for repos with both `master` and `main` branches. Merge `main` into `master` and force-push to keep the domain updated.

## Deploy on Railway

After pushing to GitHub:

1. Go to `https://railway.new`
2. Click **"New Project"**
3. Select **"Deploy from GitHub"**
4. Choose your repo
5. Railway auto-detects `Dockerfile` → **DEPLOYS**

**Custom domain:** Add in Railway settings → Settings → Domains.

## Deploy on Vercel

After pushing to GitHub:

1. Go to `https://vercel.com/new`
2. Import the repo
3. Vercel auto-detects `vercel.json` or `package.json` → **DEPLOYS**

### React/Vite Projects

For React + Vite projects, ensure `vercel.json` is valid JSON with no duplicate rewrites, and `package.json` includes a `build` script (`"build": "vite build"`).

**Common failures:**
- `Invalid vercel.json file provided` — caused by duplicate rewrite entries or malformed JSON
- `Missing script: "build"` — caused by package.json lacking a build script

**Reference:** `references/nextjs-supabase-migration.md` — Next.js App Router + Supabase SSR migration patterns (two Supabase clients, NEXT_PUBLIC_ env var prefixing, server vs client components).

## Verifying Deployment

```bash
curl -s https://YOUR-APP.vercel.app/api/health
curl -s https://YOUR-APP.railway.app/api/health
```

---

## WSL2/Windows Pitfalls

### 1. `cd /c/Users/...` Path Trap

**Problem:** Running `cd /c/Users/jorda/...` inside WSL2 bash interprets `/c/` as a path component, producing `C:\c\Users\jorda\...` which does not exist.

**Fix:** Always use `C:/Users/...` (forward slash) or `C:\Users\...` (backslash):
```bash
# WRONG — produces C:\c\Users\...:
cd /c/Users/jorda/Desktop/Projects/my-app

# CORRECT:
cd C:/Users/jorda/Desktop/Projects/my-app
```

This applies to the `terminal` tool on Windows, PowerShell, and bash in WSL2.

### 2. Git Remote URL Confusion

**Problem:** `gh repo create` creates the repo under the authenticated user, not the intended org/user. Pushes fail with "Repository not found."

**Fix:** Verify and fix the remote:
```bash
git remote -v                    # Check current remote
git remote remove origin        # Remove incorrect remote
git remote add origin https://github.com/CORRECT_USER/repo.git
git push -u origin main
```

### 3. Branch Naming: `master` vs `main`

**Fix:** Always rename before pushing:
```bash
git branch -M main
git push -u origin main
```

### 4. `nul` File in Git Index

**Problem:** On Windows, a file named `nul` can appear in the git index, causing `git add .` to fail with `short read while indexing nul`.

**Fix:**
```bash
del nul                          # Remove the file (Windows cmd)
git reset HEAD                   # Reset the index
```

**Prevention:** Ensure `.gitignore` excludes `node_modules/` and other large directories.

### 5. `.gitignore` Not Created

**Problem:** Without `.gitignore`, `node_modules/` is tracked by git, causing massive warnings and indexing failures.

**Fix:** Create `.gitignore` before the first commit:
```
node_modules/
npm-debug.log*
.env
.env.local
.idea/
.vscode/
.DS_Store
Dockerfile.dockerignore
```

## PR Conflict Resolution (Master vs Main Branches)

**When it happens:** A PR targets `master` but code is pushed to `main`. GitHub shows the PR as `CONFLICTING`/`UNSTABLE`. The repo has both `master` and `main` branches tracking different content.

**Fix sequence:**
```bash
# 1. Fetch all remote branches to discover both master and main
git fetch --all

# 2. Create local master branch tracking origin/master
git branch master origin/master

# 3. Switch to master and merge main into it
git checkout master
git merge main --no-edit

# 4. Resolve any merge conflicts — take main's version for updated files
#    (main is the newer structure; master is the stale branch)
git checkout --theirs <conflicted-file>
git add <conflicted-file>
git commit --no-edit

# 5. Force push master to origin (main is already up to date)
git push origin master --force

# 6. Switch back to main and push (should be fast-forward)
git checkout main
git push origin main

# 7. Close the stale PR
gh pr close <PR_NUMBER> --repo OWNER/REPO -c "Resolved - merged main into master branch"
```

**Key lessons:**
- When a repo has both `master` and `main`, the PR targeting `master` is stale — merge `main` into `master` locally, don't try to push `main` to `master` directly
- Use `git checkout --theirs` for conflicted files where `main` has the newer content
- Always `git fetch --all` first to discover both branches
- After merging, force-push `master` since its history is rewritten
- Close the PR after merging to clean up the GitHub UI

## PR Creation Pitfalls

**`gh pr create` fails: "head branch 'main' is the same as base branch 'main'"**
When your local branch is `main` and you try to create a PR targeting `main`, GitHub rejects it.

**Fix:** Create a separate branch first:
```bash
git checkout -b feat/catalog-overhaul
git push origin feat/catalog-overhaul
gh pr create --head feat/catalog-overhaul --base main
```

## Supabase DB Operations via Python

**When updating a Next.js+Supabase product catalog, use the Python Supabase client** to bulk-insert/update products, variants, brands, and categories directly. This avoids REST API limitations with raw SQL execution.

**Pattern:**
```python
from supabase import create_client
import openpyxl, re

env_content = open('.env.local').read()
env_vars = {}
for line in env_content.strip().split('\n'):
    if '=' in line:
        k, v = line.split('=', 1)
        env_vars[k] = v.replace('\r', '')

supabase = create_client(env_vars['NEXT_PUBLIC_SUPABASE_URL'], env_vars['SUPABASE_SERVICE_ROLE_KEY'])
```

**Critical Supabase constraints encountered:**
1. `products_strain_type_check` — `strain_type` CANNOT be NULL, must be one of: `'Indica'`, `'Sativa'`, `'Hybrid'`. Always set explicitly.
2. `thc_percent` column has precision 5,2 — values ≥1000 cause `numeric field overflow`. Edibles/vapes with "1500mg" THC should be stored as NULL, not the mg value.
3. UUID fields (`brand_id`, `category_id`, `product_id`) must be passed as strings, not dicts/objects.
4. **`product_variants.inventory_count` defaults to 0** — products show "Out of Stock". Always set explicitly (e.g., `{'inventory_count': 25}`).
5. **Storage upload fails with `bucket.upload()`** — use signed URL pattern: `bucket.create_signed_upload_url()` then PUT to the signed URL.

**Brand slug mapping** — XLSX brand names differ from DB brand slugs. Create a mapping dictionary:
```python
brand_mappings = {
    'ganjavores': 'ganjavores-by-lee-farms',
    'exotic genetix': 'exotic-genetix',
    'cookies': 'cookies-dispensary',
    'jeeter juice': 'jeeter',
    'muha meds': 'muha-meds',
    # ... etc
}
```

**Variant parsing** — Price format in XLSX: `"3.5g: $45 | 7g: $80 | 14g: $140 | 28g: $190"`. Parse by splitting on `|` then `:`.

**Google Drive Image Download** — Download product images from Google Drive URLs:
```python
file_id = url.split('/d/')[1].split('/')[0]
download_url = f"https://drive.google.com/uc?id={file_id}"
req = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
resp = urllib.request.urlopen(req, timeout=15)
with open(save_path, 'wb') as f:
    f.write(resp.read())
```

**Supabase Storage Image Upload (WORKING PATTERN):**
```python
# 1. Get signed URL
signed = bucket.create_signed_upload_url('flower/duct-tape.png')
# 2. PUT to signed URL
req = urllib.request.Request(signed['signedUrl'], data=data, headers={'Content-Type': 'image/png', 'x-upsert': 'true'}, method='PUT')
resp = urllib.request.urlopen(req, timeout=15)  # Status 200 = success
```

---

---

## Summary Table
|---------|---------|-----|
| `cd /c/Users/...` | Path not found | Use `C:/Users/...` |
| Wrong git remote | Repository not found | `git remote remove/add origin` |
| `gh repo create` wrong user | Repository not found | Verify remote, fix with `gh api` |
| `nul` in git index | `short read while indexing nul` | `del nul` + `git reset HEAD` |
| No `.gitignore` | Massive git warnings | Create `.gitignore` first |
| `master` vs `main` | Wrong branch on GitHub | `git branch -M main` |
| Push rejected | `! [rejected] main -> main` | `git pull origin main --force --allow-unrelated-histories` |
| Rebase conflicts | `Auto-merging` failures | `git checkout --theirs <file>`, `git rebase --continue` |
| `vercel` not found | Command not recognized | `npm install -g vercel` |
| PR targets stale branch | `CONFLICTING`/`UNSTABLE` | Merge main into master locally, force-push, close PR |
| Vercel `invalid vercel.json` | Build failed | Fix duplicate rewrites, validate JSON |
| Vercel `missing build script` | Build failed | Add `"build": "vite build"` to package.json |

---

## References

- `references/windows-git-pitfalls.md` — detailed reproduction recipes, exact error messages, and fix sequences for each Windows/WSL2 git pitfall encountered in production sessions.
- `references/react-vite-build-notes.md` — React + Vite project scaffolding notes, component patterns, Iconify integration, and Excel-to-product-data extraction recipes.
- `references/vercel-react-deployment.md` — full fix sequence for React/Vite deployment issues.
- `references/nextjs-supabase-migration.md` — Next.js App Router + Supabase SSR migration guide with browser/server client separation, environment variable prefixing, and page-to-component conversion patterns.
- `references/supabase-product-catalog.md` — Supabase product catalog operations (XLSX parsing, storage upload, inventory_count, admin auth)

---
1. Fix `vercel.json` — replace with single clean rewrite:
   ```json
   {
     "cleanUrls": true,
     "rewrites": [
       { "source": "/(.*)", "destination": "/index.html" }
     ]
   }
   ```
   Remove ALL duplicate entries. Validate JSON with `cat vercel.json`.

2. Fix `package.json` — add `build` script:
   ```json
   {
     "scripts": {
       "dev": "vite",
       "build": "vite build",
       "preview": "vite preview",
       "start": "vite preview"
     }
   }
   ```

3. Rebuild locally to verify: `npm run build` — must succeed with no errors.

4. Commit and push: `git add . && git commit -m "fix: deployment config" && git push origin main`

5. Vercel auto-deploys on push. Verify at `https://dreams-fsgcn66uk-do-mo-crew.vercel.app` (or your deployment URL).

**Dockerfile for React/Vite (multi-stage):**
```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## Git Push — Exact Sequence for Existing Remote (2026-09-15)

**When pushing to an existing remote:**
```bash
cd /c/Users/jorda/Desktop/Projects/websites/dreamz-dc-react
git remote -v                    # Verify remote URL
git branch -M main               # Ensure branch is main
git push origin main             # Push to existing remote
```

**If push is rejected (remote has newer commits):**
```bash
git pull origin main --force --allow-unrelated-histories
# Resolve any conflicts, then:
git add .
git commit -m "Merge React into existing repo"
git push origin main
```

**If `gh repo create` created wrong repo:**
```bash
# Use gh api to find/create under correct user:
gh api repos/TRULY_CORRECT_USER/repo --jq '.fullName'
# If not found, create:
gh repo create CORRECT_USER/repo --public
# Then fix remote and push:
git remote set-url origin https://github.com/CORRECT_USER/repo.git
git push -u origin main
```
