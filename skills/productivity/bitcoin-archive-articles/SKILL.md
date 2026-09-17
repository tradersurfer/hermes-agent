---
name: bitcoin-archive-articles
description: Compose Bitcoin Archive articles from X posts.
---

# Bitcoin Archive Article Production

Use when the user (jorda) hands you a Bitcoin news topic, an X post link, or a batch of
@BitcoinArchive posts and wants a finished website article for bitcoinarchive.co — copy-paste
ready in both HTML and Markdown.

## Trigger
- User says "write an article", "compose for Bitcoin Archive", pastes X post URLs/links, or
  references their X account / Archie / the website.
- This is a STANDING recurring task: jorda runs the @BitcoinArchive X account and writes the
  site's articles. Expect repeated use.

## HARD RULE — NO HOLLOW SHELLS (the #1 thing the user rejected)
The user explicitly said an earlier deliverable was useless because it had "no real written
body content at all, no pulled x posts." Every article MUST contain:
- A real, researched, multi-paragraph body (not placeholders, not "[VERIFY]" stubs).
- Real pulled X posts rendered as styled embeds WITH working `x.com/.../status/<id>` URLs.
- A Key Takeaway box at the top.

If you cannot verify a specific figure, either (a) pull it from the user's live X tab or a
live data API, or (b) phrase it as a general established fact — never leave `[VERIFY]` markers
in the final copy. BA's style guide says "verify, don't fabricate," but an empty shell is worse
than a fully-written article with one honestly-sourced caveat. Accuracy and completeness are
BOTH required.

If an X post URL has not been verified via the user's live Edge tab, render the x-embed with
`href="#"` and a `TODO_PULL_FROM_X` comment in the draft dict — then regenerate after
pushing the real URL. Better a `#` placeholder than a fabricated status link.

### Data APIs verified working (2026-08-29 session)
- `https://api.blockchain.info/stats` → live BTC price (`market_price_usd`) + block height (`n_blocks_total`). In-session: ~$78,390 / height 964,598.
- `https://mempool.space/api/blocks/tip/height` → block height as text (`mempool.space/api/price` 404s).
- `https://query1.finance.yahoo.com/v8/finance/chart/MSTR?range=5d&interval=1d` → MSTR closes. In-session: ~$127.31 (range $122–137).

### Known-broken / rate-limited (don't waste turns)
- `api.coingecko.com` (simple price, treasury, historical) → 429 / empty / wrong path.
- `nayibtracker.com` / `strategytracker.com` → redirect loop.
- Google/Bing via `browser_navigate` → CAPTCHA/JS-only. DuckDuckGo HTML scrape → blocked.

## SECONDARY RULE — VERIFY CLAIMS THAT SOUND SPECIFIC
Claims like "controls ~4% of all bitcoin," "carrying $X unrealized profit," or any ratio/
percentage the model computes itself should be sanity-checked with arithmetic before
publishing. The user noticed and flagged the earlier % claim. When in doubt, show the math
(e.g. "845,050 / 21,000,000 = 4.02%") in the article or confirm against a known source.

## Output rules — HARD (user-corrected 2026-08-31)
- **HTML ONLY.** Do NOT emit `.md` files. The user never finds the md and it adds a step. Emit `.html` into `articles/` only.
- **Present the final article inline in chat** when done (paste the full HTML or a direct link to the article). The user has to search too hard to find finished articles.
- **Speed matters.** These are news articles that go live hours after announcement. Fast path:
  1. Pull X posts from the live Edge tab (computer_use) or use the SEC 8-K PDF the user dropped.
  2. Write the draft dict inline (one Python file or a JSON literal).
  3. Run `gen_html.py` (not `gen_article.py`) → emits `.html` only, no md.
  4. Present the article in chat. Done.
- Do NOT run more than one round of regeneration unless the user explicitly asks. Get it close, ship it, iterate on feedback.
- Images: reference the local asset path as a placeholder comment in the HTML so Archie can drop the image in. Do NOT spend turns analyzing/rotating images unless the user asks — use a `TODO: image` comment if no image is assigned yet.
- Orange eyebrow category label (BITCOIN / CHARTS / MARKETS / WORLD / TREASURIES / MINING &
  ENERGY / ADOPTION & PAYMENTS / CULTURE).
- H1 headline, byline "Published <date> · By Archie".
- Key Takeaway box (orange left border) directly under the byline — 2 short paragraphs.
- Body: 2–3 min read for NEWS; longer / deeper for TRENDING.
- Pulled X posts as styled cards (handle + text + "via X" + link).
- Sources & References list at the bottom.
- NO X hashtags in article body. Author is always "Archie".

## Workflow
1. Gather the topic + any X links the user pasted.
2. Research the subject:
   - Live BTC price / block height → references/live-data-apis.md.
   - Real @BitcoinArchive post text + engagement + image → references/x-extraction.md
     (pull from the user's LOGGED-IN Edge tab via computer_use — not browser_navigate).
3. Write a draft dict (schema below) or import `build()` from scripts/gen_article.py and call it.
4. Run the generator → emits `<BA_WORKFLOW>/articles/<slug>.html` + `.md`.
5. Verify output: no literal `**` in HTML, x-embed cards present with real URLs, Key Takeaway
   present (re-run build() on a test draft and assert on the produced files, then delete the
   test artifacts).

### Draft dict schema (passed to build())
```
{
  "category": "MARKETS",
  "type": "NEWS",            # NEWS | TRENDING
  "headline": "...",
  "date": "29 August 2026",
  "slug": "my-article-slug",
  "key_takeaway": ["Para 1.", "Para 2."],
  "body_md": "Full markdown body...",
  "asset": "C:/path/to/img.png",   # optional
  "sources": ["Text – Publication (https://...)"],
  "x_posts": [ {"quote": "...", "handle": "@BitcoinArchive", "url": "https://x.com/.../status/<id>"}, ... ]
}
```

## Output location
Canonical working dir: `C:\Users\jorda\bitcoin-archive-workflow\` (templates/, workflow/,
articles/). The generator defaults there; override with the `BA_WORKFLOW` env var.

## Pitfalls
- browser_navigate / browser_* tools hit a SANDBOXED Browserbase instance, NOT the user's
  machine — X returns only a login shell there. To read the user's real X tab, use computer_use
  on `msedge.exe` (see references/x-extraction.md).
- Search engines (Google/Bing) block the sandbox IP (CAPTCHA / JS-only). Don't rely on
  browser_navigate for web research in this environment.
- X virtualizes its timeline — only ~5 posts in the DOM at once; scroll/End only partially
  loads; `javascript:` bookmarklets are blocked by CSP. The RELIABLE path is to navigate the
  address bar to the exact status URL and capture.
- CoinGecko API is rate-limited (429); `mempool.space/api/price` 404s. Use
  `api.blockchain.info/stats` for live price.
- Never emit `[VERIFY]` / `[PULL X POST]` placeholders in the final copy.

## Support files
- `references/style-rules.md` — BA formatting rules, condensed from Style Guide 2.pdf.
- `references/x-extraction.md` — pulling @BitcoinArchive posts from the logged-in Edge tab.
- `references/live-data-apis.md` — live price / block-height endpoints that work here.
- `templates/article-template.html` / `article-template.md` — BA layout scaffolds.
- `scripts/gen_article.py` — draft dict → `.html` + `.md` (Key Takeaway, x-embed cards,
  inline `**bold**`, pipe tables).
