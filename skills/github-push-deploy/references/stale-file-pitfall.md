# Stale/Placeholder Source Files Pitfall

## The Problem

The #1 cause of "changes not showing on the live site" is when source files exist on disk but are incomplete stubs that were already committed. `git status` shows no changes, pushes succeed, but the site shows old content.

## Detection Pattern — ALWAYS Verify Before Committing

```bash
wc -l src/App.jsx                    # Should be 400+ lines for full e-commerce, not 50
grep -c 'id:' src/App.jsx            # Should match product count (e.g., 45)
grep -c 'href.*product' src/App.jsx  # Should be >0 (clickable product cards)
grep -c 'announcement' src/App.jsx   # Should be >0 (announcement bar present)
grep -c 'DREAMZ2026!' src/App.jsx   # Should be >0 (admin credentials)
ls public/images/ | wc -l            # Should match expected image count (e.g., 43)
```

## The Fix: Rebuild from Scratch

If files are stale/placeholder:
1. Do NOT try to patch the stub file — it's already committed and the diff will be huge/unmanageable
2. Rebuild from scratch: `rm -rf src/ && npx create-vite@latest . --template react` (or `npx create-next-app@latest` for Next.js)
3. Write ALL source files fresh (App.jsx, App.css, page components)
4. Run `npm run build` to verify
5. Copy images to `public/`
6. THEN commit and push

## Why This Happens

A previous session's work may have been interrupted, leaving stub files that get committed. `git log --oneline` looks fine but `git show HEAD:src/App.jsx` contains placeholder code.

## Verification After Push

```bash
gh api repos/OWNER/REPO/contents/src/App.jsx --jq '.size'  # Check file size on GitHub
gh api repos/OWNER/REPO/contents/public/images/ --jq '.[].name'  # Verify images exist
```

## Real-World Example

Session: DREAMZ DC dispensary (2026-09-15). User reported "I'm still not seeing any of the changes on the master branch. All product images still have icons, non of the product cards are clickable, non of the blog articles have images." Investigation revealed `src/App.jsx` was only ~316 lines (a stub) instead of the expected 500+ line full e-commerce implementation. The local repo showed `git status` clean because the stubs had already been committed in a previous session. Resolution: Rebuilt the entire project from scratch with a fresh `create-vite@latest` scaffold, writing all 512 lines of `App.jsx` fresh with 45 real products, clickable product card links (`<a href="/product/{id}">`), announcement bar, and blog images with real paths (`Code_Generated_Image (12).jpg`, `storefront.jpg`, `Frozen Black Cherry by DREAMZ - Top Shelf Whole Flower.jpg`). Build passed with `npm run build`. Next: copy 43 images from `dreamz-dc/public/images/` to `dreamz-dc-react-new/public/images/`, commit, push to BOTH main and master branches, deploy on Vercel.
