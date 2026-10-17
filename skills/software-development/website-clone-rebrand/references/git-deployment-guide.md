# Git Setup & Deployment Guide

## Pre-Deployment Checklist

### 1. .gitignore Configuration

Create `.gitignore` at project root with these entries:

```
# Dependencies
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Environment
.env
.env.local
.env.production

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Build
dist/
build/

# Railway
.railway/

# Vercel
.vercel

# Docker
Dockerfile.dockerignore

# Test
test/
tests/
__test__/

# Package
package-lock.json
yarn.lock
pnpm-lock.yaml
```

**CRITICAL**: Do NOT add `Dockerfile` to .gitignore — only `Dockerfile.dockerignore`. The Dockerfile must be committed for Railway and Vercel to detect it.

### 2. Verify .gitignore Works

```bash
git status --short
```

Should NOT show any `node_modules/` files. If it does, `.gitignore` isn't working correctly.

### 3. Remove Phantom Files

Windows sometimes creates phantom `nul` files:

```bash
del nul 2>nul || true
# or
rm -f nul
```

Verify with: `ls nul 2>/dev/null` → should say "No such file"

### 4. Git Commits

Make sure all project files are committed:
```bash
git add -A
git commit -m "DREAMZ DC v2.0 - Full-stack dispensary website"
```

## Deployment to Railway

### Step 1: Create GitHub Repository

1. Go to https://github.com/new?name=dreamz-dc
2. Create a **public** repository
3. Do NOT initialize with README (you already have one)
4. Click "Create repository"

### Step 2: Push to GitHub

```bash
cd C:\Users\jorda\Desktop\Projects\websites\dreamz-dc
git remote add origin https://github.com/YOURUSER/dreamz-dc.git
git push -u origin main
```

### Step 3: Deploy on Railway

1. Go to https://railway.new
2. Click "New Project"
3. Select "Deploy from GitHub"
4. Choose the `dreamz-dc` repository
5. Railway auto-detects the `Dockerfile`
6. Click "Deploy"
7. Wait for build (~2-3 minutes)
8. Your site is live at `https://your-app.railway.app`

### Step 4: Verify Deployment

```bash
curl https://YOURAPP.railway.app/api/health
# Should return: {"status":"ok",...}
```

## Deployment to Vercel

### Step 1: Push to GitHub (same as above)

### Step 2: Deploy on Vercel

1. Go to https://vercel.com
2. Click "Add New Project"
3. Import the `dreamz-dc` repository
4. Framework Preset: `Other`
5. Build Command: (leave empty)
6. Dev Command: `node server/index.js`
7. Click "Deploy"
8. Your site is live at `https://your-app.vercel.app`

## Common Issues

### `nul` File Appears in Git

This is a Windows artifact. Remove it:
```bash
del nul
git add -A
git commit -m "Remove nul file"
```

### Port Binding in Production

Express must use `process.env.PORT || 3000`:
```javascript
app.listen(process.env.PORT || 3000, () => {
    console.log(`Server running on port ${process.env.PORT || 3000}`);
});
```

### Docker Build Fails on Railway

Check that `Dockerfile` starts with `FROM node:24-alpine` and ends with `CMD ["node", "server/index.js"]`. The `COPY package*.json ./` must come before `RUN npm install --production`.

### CORS Errors on Deployed Site

If the frontend and API are on different domains, add CORS:
```javascript
app.use(cors({origin: 'https://yourdomain.com'}));
```
