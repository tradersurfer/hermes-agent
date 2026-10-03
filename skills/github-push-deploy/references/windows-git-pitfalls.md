# Windows Git & Deployment Pitfalls

This reference document catalogs the specific issues encountered when working on Windows via WSL2 bash and the `terminal` tool. These are session-specific details distilled from real debugging paths.

## 1. `cd /c/Users/...` Path Trap

**When it happens:** Running `cd /c/Users/jorda/...` in bash via the `terminal` tool on Windows.

**What goes wrong:** WSL2 bash interprets `/c/` as a literal path component, producing `C:\c\Users\jorda\...` which does not exist. Error: `Cannot find path 'C:\c\Users\jorda\...'`.

**Root cause:** The `terminal` tool runs commands through bash (git-bash/MSYS) on Windows. Paths starting with `/c/` are relative to the filesystem root, not Windows drive letters.

**Fix:** Always use `C:/Users/...` (forward slash) or `C:\Users\...` (backslash):
```bash
# WRONG:
cd /c/Users/jorda/Desktop/Projects/my-app
# → C:\c\Users\jorda\Desktop\Projects\my-app (NOT FOUND)

# CORRECT:
cd C:/Users/jorda/Desktop/Projects/my-app
# → C:\Users\jorda\Desktop\Projects\my-app (WORKS)
```

**Applies to:** All bash commands in `terminal` tool, PowerShell (use `cd C:\Users\...`).

## 2. Git Remote URL Confusion

**When it happens:** After `gh repo create`, the remote points to the authenticated user, not the intended org/user. Pushes fail with "Repository not found."

**Fix sequence:**
```bash
git remote -v                    # Check current remote URL
git remote remove origin        # Remove incorrect remote
git remote add origin https://github.com/CORRECT_USER/repo.git
git push -u origin main         # Push to correct remote
```

**Verification:**
```bash
gh api repos/CORRECT_USER/repo --jq '.fullName'
# Should return "CORRECT_USER/repo"
```

## 3. `nul` File in Git Index

**When it happens:** On Windows, a file named `nul` (the Windows null device) appears in the git index, causing `git add .` to fail.

**Fix:**
```bash
del nul                          # Windows cmd
git reset HEAD                   # Reset the index
```

## 4. `.gitignore` Not Created

**Fix:** Create `.gitignore` BEFORE the first commit:
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

## 5. Branch Naming: `master` vs `main`

**Fix:** Always rename before pushing:
```bash
git branch -M main
git push -u origin main
```

## 6. `gh repo create` Creates Wrong Repository

**When it happens:** `gh repo create dispensary-app --public` creates the repo under the authenticated GitHub user (e.g., `tradersurfer/dreamz-dc`), not the intended user. Pushes fail with `Repository not found`.

**Fix:** Use `gh api` to verify the correct repo exists, then fix the remote:
```bash
gh api repos/TRULY_CORRECT_USER/repo --jq '.fullName'
git remote set-url origin https://github.com/TRULY_CORRECT_USER/repo.git
git push origin main
```

**Lesson learned:** `gh repo create` creates under the authenticated user. Always verify the remote after creation.

## 7. Git Push Rejected (Remote Has Newer Commits)

**When it happens:** Pushing to an existing remote that has commits the local repo doesn't have. Error: `! [rejected] main -> main (fetch first)`.

**Fix:**
```bash
git pull origin main --force --allow-unrelated-histories
# Resolve any conflicts, then commit and push
```

**Critical:** Use `--allow-unrelated-histories` if the local repo was initialized fresh (no shared commit history with remote).

## 8. Git Rebase Conflicts

**When it happens:** Rebasing a new commit onto a remote that has diverged. Conflicts appear in `.gitignore`, `Dockerfile`, `package.json`, `index.html`, etc.

**Fix:**
```bash
git checkout --theirs <conflicted-file>  # Take the new version
git add <conflicted-file>
git rebase --continue
```

If rebase gets stuck with `unix2dos` converting `.git/COMMIT_EDITMSG`, use `GIT_REBASE_SKIP=1 git rebase --continue` or abort and re-initialize: `rm -rf .git && git init && git branch -M main && git remote add origin ... && git add -A && git commit -m "..." && git push origin main --force`.

## 9. React/Vite Deployment Failures

### `Build Failed Invalid vercel.json file provided`
**Cause:** Duplicate rewrite entries in `vercel.json`.
**Fix:** Replace with single clean rewrite:
```json
{"cleanUrls": true, "rewrites": [{"source": "/(.*)", "destination": "/index.html"}]}
```

### `Missing script: "build"`
**Cause:** `package.json` lacks `"build": "vite build"`.
**Fix:** Add to scripts section.

### Dockerfile for React Multi-Stage Build
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

## Summary Table

| Pitfall | Symptom | Fix |
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