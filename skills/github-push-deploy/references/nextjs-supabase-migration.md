# Next.js + Supabase Migration Guide

## Background

Migrated DREAMZ DC dispensary from React/Vite single-page app to Next.js 16 App Router with Supabase SSR backend. This guide captures the key patterns and pitfalls encountered during the migration.

## Architecture: Two Supabase Clients

Next.js App Router requires distinct clients for server and browser:

### Browser Client (Client Components)
Used in components with `"use client"` directive that use hooks like `useState`, `useEffect`:
```typescript
import { createBrowserClient } from '@supabase/ssr'

export function createBrowserSupabaseClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
}
```

### Server Client (Server Components)
Used in async server components for data fetching:
```typescript
import { createServerClient } from '@supabase/ssr'

export function createServerSupabaseClient() {
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { cookies: { getAll: () => [], setAll: () => [] } }
  )
}
```

## Environment Variable Prefixing

**CRITICAL**: Next.js strictly isolates server/browser environments:

- `NEXT_PUBLIC_SUPABASE_URL` — required for browser client
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` — required for browser client
- `SUPABASE_SERVICE_ROLE_KEY` — server-only, no `NEXT_PUBLIC_` prefix

If keys are not prefixed `NEXT_PUBLIC_`, browser components read them as `undefined`, causing silent connection failures.

## Vercel Environment Sync

Local `.env.local` does NOT track to GitHub. Must explicitly add `NEXT_PUBLIC_` variables in:
- Vercel Dashboard → Project Settings → Environment Variables
- Railway Dashboard → Project Settings → Environment Variables

## Page Structure

```
src/app/
├── layout.tsx          # Root layout (server component)
├── page.tsx            # Home page (server component, fetches products)
├── globals.css         # Tailwind + custom CSS
├── shop/
│   └── page.tsx        # Shop page ("use client", fetches from Supabase)
├── product/
│   └── [id]/
│       └── page.tsx    # Product detail ("use client", fetches by ID)
├── blog/
│   ├── page.tsx        # Blog listing (server component)
│   └── [id]/
│       └── page.tsx    # Blog article (server component)
├── admin/
│   └── page.tsx        # Admin dashboard ("use client", login)
├── brands/
│   └── page.tsx        # Brands page (server component)
├── checkout/
│   └── page.tsx        # Checkout page
└── not-found.tsx       # 404 page
```

## Common Issues

### Build fails with `next` not found
Ensure `next` is in dependencies, not devDependencies. Run `npm install`.

### Supabase connection fails silently
Check that `NEXT_PUBLIC_` prefix is on all browser-accessible env vars. Verify in Vercel dashboard.

### Images not showing
Copy images to `public/images/`. Vercel serves from `/images/` path.

### Package.json missing build script
Ensure `"build": "next build"` is in scripts section.

## Deployment Sequence

1. `npm run build` — must succeed locally
2. `git add . && git commit -m "feat: Next.js + Supabase migration"`
3. `git push origin main`
4. Vercel auto-deploys on push
5. Verify env vars in Vercel dashboard

## Key Lessons

- Always use `NEXT_PUBLIC_` prefix for env vars accessed by client components
- Server components fetch data directly; client components use browser client
- The old single global Supabase client pattern does NOT work in Next.js App Router
- `.env.local` is gitignored — env vars must be set in hosting dashboard
- `@supabase/ssr` package provides both client types — install it alongside `@supabase/supabase-js`
