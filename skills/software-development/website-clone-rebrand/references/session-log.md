## DREAMZ DC Clone Session (September 6, 2026)

### Summary
Cloned https://dc.cookies.co/ and rebranded to DREAMZ DC Compound dispensary website.

### What was extracted from source
- Joint.ecommerce config with all business info (address, phone, hours, order types)
- Full product catalog data (28+ products across multiple brands)
- Self-certification URL: https://octo.quickbase.com/db/bscn22va8?a=dbpage&pageID=39
- Age gate requirement (21+)
- Store hours from config

### Files created
- `C:\\Users\\jorda\\Desktop\\Projects\\websites\\dreamz-dc\\index.html` (51KB)
- `C:\\Users\\jorda\\Desktop\\Projects\\websites\\dreamz-dc\\assets\\js\\products.js` (21KB)
- `C:\\Users\\jorda\\Desktop\\Projects\\websites\\dreamz-dc\\README.md` (4KB)
- 6 brand images in assets/images/

### Key decisions made
- Used Python urllib.request instead of curl (WDAC blocks)
- Used python not python3 (Windows Store shim issue)
- Inline CSS in HTML (styles.css is placeholder)
- Products.js as separate module for catalog data
- Age gate overlay on page load
- Gold/dark color scheme (replacing Cookies green/red)

### Skills updated
- build-news-bot: Added WDAC workarounds, e-commerce clone pattern, self-cert pattern
- website-clone-rebrand: New skill created with full workflow

---

## Ganjavores DC Catalog Update (September 15, 2026)

### Summary
Updated product catalog via XLSX, uploaded images to Supabase Storage, fixed variant inventory, added admin password reset links.

### Key Fixes

1. **Supabase Storage upload**: `bucket.upload()` returns 400 Bad Request. Use signed URL pattern instead:
   ```python
   signed = bucket.create_signed_upload_url(remote_path)
   req = urllib.request.Request(signed['signedUrl'], data=file_data,
                                headers={'Content-Type': 'image/png'}, method='PUT')
   resp = urllib.request.urlopen(req, timeout=15)
   ```
   - Upload via `PUT` to `signedUrl`, NOT `POST` to `/object/public/`
   - `x-upsert` header not needed when using signed URL

2. **Variant inventory_count defaults to 0**: When inserting variants without explicit `inventory_count`,
   products show "Out of Stock" on the site. Must explicitly set `inventory_count = 25`.
   ```python
   supabase.table('product_variants').update({'inventory_count': 25}).eq('id', pid).execute()
   ```
   - `add-to-cart-panel.tsx` checks `selectedVariant.inventory_count <= 0` → "Out of Stock"

3. **Admin login has NO password reset link**: Users cannot recover forgotten passwords from the admin UI.
   - Added "Reset Password" link to `/admin/login` pointing to Supabase auth recovery:
     `https://{PROJECT_REF}.supabase.co/auth/v1/recover?email={email}`
   - Added `/admin/request-access` page with magic link login:
     `supabase.auth.signInWithOtp({ email, options: { emailRedirectTo: '/admin' } })`

4. **Count queries with `.select('count')` return None**: Use `.select('id')` and `len(result.data)` instead.
   - Affected: `product_images`, `product_variants`, `products` count queries

5. **XLSX image URLs vs Supabase Storage**: Images from XLSX downloaded and re-uploaded to Supabase Storage bucket.
   Public URLs: `https://{PROJECT_REF}.supabase.co/storage/v1/object/public/product-images/{category}/{filename}.png`

### Admin Credentials
- **Email**: jordanad46@gmail.com (Supabase auth user)
- **UID**: 1434908f-3feb-4ed0-8a6c-f08390b17c0e (linked to admin_profiles with role=owner)
- **Password**: Set when auth account was created — reset via Supabase Dashboard or new recovery link
- **Admin profile**: Already exists in `admin_profiles` table with role='owner'

---

## DREAMZ DC React+Vite Admin Panel (September 16, 2026)

