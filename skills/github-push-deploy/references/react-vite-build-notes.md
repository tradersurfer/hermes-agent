# React + Vite Build Notes

## Project Scaffolding

### Creating a React + Vite Project
```bash
npm create vite@latest <project-name> -- --template react
cd <project-name>
npm install
```

This creates the modern React folder structure with `src/App.jsx`, `src/main.jsx`, `src/index.css`, `vite.config.js`, and `package.json`.

### Additional Dependencies Used
```bash
npm install @iconify/react react-router-dom react-icons axios
```

- `@iconify/react` — Iconify component for category icons (e.g., `mdi:cannabis`, `mdi:vape`, `mdi:pill`)
- `react-router-dom` — Client-side routing (BrowserRouter, Routes, Route, Link, useParams, useNavigate, useLocation)
- `react-icons` — Additional icon library (fallback)
- `axios` — HTTP client for API calls (future use)

## Component Structure

### App.jsx Pattern
- `AppProvider` context wraps `BrowserRouter`
- Context provides: `cart`, `setCart`, `ageVerified`, `setAgeVerified`, `user`, `setUser`, `orders`, `setOrders`, `promos`, `setPromos`, `notifications`, `setNotifications`
- All pages consume context via `useApp()` hook
- Routes: `/`, `/shop`, `/shop/:id`, `/blog`, `/blog/:id`, `/brands`, `/about`, `/checkout`, `/cart`, `/admin`, `/med-reg`, `/faq`

### Product Card Component
```jsx
<Link to={`/product/${product.id}`} className="product-card-link">
  <div className="product-card">
    <div className="product-image">
      <img src={product.image} alt={product.name} />
      {product.badge && <span className={`product-badge badge-${product.badge}`}>{product.badge}</span>}
    </div>
    <div className="product-info">
      <div className="product-brand">{product.brand}</div>
      <div className="product-name">{product.name}</div>
      <div className="product-details">{product.strain} • {product.thc}</div>
      <div className="product-price">
        <span className="price">${product.price}</span>
        <button className="add-cart" onClick={(e) => { e.preventDefault(); addToCart(product); }}>ADD</button>
      </div>
    </div>
  </div>
</Link>
```

### Announcement Bar (Scrolling Ticker)
```jsx
<div className="announcement-bar">
  <div className="announcement-content">
    🔥 <strong>LIMITED TIME:</strong> 10% OFF first order! Free delivery on orders $75+.
  </div>
</div>
```
CSS uses animated gradient background and flex layout.

## Product Data from Excel

### Extracting Product Data from `.xlsx`
Use `openpyxl` to read product data:
```python
import openpyxl
wb = openpyxl.load_workbook('Cannabis_Product_Descriptions.xlsx')
ws = wb['Product Summary']
# Columns: Product Name, Brand, Genetics, Strain Type, THC, CBD, Category, Price, Image URL
for row in ws.iter_rows(min_row=5, values_only=True):
    if row[0] and row[0] != 'Product Name':
        name, brand, _, strain, thc, _, category, price, image = row[:9]
        # Process...
```

### Product Image Mapping
Excel `Image URL` column contains Google Drive links. Map to local `public/images/` filenames by brand name:
- Cookies → `Blueberry Banana by Cookies.jpg`
- Ganjavores → `Green Crack by Ganjavores - Premium Flower.jpg`
- Muha Meds/Devour → `DeVour Gummy Edibles - Watermelon Slices - 1500mg (150mg ea pc).jpg`
- Jeeter Juice → `Jeeter Juice - Ice Cream Banana (Indica) - Disposable Straw Vape - 1G - Live Resin.jpg`
- Rythm → `London Poundcake (Hybrid) by Rythm - 7G Jars - Premium Whole Flower.jpg`
- Trulieve/Cultivation Labs → `Cultivar Collection by Trulieve - Bubble Gum Kush - Premium Whole Flower.jpg`
- BackpackBoyz → `BackPackBoyz Lemon & Cherriez disposable vape, 2g, All-In-One, Live Resin, Melted Diamonds.jpg`
- Others → `/images/storefront.jpg` (fallback)

### Product Fields
Each product needs: `id`, `name`, `brand`, `category`, `type`, `strain`, `thc`, `terps`, `price`, `oldPrice`, `badge`, `description`, `image`.

## Iconify Integration

### Category Icons
```jsx
import { Icon } from '@iconify/react';
const CATEGORY_ICONS = {
    flower: 'mdi:cannabis',
    preroll: 'mdi:flower',
    cartridge: 'mdi:vape',
    edibles: 'mdi:pill',
    concentrate: 'mdi:droplet',
    topical: 'mdi:band-aid',
    tincture: 'mdi:bottle-tonic-outline',
    accessories: 'mdi:hat-wizard',
};
```

### Brand Logos (Circular)
Brand logos should be displayed in small circular frames. Use the image file from `public/images/` as the logo source.

## CSS Patterns

### Announcement Bar CSS
```css
.announcement-bar {
    background: linear-gradient(90deg, var(--accent), var(--accent-glow), var(--gold), var(--accent-glow), var(--accent));
    background-size: 200% 100%;
    animation: gradient-shift 3s ease infinite;
    padding: 8px 0;
    overflow: hidden;
    white-space: nowrap;
}
@keyframes gradient-shift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
```

### Product Card Link CSS
```css
.product-card-link {
    text-decoration: none;
    color: inherit;
}
.product-card-link:hover .product-card {
    transform: translateY(-6px);
    box-shadow: 0 16px 48px rgba(0,0,0,0.18);
}
```

## Common Build Issues

### `Build Failed Invalid vercel.json file provided`
- **Cause:** Duplicate rewrite entries or malformed JSON in `vercel.json`
- **Fix:** Replace with single clean rewrite: `{ "cleanUrls": true, "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }] }`

### `Missing script: "build"`
- **Cause:** `package.json` lacks `"build": "vite build"`
- **Fix:** Add to scripts section: `"build": "vite build", "dev": "vite", "preview": "vite preview", "start": "vite preview"`

### `Error: Cannot find module` or similar import issues
- **Cause:** Missing `import { Link } from 'react-router-dom'` in App.jsx
- **Fix:** Ensure all React Router hooks are imported: `BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation, Link`

## Git Push Sequence for React Projects
```bash
cd /c/Users/jorda/Desktop/Projects/websites/dreamz-dc-react
git init
git branch -M main
git remote add origin https://github.com/tradersurfer/dreamz-dc.git
git add -A
git commit -m "feat: DREAMZ DC React dispensary"
git push origin main
```

If push is rejected:
```bash
git pull origin main --force --allow-unrelated-histories
# Resolve conflicts, commit, push again
```

## Deployment Verification
```bash
npm run build    # Must succeed locally
cat vercel.json  # Validate JSON
cat package.json # Verify build script
```
