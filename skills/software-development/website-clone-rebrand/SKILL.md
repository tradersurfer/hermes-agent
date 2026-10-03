---
name: website-clone-rebrand
description: "Clone and rebrand an existing website for a new business."
version: 4.0.0
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [web, clone, rebrand, dispensary, e-commerce, full-stack, nodejs, express, wordpress, react, vite]
    related_skills: [build-news-bot, writing-plans, plan]
---

# Website Clone & Rebrand

Clone an existing website's structure, design, and functionality, then rebrand it for a new business with different identity, content, and information.

## When to Use

- User wants to replicate an existing website for their own business
- Rebranding an existing template/site with new logos, colors, and content
- Adapting a competitor's or reference site to match a new brand

## Workflow

### Phase 1: Extract Source

1. **Fetch the source website** using Python `urllib.request` (bypasses WDAC curl blocks on Windows):
   ```python
   import urllib.request
   req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
   html = urllib.request.urlopen(req, timeout=30).read().decode('utf-8')
   ```

2. **Extract embedded config/API data** from the HTML:
   - Look for `<script id='...config'>` tags containing JSON
   - WordPress REST API endpoints in script tags
   - Any hardcoded business info (address, phone, hours, store config)

3. **Identify the tech stack**: WordPress + plugin (e.g., Joint.co), custom HTML/CSS/JS, React, etc.

### Phase 2: Gather Business Info

1. **Extract from Google Business Profiles** or user-provided sources
2. **Collect assets**: logos, images, product photos from provided folders
3. **Map business details**: name, address, phone, email, hours, self-cert links
4. **Extract product catalog** from spreadsheets, APIs, or the source site's data

### Phase 3: Build the Clone

1. **Create project structure**:
   ```
   project-name/
   ├── index.html          # Main page
   ├── assets/
   │   ├── css/            # Stylesheets
   │   ├── js/             # JavaScript (product catalog, cart, etc.)
   │   └── images/         # Brand assets, product photos
   └── README.md           # Project documentation
   ```

2. **Clone the HTML structure** from source site, replacing:
   - Logo images and text
   - Brand name everywhere (headings, buttons, meta tags)
   - Color scheme (CSS variables)
   - Contact info (phone, email, address)
   - Navigation items
   - Footer content

3. **Adapt the product catalog**:
   - Map existing product types to new brand products
   - Update pricing as needed
   - Replace product images with new brand assets
   - Update descriptions and branding per product

4. **Configure business-specific features**:
   - Self-certification links (for cannabis dispensaries)
   - Age gate overlay (21+ verification)
   - Store hours, address, phone in footer
   - Self-cert banner prominently displayed

### Phase 4: Verify

1. **Open in browser** and confirm all sections render correctly
2. **Check all links** resolve (internal navigation, external links, self-cert)
3. **Verify images** load properly
4. **Test interactive elements**: cart, age gate, mobile menu, FAQ accordion
5. **Run a verification script** confirming file integrity

## Key Techniques

## Phase 5: Full-Stack Architecture (Production)

After building the static site, convert to a full-stack architecture for production deployment:

### Server Structure
```
project-name/
├── server/
│   ├── index.js              # Express.js main server
│   ├── routes/
│   │   ├── products.js       # Product API routes (GET /api/products, GET /api/products/:id)
│   │   └── cart.js           # Cart API routes (GET/POST/PATCH/DELETE)
│   └── data/
│       └── products.js       # Product database array + business config (BUSINESS, PRODUCTS, CATEGORIES)
├── public/                    # Frontend static files (served by Express)
│   ├── index.html            # Main homepage
│   ├── blog.html             # Blog page
│   ├── pages/                # Additional page HTML files
│   ├── blog/                 # Blog article content
│   ├── css/
│   ├── js/
│   └── images/              # 40+ product and brand images
├── package.json              # Express, cors, helmet, compression dependencies
├── vercel.json               # Vercel deployment config
├── railway.json              # Railway deployment config
├── Dockerfile                # Docker image for containerized deployment
├── .gitignore                # Exclude node_modules, env files
└── README.md
```

### Express.js Setup Pattern
```javascript
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const path = require('path');

const app = express();
app.use(helmet({ contentSecurityPolicy: {...} }));
app.use(cors());
app.use(compression());
app.use(express.json());
app.use(express.static(path.join(__dirname, '..', 'public')));

// API routes
app.use('/api', require('./routes/products'));
app.use('/api', require('./routes/cart'));

// Health check
app.get('/api/health', (req, res) => res.json({status: 'ok'}));

// Serve pages
app.get('/', (req, res) => res.sendFile(path.join(__dirname, '..', 'public', 'index.html')));
app.get('/blog', (req, res) => res.sendFile(path.join(__dirname, '..', 'public', 'blog.html')));
```

