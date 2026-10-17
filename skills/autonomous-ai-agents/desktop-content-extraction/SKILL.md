---
name: desktop-content-extraction
description: Grab the user's browser via computer_use, not browser_*.
---

# Desktop Content Extraction (real machine, not sandbox)

## The core distinction — read this first
- `browser_navigate` / `browser_snapshot` / `browser_console` connect to a **separate, sandboxed Browserbase session**. It does NOT carry the user's logins, cookies, or open tabs. If the user references something in *their* browser, these tools will fail, hit bot-walls, or return a login shell with no data — and `browser_console` evaluations run in that empty sandbox, not the user's tab.
- `computer_use` drives the **user's actual desktop** (background, no cursor steal). Their real apps, sessions, and tabs are reachable here.

**Rule: when the user points at content in their open app/tab, route to `computer_use`, not `browser_*`.**

## How to extract from an open tab (computer_use)
1. `computer_use(action='list_windows')` → find the app (e.g. `msedge.exe`) and confirm the right tab is open.
2. If the target tab isn't frontmost, `click` its tab element (background) to focus it.
3. `capture(app=<app>, mode='ax')` or `mode='som'`. The AX tree exposes each post/tweet as a `Group`/`Text` label containing the full post text + engagement counts. Parse these.
4. For URLs, `set_value` on the address-bar `Edit` element, then `key` `return` with `delivery_mode='foreground'` (Edge/Chrome drop background key/scroll events).

## Gotchas baked in from real use
- **Lazy-loaded / virtualized timelines** (X especially): only ~5 items exist in the DOM at once. Synthetic infinite-scroll often does NOT force more to load. If you need more, ask the user to paste, or accept the N most-recent visible posts.
- **`javascript:` bookmarklets are blocked** by X's CSP via the address bar — don't rely on injecting scrapers.
- **Background scroll/keys dropped** on Edge/Chrome class → use `delivery_mode='foreground'` (briefly fronts the window).
- **SSRF fallback**: `curl https://x.com/<handle>` returns the server-rendered shell containing the ~5 most-recent posts' text + like/view counts (even behind the login wall). Useful when you only need the latest few and can't drive the UI. See `references/x-profile-extraction.md`.

## Verify, don't fabricate
Extracted text is ground truth — embed it verbatim (with attribution). For originating source URLs or exact post links you couldn't reach, mark `[VERIFY]` / `[PULL X POST]` rather than inventing a link or quote.

## Support files
- `references/x-profile-extraction.md` — X-specific quirks + the working no-login curl SSRF recipe.
