# Extracting @BitcoinArchive posts (the REAL tab, not the sandbox)

## Why browser_navigate fails on X
`browser_navigate` / `browser_*` tools run in a SANDBOXED Browserbase instance with NO X
session. X returns a login shell (HTML only, ~5 SSR posts, no auth). Do NOT rely on it for
real post content or for pulling the 60-post window.

## The working path: computer_use on the user's logged-in Edge
The user's X tab is in `msedge.exe` and is already authenticated.

1. `computer_use(action='list_windows')` → confirm `msedge.exe`, note the X tab.
2. `computer_use(action='capture', app='msedge.exe', mode='som')` → find the address bar
   (usually element ~7, role Edit 'Address and search bar').
3. `computer_use(action='set_value', element=7, value='https://x.com/BitcoinArchive/status/<ID>')`
   then `action='key', keys='return', delivery_mode='foreground'` — foreground so the nav
   uses the user's auth cookies.
4. `capture(app='msedge.exe', mode='ax')` → the AX tree exposes the full post:
   handle, @handle, timestamp, body text, reply/repost/like/view counts, and any image link.

## Gotchas (learned the hard way)
- X virtualizes its timeline: only ~5 posts exist in the DOM at once. Scrolling (background
  OR foreground, `End` key, `javascript:` bookmarklets) does NOT reliably load older posts —
  X's CSP blocks injected JS and the lazy-loader needs interaction the sandbox can't fake.
- The RELIABLE method is to navigate the address bar directly to each exact
  `x.com/BitcoinArchive/status/<ID>` URL the user pasted. You get the canonical post + image.
- To read the 60-post profile window, ask the user to paste 10–15 posts, OR navigate status
  URLs one by one. Don't try to scrape 60 via scroll.
- Engagement counts come from the AX labels like "657 Likes. Like" / "54.8K Views".

## Embedded image URLs
Post images are hosted on pbs.twimg.com. Grab the URL from the post DOM (the Image hyperlink)
if you want to download/embed the asset locally.