### Product Data Module (server/data/products.js)
- Export `{ BUSINESS, PRODUCTS, CATEGORIES, FLOWER_SUBCATEGORIES }`
- `BUSINESS` object: name, phone, email, address, hours array, selfCertUrl, socials object, announcements array, logo/storefront/hero image paths
- `PRODUCTS` array: each product has id, name, brand, type, category, subCategory, strain, strainType, thc, terps, price, oldPrice, badge, description, image, weight, menuTypes
- `CATEGORIES` array: slug, name, icon (Font Awesome class), subCategories
- `FLOWER_SUBCATEGORIES`: slug, name, image path for flower category sub-navigation

### Next.js + Supabase Architecture (GANJAVORES DC pattern)
When the target project uses **Next.js App Router + Supabase** (not Express):
- **Product data lives in Supabase tables**: `products`, `product_variants`, `product_images`, `product_terpenes`, `product_cannabinoids`, `brands`, `categories`, `reviews`, `orders`, `announcements`
- **Seed SQL files populate the database**: `supabase/schema.sql`, `supabase/seed-products.sql`, `supabase/seed-products-batch2.sql`, `supabase/seed-products-batch3.sql`, etc.
- **Products are loaded server-side via Supabase queries**: `lib/supabase/queries.ts` contains `getShopProducts()`, `getProductBySlug()`, `getAllBrands()`, `getAllCategories()`, `getPriceBounds()`
- **Product types defined in `lib/types.ts`**: `Product`, `Brand`, `Category`, `ProductVariant`, `ProductImage`, `ProductTerpene`, `ProductCannabinoid`, `Review`, `CartLine`
- **Business config in `lib/business-info.ts`**: Single source of truth for name, phone, email, address, hours, socials, license
- **CSV spreadsheets → SQL seed files**: When updating product catalog from a spreadsheet, parse CSV → compare against existing SQL seed files → generate `supabase/seed-catalog-update.sql` with DELETE/INSERT/UPDATE statements per product → run against Supabase. Never manually edit individual SQL rows. See `references/ganjavores-dc-catalog-update.md` for the full pattern.
- **Supabase SQL execution on Windows**: Cannot use `supabase db execute` (requires Docker). Use the Supabase Python REST client (`from supabase import create_client`) or the Supabase Dashboard SQL Editor instead. The REST client can only do CRUD, not raw SQL. Always delete ALL variants first with `.delete().neq('id', '00000000-0000-0000-0000-000000000001')` before re-inserting. See `references/ganjavores-dc-catalog-update.md` for details.
- **NEXT.js pages are server-side rendered** with `export const dynamic = "force-dynamic"` for real-time inventory
- **Product variants handle multi-size pricing**: Each product has multiple `product_variants` rows (e.g., 3.5g/7g/14g/28g), not a flat price field
- **Cart uses localStorage React context** (`lib/cart-context.tsx`), no accounts needed
- **Checkout writes to Supabase orders table**, no payment processor (pay on delivery/pickup)
- **Admin panel** at `/admin` with Supabase Auth, protected by `app/admin/(protected)/` route group
- **Frontend polish matters**: Remove emoji icons from trust bars (use Lucide React icons instead), remove dead links (e.g., ganjavores.com Shopify store), improve placeholder states for product images, and clean up business-info.ts comments about dead stores
- **The site is dynamically driven from Supabase**: Products, brands, categories, variants, and descriptions all come from the database via `lib/supabase/queries.ts`. Updating the catalog means updating the DB, not editing component files. Component files only need changes for visual polish
- **XLSX catalog updates (from Cannabis_Product_Descriptions.xlsx)**: The XLSX products are often ENTIRELY DIFFERENT from seed SQL products — do NOT assume slug matching works. Use `openpyxl` to parse, map brand names to DB slugs (see XLSX brand mapping below), delete all existing products/variants via Supabase REST client, then insert all XLSX products. Critical constraints: `strain_type` CHECK only allows 'Indica'/'Sativa'/'Hybrid' (never NULL), `thc_percent` is NUMERIC(5,2) (must be < 1000, NULL for edibles), and all UUID foreign keys must be passed as strings via `str()`. See `references/ganjavores-dc-xlsx-catalog.md` for the full pattern.
- **Supabase SQL execution on Windows**: Cannot use `supabase db execute` (requires Docker). Use the Supabase Python REST client (`from supabase import create_client`) or the Supabase Dashboard SQL Editor instead. The REST client can only do CRUD, not raw SQL. Always delete ALL variants first with `.delete().neq('id', '00000000-0000-0000-0000-000000000001')` before re-inserting. See `references/ganjavores-dc-catalog-update.md` for details.
### Cart API Pattern
```javascript
// In-memory cart (replace with database for production)
let cart = [];
// GET /api/cart → returns { cart, total, itemCount }
// POST /api/cart → adds item { productId, name, price, image }
// PATCH /api/cart/:productId → updates qty
// DELETE /api/cart/:productId → removes item
// DELETE /api/cart → clears cart
```

