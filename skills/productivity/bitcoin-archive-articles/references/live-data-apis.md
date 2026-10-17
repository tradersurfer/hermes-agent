# Live data APIs that WORK from this environment (Windows sandbox)

Use these for real figures in articles. Search engines (Google/Bing) and most rate-limited
crypto APIs are unreliable here — see below.

## BTC price / block height (verified working)
- `https://api.blockchain.info/stats`
  Returns JSON with `market_price_usd` (live USD price) and `n_blocks_total` (block height).
  Example call: `curl -sS "https://api.blockchain.info/stats"` then parse `.market_price_usd`.
  In-session result: price ~$77,857, height 964,598.

## Block height only
- `https://mempool.space/api/blocks/tip/height` → returns the current block height as text.
  (Note: `mempool.space/api/price` 404s — don't use it for price.)

## Known-broken / rate-limited (don't waste turns)
- `api.coingecko.com/api/v3/simple/price` → HTTP 429 rate limit (free tier, shared IP).
- `api.coingecko.com/api/v3/companies/public_treasury/bitcoin` → empty `companies` array
  under rate limit.
- `nayibtracker.com` / `strategytracker.com` → redirect loop, no clean JSON.
- Google / Bing search via `browser_navigate` → CAPTCHA / JS-only, no result text.
- DuckDuckGo HTML scrape → blocked.

## Consistency check (useful sanity test)
If a post says "X million buys N BTC", implied price = $Xm / N. It should be within a few %
of the live blockchain.info price. In-session: Strive $66M / 843 BTC = ~$78,288, vs live
$77,857 — consistent. Use this to validate pulled numbers.