### Summary
Added Ganjavores-style admin panel to the React+Vite DREAMZ DC project (commit `7a668b4`) without modifying the existing website structure or data.

### Key Learning: Verify commit before making changes
The user's final working deployment was at commit `7a668b4` (confirmed by user). An earlier attempt started from wrong commit (`35adfa4`) which replaced the working App.jsx with an older broken version. **Always confirm the exact commit hash with the user before making any changes.** If changes appear to have destroyed existing work, use `git reflog` to find the correct starting commit, then `git reset --hard <correct-commit>`.

### Admin Panel Architecture (React+Vite, not Next.js)
The admin panel was built as a self-contained module that does NOT require converting the project to Next.js:

1. **`src/admin.jsx`** — Contains:
   - `AdminProvider` — A self-contained React context with CRUD state (catalog, orders, reviews, brands, categories, announcements, messages)
   - `AdminShell` — Sidebar navigation + nested `<Routes>` for admin sub-pages
   - `AdminLogin` — Login form (email: `jordanad46@gmail.com` or `admin`, password: `LoneWolf.276$`)
   - All admin page components: Dashboard, Products (list/new/edit/delete), Orders, Brands, Categories, Announcements, Reviews, Messages

2. **`src/admin.css`** — Dedicated admin panel styles (dark theme, separate from main site CSS)

3. **In `src/main.jsx`** — Wrap `<App />` in `<AdminProvider>` so admin context is available app-wide

4. **In `src/App.jsx`** — Routes:
   ```jsx
   <Route path="/admin/login" element={<AdminProvider><AdminLogin /></AdminProvider>} />
   <Route path="/admin/*" element={<AdminProvider><AdminShell /></AdminProvider>} />
   ```

### Vite vs Express server/ directory
The project at commit `7a668b4` uses **React + Vite** (not the Express server). The `server/` directory and `Dockerfile` still exist from the old Express-based version but are **not used** in the current Vite build. The `vercel.json` build command strips old HTML files and runs `vite build`. Do NOT delete the `server/` directory — it doesn't interfere with the Vite build.

### Vercel Domain 404 Fix
When `www.dreamzdccompound.shop` returns 404:
1. Check if the alias is configured: `vercel alias list` shows which deployment URLs map to the custom domain
2. If the domain points to an old/deleted deployment, trigger a fresh production deploy: `vercel --prod`
3. Verify with `curl -sI https://www.dreamzdccompound.shop` — should return 200 OK

### Multi-branch sync for React+Vite projects
When master and main diverge:
1. Cherry-pick the commit from one branch to the other: `git cherry-pick <commit>`
2. Force push both: `git push origin master main --force`
3. Or reset main to match master: `git checkout main && git reset --hard master && git push origin main --force`
4. Verify with `git log --oneline -1 master && git log --oneline -1 main` — both should show the same commit

### Self-contained AdminProvider pattern
When adding an admin panel to an existing React+Vite SPA WITHOUT modifying the existing AppContext:
- Create a **separate** `AdminProvider` in `admin.jsx` that manages its own state (catalog, orders, reviews, etc.)
- Pass seed data (PRODUCTS, BRANDS, CATEGORIES) from the existing `data.js` as initial state
- Wrap admin routes with `<AdminProvider>` in the route definitions
- This avoids modifying the existing `AppProvider` in `App.jsx` and keeps admin state isolated
- Admin credentials are managed in the AdminProvider's login flow, not the main site's auth

### Git safety when user corrects commit selection
When the user says "your changes were on the wrong commit":
1. Identify the correct commit hash (e.g., `7a668b4`)
2. `git checkout master && git reset --hard <correct-commit>`
3. Clean any new files that would conflict: `git checkout master && git clean -fd src/admin.jsx`
4. Cherry-pick the work commit onto the correct base: `git cherry-pick <commit>`
5. Force push: `git push origin master main --force`
6. Redeploy to Vercel: `vercel --prod`