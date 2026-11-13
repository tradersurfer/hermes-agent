# X (Twitter) Profile Extraction — reference

## What works (validated)
- **Real tab via computer_use:** `list_windows` → find `msedge.exe` → `click` the X tab element → `capture(mode='ax')`. The AX tree shows each post as a `Group` label like:
  `Bitcoin Archive Verified account @BitcoinArchive 15h Perfect execution from El Salvador. 10/10. ... Quote @bitcoinofficesv ... 321 likes, 51889 views`
  Parse with a regex over `<article>` blocks (server shell) or the AX `Group` text.
- **No-login SSRF fallback (curl):** `x.com/<handle>` server-renders ~5 most-recent posts into the HTML even behind the login wall.
  ```bash
  curl -sS -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" "https://x.com/BitcoinArchive" -o ba.html
  # then extract <article>...</article> blocks; strip tags; each yields:
  #   handle, relative time, post body, reply/repost/like/view counts
  ```
  Limitation: **only ~5 posts** via SSRF. The GraphQL API (`/i/api/graphql/...`) returns 403 without the user's browser session, and hardcoding a query ID fails because X rotates them per session.

## What does NOT work
- `browser_*` tools → sandboxed Browserbase, no user session; X returns `ERR_HTTP_RESPONSE_CODE_FAILURE` / login shell.
- `javascript:` bookmarklets in the Edge address bar → blocked by X CSP.
- Synthetic infinite-scroll (wheel/`End`/`window.scrollTo`) → X virtualizes; DOM keeps only ~5 posts, more don't load.
- `api.x.com/1.1/guest/activate.json` → 404; legacy `users/show.json` → 403.

## Practical limits
- Need "last 60 posts"? Not reliably reachable. Accept the ~5 most-recent (SSRF) or ask the user to paste the ones they want.
- Always mark unverified source URLs / exact post links with `[VERIFY]` / `[PULL X POST]` — never invent them.

## Example parse (python, server shell)
```python
import re, html
t = open("ba.html", encoding="utf-8", errors="ignore").read()
for a in re.findall(r"<article.*?</article>", t, re.S):
    s = re.sub(r"<[^>]+>", " ", a)
    s = html.unescape(s); s = re.sub(r"\s+", " ", s).strip()
    print(s[:300])
```
