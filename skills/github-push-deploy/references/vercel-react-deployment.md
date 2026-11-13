# React/Vite Deployment on Vercel

## Critical File Requirements

### `vercel.json` — Must be valid JSON
```json
{
  "cleanUrls": true,
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```
**Common failure:** Duplicate rewrite entries cause `Invalid vercel.json file provided`. Remove duplicates, validate with `cat vercel.json`.

### `package.json` — Must have `build` script
```json
{
  "scripts": {
    "build": "vite build",
    "dev": "vite",
    "preview": "vite preview"
  }
}
```
**Common failure:** Missing `"build": "vite build"` causes `Missing script: "build"`. Add it.

## Verification Steps
```bash
npm run build    # Must succeed locally before push
cat vercel.json  # Validate JSON is well-formed
cat package.json # Verify build script exists
git add . && git commit -m "fix: deployment config" && git push
```

## Typical Fix Sequence
1. `npm run build` fails locally → check error messages
2. If `Invalid vercel.json` → remove duplicate rewrites, validate JSON
3. If `Missing script: "build"` → add `"build": "vite build"` to package.json scripts
4. Commit and push — Vercel auto-deploys on push

## Reference
Part of the `github-push-deploy` skill. See `references/windows-git-pitfalls.md` for broader git/deployment issues.
