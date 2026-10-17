# Bot Architecture Reference

## File Structure

```
news-fetcher-bot/
├── main.py                  # Entry point with CLI args
├── requirements.txt         # Python dependencies
├── .env.template            # Environment template
├── README.md               # This file
├── core/
│   ├── __init__.py         # Core module exports
│   └── config.py           # Shared config, models, dedup engine
├── modules/
│   ├── x_scraper.py        # Fetch posts from X profiles
│   ├── google_search.py    # Google Advanced Search for Bitcoin news
│   ├── sec_edgar.py        # SEC EDGAR filings (10-K, 8-K, 10-Q)
│   ├── ai_processor.py     # Claude-based headline rewriting
│   ├── x_poster.py         # Direct posting to @AdrianJordan_io
│   └── orchestrator.py     # Main scheduler + pipeline
└── sources/
    └── x_profiles.py       # X profiles to monitor
```

## Pipeline Flow

```
sources (X profiles, Google, SEC EDGAR)
    ↓
Dedup Engine (seen_stories.json)
    ↓
AI Processor (Claude → 3 draft options)
    ↓
X Poster (direct to @AdrianJordan_io)
```

## Data Models (core/config.py)

- `RawStory`: title, url, source, source_type, posted_at, fetched_at
- `DraftPost`: story_id, raw_title, option_1/2/3, credit_line

## Environment Variables

```env
ANTHROPIC_API_KEY=
TWITTER_BEARER_TOKEN=
TWITTER_API_KEY=
TWITTER_API_SECRET=
TWITTER_ACCESS_TOKEN=
TWITTER_ACCESS_SECRET=
TARGET_HANDLE=AdrianJordan_io
GOOGLE_API_KEY=
GOOGLE_CX=
FETCH_INTERVAL_MINUTES=5
SEC_CIK_NUMBERS=0001350862
SEEN_STORIES_FILE=seen_stories.json
MIN_POST_GAP_SECONDS=300
```
