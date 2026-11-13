# React + Vite Migration Guide

## Project Setup

```bash
cd /c/Users/jorda/Desktop/Projects/websites/<project-name>
npm create vite@latest . -- --template react
npm install @supabase/supabase-js @supabase/ssr react-router-dom react-icons
```

## Dependencies to AVOID

- **@iconify/react**: Package versions on npm don't match registry expectations. Replace with `react-icons` (Font Awesome). Symptom: `npm install` returns 404 for `@iconify/react`. Fix: remove from deps, use `<i className="fas fa-...">` instead of `<Icon icon="...">`

## Component Architecture

### Context Pattern
```jsx
const AppContext = createContext()
function AppProvider({ children }) {
    const [cart, setCart] = useState([])
    const value = useMemo(() => ({ ... }), [deps])
    return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}
```

### Essential Routes
All routes must be defined in `<Routes>`:
```
/ /shop /shop/:id /brands /about /delivery /blog /blog/:id /faq /cart /checkout /admin
```

## Admin Panel Pattern (Ganjavores-style, September 16, 2026)

When adding a full admin panel to an existing React+Vite SPA **without modifying the existing AppContext**:

1. **Create `src/admin.jsx`** with a self-contained `AdminProvider` that manages its own state:
   - Catalog (with CRUD: `upsertProduct`, `deleteProduct`)
   - Orders (with `setOrderStatus`)
   - Reviews (with `setReviewApproved`, `deleteReview`)
   - Brands (with `upsertBrand`, `deleteBrand`)
   - Categories (with `upsertCategory`, `deleteCategory`)
   - Announcements (with `addAnnouncement`, `toggleAnnouncement`, `deleteAnnouncement`)
   - Messages (with `markMessageRead`)
   - User auth state (`user`, `setUser`)

2. **Import seed data** from existing `data.js`:
   ```jsx
   import { PRODUCTS, BRANDS, CATEGORIES } from './data.js'
   ```
   Use these as initial state in `AdminProvider`: `useState(PRODUCTS)`, `useState(BRANDS)`, etc.

3. **Wrap admin routes** with `AdminProvider` in App.jsx route definitions:
   ```jsx
   import { AdminShell, AdminLogin, AdminProvider } from './admin.jsx'
   
   <Route path="/admin/login" element={<AdminProvider><AdminLogin /></AdminProvider>} />
   <Route path="/admin/*" element={<AdminProvider><AdminShell /></AdminProvider>} />
   ```

4. **AdminShell** contains:
   - Sidebar with `NavLink` navigation (Dashboard, Products, Orders, Brands, Categories, Announcements, Reviews, Messages)
   - Nested `<Routes>` with relative paths (index, products, products/new, products/:id, etc.)
   - Auth guard: `if (!user) return <Navigate to="/admin/login" replace />`

5. **AdminLogin** credentials: email `jordanad46@gmail.com` or `admin`, password `LoneWolf.276$`

6. **Create `src/admin.css`** — separate dark-theme stylesheet, imported in `admin.jsx`

7. **Do NOT modify the existing `AppProvider`** in `App.jsx` — let the admin context be isolated

### Admin Credentials (non-Supabase, localStorage-based)
- Email: `jordanad46@gmail.com` or username `admin`
- Password: `LoneWolf.276$`

## Build & Deploy

### package.js
```json
{
  "type": "module",
  "scripts": { "build": "vite build", "dev": "vite" }
}
```

### vercel.json
```json
{
  "installCommand": "npm install --legacy-peer-deps",
  "buildCommand": "vite build"
}
```

### Multi-branch push
```bash
git push origin master main
# If divergent: git push --force origin master main
```

## Critical Checklist Before Push

1. **ProductCard** uses `<a href="/product/{id}">` not `<div>`
2. **AnnouncementBar** rendered OUTSIDE hero section, ABOVE content
3. **Hero padding-top** = 60px (not 80px) so announcement isn't clipped
4. **z-index** — announcement-bar: 1002, header: 1000
5. **Admin route** — `<Route path="/admin/*" element={<AdminProvider><AdminShell /></AdminProvider>} />`
6. **Dropdown nav** — CSS `.dropdown-menu` hover styles
7. No `@iconify/react` in deps
8. All images exist in `public/images/`
9. `vercel.json` has clean single rewrite

## Vercel Domain Fix
When `www.dreamzdccompound.shop` returns 404:
1. Check alias: `vercel alias list` shows which deployment URL maps to the custom domain
2. If domain points to old/deleted deployment, redeploy: `vercel --prod`
3. Verify: `curl -sI https://www.dreamzdccompound.shop` → should return 200 OK

## User Preferences

### Verify commit before changes
**Always confirm the exact commit hash with the user before making changes.** If the user says your changes were on the wrong commit, use `git reflog` to find the correct starting commit, `git reset --hard <correct-commit>`, then re-apply changes. Never assume the HEAD commit is the correct base.

### Project naming
Never create new project directories (e.g., `dreamz-dc-react-new`, `dreamz-dc-next`) for the same project. Always work within the existing repo name. New dirs confuse the user — Vercel/GitHub are configured for the original repo.

### Aggressive momentum
- Push through blockers autonomously — never ask for confirmation
- Make decisions and act immediately
- When user says "keep pushing it", speed up further
- Skip GUI walkthroughs — take the shortest path
- "Just give me the answer" — be concise

## Troubleshooting

### "npm install" fails on Vercel
1. Remove `@iconify/react` from deps
2. Add `"type": "module"` to package.json
3. Add `"installCommand": "npm install --legacy-peer-deps"` to vercel.json
4. Remove server-only deps (express, cors, helmet, nodemon)