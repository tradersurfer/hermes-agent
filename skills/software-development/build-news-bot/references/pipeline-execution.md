# Pipeline Execution Reference

## Running the Bot

### Test (no posting)
```bash
"C:\Users\jorda\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" main.py --test
```
Expected output with no API keys: 0 stories from each source, but pipeline executes end-to-end without crashes.

### Single cycle
```bash
"C:\Users\jorda\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" main.py --once
```

### Continuous (5-min default)
```bash
"C:\Users\jorda\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" main.py
```

### Custom interval
```bash
"C:\Users\jorda\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" main.py --interval 10
```

## What the Test Cycle Shows

When running `--test` with no API keys configured:
- Google Search: 0 stories (GOOGLE_API_KEY and GOOGLE_CX are placeholders)
- X Profiles: 401 Unauthorized for all profiles (TWITTER_BEARER_TOKEN not set)
- SEC EDGAR: Successfully queries EDGAR, returns filings (may be 0 Bitcoin-relevant)
- AI Processing: 0 drafts (no stories to process)
- No crash, exit code 0

This confirms the pipeline works. Fill `.env` with real keys for production.

## PR Status

PR #1 is open at https://github.com/tradersurfer/news-fetcher-bot/pull/1
Branch: `v2.0-branch` → `main`

## .env Setup Checklist

Before running production, ensure `.env` contains:
- `ANTHROPIC_API_KEY` — from console.anthropic.com
- `TWITTER_BEARER_TOKEN`, `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_SECRET` — from developer.x.com
- `GOOGLE_API_KEY` — from Google Cloud Console
- `GOOGLE_CX` — Custom Search Engine ID from Google

Copy from `.env.template` and fill in real values.

## Source Priority Order

1. Google Search (PRIMARY) — 16 Bitcoin queries
2. X Profiles (SECONDARY) — 28+ handles
3. SEC EDGAR (TERTIARY) — 10-K/10-Q/8-K filings
4. AI Processing — Claude 3 draft options
5. X Poster — Direct posting to @AdrianJordan_io