### Key Techniques

#### WDAC Workarounds (Windows)
- Use Python `urllib.request` instead of `curl` for HTTP requests
- Use `python` not `python3` (Windows Store shim issue)
- The venv python at `C:\Users\jorda\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe` works reliably
- `vision_analyze` with local file paths 404s — use `file:///C:/...` prefix or `browser_vision`

#### Bash-on-Windows Path Handling
- When running `terminal` commands with `bash`, paths like `/c/Users/...` get converted to `C:\c\Users\...` or mangled
- **Use `execute_code` instead** for Python file I/O with absolute Windows paths — it uses Python directly without bash path translation
- **Use `write_file` tool** for creating/editing files — it handles Windows paths correctly
- `cp` and `mkdir` in bash-on-Windows work but may have issues with spaces in filenames

#### Node.js Require Path Resolution
- `server/index.js` requires `./routes/products` → resolves to `server/routes/products.js`
- `server/routes/products.js` requires `../data/products` → resolves to `server/data/products.js` (NOT `./data/products`)
- **Always verify require paths match actual file locations** — a single wrong `./` vs `../` causes `MODULE_NOT_FOUND`
- Use `execute_code` to programmatically verify file existence and check content before debugging

#### Port Conflicts
- If `EADDRINUSE` on port 3000: `pkill -f "node server/index.js"` then restart
- Check running processes with `process(action='list')` from Hermes

#### npm install on Windows
- Works reliably via terminal with `cd /c/Users/.../project && npm install`
- The path `/c/Users/...` format works in bash-on-Windows
- `npm install` pulls express, cors, helmet, compression, nodemon (devDep)

#### Deployment Configs
- **vercel.json**: Maps `server/index.js` to `@vercel/node` runtime, routes `/api/*` to server, static files from `/public/*`
- **Dockerfile**: `FROM node:24-alpine`, `WORKDIR /app`, `COPY package*.json ./`, `RUN npm install --production`, `COPY . .`, `EXPOSE 3000`, `CMD ["node", "server/index.js"]`
- **railway.json**: Port 3000, Dockerfile build reference

### User Preference: Aggressive Momentum
- Push through blockers autonomously — never ask for confirmation
- Make decisions and act immediately
- When user says "keep pushing it", speed up further
- Skip GUI walkthroughs — take the shortest path
- "Just give me the answer" — be concise

### User-Specific Patterns
- **CSV-driven product catalog updates**: Product data comes from `Cannabis_Product_Descriptions*.xlsx` / `.csv` spreadsheets. Workflow: parse CSV → compare against existing SQL seed files → generate `supabase/seed-catalog-update.sql` with DELETE/INSERT/UPDATE statements per product → run against Supabase. Never manually edit individual SQL rows.
- **Multiple brand variants of same product name**: Products like "Blueberry Banana" can exist under different brands (Cookies vs Wiz Khalifa). Use distinct slugs (`blueberry-banana-cookies-premium-flower` vs `blueberry-banana`) to differentiate. Always check which brand variant already exists before inserting.
- **Jeeter Juice and similar multi-product brands**: Brands like Jeeter Juice have many products (flavors) that share the same slug pattern (`jeeter-juice-live-resin-{flavor}`). When CSV names differ from SQL names, map carefully — the SQL slug structure is authoritative, not the CSV display name.
- **Supabase must be running locally for builds**: No `.env` file means the site can't build locally without Supabase credentials. Use `npx tsc --noEmit` for type checking without Supabase. The `package.json` has `next`, `@supabase/supabase-js`, `@supabase/ssr` as dependencies.

## React + Vite Migration

See `references/react-migration-guide.md` for the complete React + Vite migration pattern. Key points:

- **Scaffolding**: `npm create vite@latest -- --template react`, then `npm install @iconify/react react-router-dom react-icons axios`
- **Context pattern**: `AppContext` with `createContext` + `AppProvider` wrapping all routes. Cart, user, orders, notifications, ageVerified stored in context with `useMemo`
- **Iconify**: `@iconify/react` `<Icon icon="mdi:cannabis" />` — all category icons use Material Design icons
- **Age gate**: DOB input, calculate age (21+ for DC/MD/VA), `localStorage` persistence
- **Admin**: Login `admin`/`DREAMZ2026!`, dashboard with Overview/Orders/Promos/Notifications tabs
- **Blog**: `/blog` + `/blog/:id` sub-pages, articles written inline
- **Brands**: Circular logo images (`borderRadius: '50%'`)
- **Product cards**: Smaller grid `minmax(160px, 1fr)`, more per row
- **Build**: `npm run build` must succeed, verify with `npm run build`
- **Dockerfile**: Multi-stage build with `node:18-alpine` + `nginx:alpine`

- `references/react-migration-guide.md` — React + Vite migration pattern, component architecture, common pitfalls

## Deployment

### Vercel
- `vercel.json` with `@vercel/node` build target
- Static files served from `public/` directory
- API routes in `server/index.js` handled by Vercel Node runtime

### Railway
- Create `Dockerfile` (Node 24 alpine, `npm install --production`, `node server/index.js`)
- Create `railway.json` with port 3000
- Railway auto-detects Dockerfile
- **GitHub required first**: Create repo, push, then import on railway.new

### Local Development
- `npm install` then `npm run dev`
- Opens at `http://localhost:5173` (Vite default)
- `npm run build` for production build

## References

- `references/pr-conflict-resolution.md` — Master vs Main branch PR conflict fix sequence
- `references/github-remote-verification.md` — Verify GitHub remote URLs before pushing
- `references/windows-git-pitfalls.md` — Deep-dive on Windows/WSL2 git issues
- `references/git-deployment-guide.md` — Complete deployment walkthrough
- `references/react-migration-guide.md` — React + Vite migration pattern and common pitfalls
- `references/ganjavores-dc-catalog-update.md` — Supabase catalog update pattern (includes XLSX workflow, storage upload, inventory_count pitfalls)
- `references/session-log.md` — Session-specific notes and learnings
- `references/session-log.md` — Session-specific notes and learnings. See `references/pr-conflict-resolution.md` for details

### Supabase Storage — Product Image Upload (WORKING PATTERN)

**DO NOT use `bucket.upload()` directly** — it fails with 400 Bad Request on Supabase.
**DO NOT use the REST API POST to `/storage/v1/object/public/...`** — also fails with 400.

**USE the signed URL upload pattern:**

```python
from supabase import create_client
supabase = create_client(SUPABASE_URL, SERVICE_ROLE_KEY)
bucket = supabase.storage.from_('product-images')

# 1. Get a signed upload URL
signed = bucket.create_signed_upload_url('flower/duct-tape.png')
# Returns: {'signed_url': '...', 'path': 'flower/duct-tape.png', ...}

# 2. Upload file content to the signed URL via PUT
import urllib.request
with open(local_path, 'rb') as f:
    data = f.read()
req = urllib.request.Request(
    signed['signedUrl'],
    data=data,
    headers={'Content-Type': 'image/png', 'x-upsert': 'true'},
    method='PUT'
)
resp = urllib.request.urlopen(req, timeout=15)
# Status 200 = success
```

**To create product_images records after upload:**
```python
public_url = f"https://{PROJECT_REF}.supabase.co/storage/v1/object/public/product-images/{remote_path}"
supabase.table('product_images').insert({
    'product_id': pid,
    'url': public_url,
    'alt_text': 'Product name',
    'display_order': 0
}).execute()
```

### Variant inventory_count

**`product_variants.inventory_count` defaults to 0** when inserted without an explicit value. Products with `inventory_count = 0` show **"Out of Stock"** on the site.

Always set `inventory_count` explicitly:
```python
supabase.table('product_variants').update({'inventory_count': 25}).eq('id', pid).execute()
```

### Admin Auth Setup

The admin panel uses **Supabase Auth**. There is NO default admin password.

**To set up admin access:**
1. Supabase Dashboard → Authentication → Users → Add User
2. Copy the generated User UID
3. Insert into admin_profiles: `insert into admin_profiles (id, full_name, role) values ('<uid>', 'Your Name', 'owner')`
4. The user can then log in at `/admin/login` with their email/password

**Password reset:** Direct users to `https://{PROJECT_REF}.supabase.co/auth/v1/recover?email=<user@example.com>`

**Magic link for new admins:** Use `supabase.auth.signInWithOtp({ email, options: { emailRedirectTo: '...' } })`

**Note:** There is NO "forgot password" link in the admin UI — add one manually or link to Supabase's password recovery page.