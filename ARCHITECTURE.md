# Architecture — Local AI Job Search Agent

## Data flow (ASCII)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           main.py (entry point)                          │
│  • Starts Flask UI (daemon thread)                                       │
│  • Starts APScheduler (blocking)                                         │
└─────────────────────────────────────────────────────────────────────────┘
                    │                                    │
                    ▼                                    ▼
┌──────────────────────────────┐         ┌──────────────────────────────┐
│   scheduler.py                │         │   ui/app.py (Flask)           │
│   • Pipeline every 4h from 6am │         │   • GET /blacklist, /jobs      │
│   • Digest daily at 8am       │         │   • POST /blacklist/add|remove │
└──────────────────────────────┘         └──────────────────────────────┘
                    │                                    │
                    ▼                                    │
┌──────────────────────────────┐                        │
│   run_pipeline()              │                        │
│   1. Fetch (sources)         │                        │
│   2. Normalise (pipeline)    │                        │
│   3. Hard filter (pipeline)  │◄───────────────────────┘
│   4. Dedupe (pipeline + db)  │     blacklist from db
│   5. Score (pipeline)        │
│   6. Save (db)              │
│   7. Instant alerts (Telegram)                        │
└──────────────────────────────┘
                    │
    ┌───────────────┼───────────────┐
    ▼               ▼               ▼
┌─────────┐  ┌─────────────┐  ┌─────────────┐
│ sources │  │  pipeline   │  │ database    │
│ Adzuna  │  │ normalizer  │  │ jobs        │
│ Reed    │  │ hard_filter │  │ notifications│
│ OpenAI  │  │ scorer      │  │ blacklist   │
└─────────┘  │ deduplicator│  └─────────────┘
             └─────────────┘
                    │
                    ▼
             ┌─────────────┐
             │ notifications│
             │ Telegram     │
             └─────────────┘
```

## Components

- **config.py**: Loads `.env` via python-dotenv, validates required keys, exports a single `config` dict. No secrets in code.
- **database/db.py**: SQLite context manager, schema creation, and all DB operations (jobs, notifications, blacklist). Parameterised queries only.
- **sources/adzuna.py, reed.py, openai_web_search.py**: HTTP/API clients for each source. Return normalized job dicts (title, company, location, description, url, salary_min, salary_max, source). Rate limiting and timeouts applied.
- **pipeline/normalizer.py**: Lowercases and strips text, strips HTML from description, adds `normalized_company` and `normalized_title`.
- **pipeline/hard_filter.py**: Applies blacklist, salary floor (£30k), UK-only location, required keywords (AI, Python, LLM, etc.), and seniority (reject senior/lead unless junior/associate).
- **pipeline/scorer.py**: Keyword score (weight 0.3) + TF-IDF cosine similarity to candidate profile (weight 0.7). Output in [0, 1].
- **pipeline/deduplicator.py**: SHA256 hash of URL; in-batch dedupe and DB check via `job_exists`.
- **notifications/telegram.py**: Instant alert for 100% match (with cooldown), daily digest for 75%+ matches. Uses Telegram Bot API with HTML and 4096-char limit.
- **ui/app.py**: Flask on 127.0.0.1:5000. Routes: /, /blacklist, /blacklist/add, /blacklist/remove, /jobs, /health.
- **scheduler.py**: APScheduler (BlockingScheduler). Pipeline job every 4 hours starting 6am; digest cron at 8am.

## Database schema

**jobs**

| Column       | Type    | Notes                          |
|-------------|---------|---------------------------------|
| id          | INTEGER | PRIMARY KEY AUTOINCREMENT      |
| title       | TEXT    | NOT NULL                       |
| company     | TEXT    | NOT NULL                       |
| location    | TEXT    |                                |
| description | TEXT    |                                |
| url         | TEXT    | UNIQUE NOT NULL                |
| salary_min  | INTEGER |                                |
| salary_max  | INTEGER |                                |
| source      | TEXT    | adzuna / reed / openai_web_search |
| match_score | REAL    | 0.0–1.0                       |
| hash        | TEXT    | UNIQUE NOT NULL (SHA256 of URL)|
| created_at  | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP    |
| notified    | INTEGER | DEFAULT 0 (1 = instant sent)   |
| digest_sent | INTEGER | DEFAULT 0 (1 = in digest)     |

**notifications**

| Column           | Type      | Notes                          |
|------------------|-----------|---------------------------------|
| id               | INTEGER   | PRIMARY KEY AUTOINCREMENT      |
| job_id           | INTEGER   | REFERENCES jobs(id)             |
| sent_at          | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP      |
| notification_type| TEXT      | 'instant' or 'digest'          |

**blacklist**

| Column   | Type      | Notes                          |
|----------|-----------|---------------------------------|
| id       | INTEGER   | PRIMARY KEY AUTOINCREMENT      |
| company  | TEXT      | UNIQUE NOT NULL                |
| added_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP      |

## Notification logic and thresholds

- **Instant alert**: When a newly saved job has `match_score >= MATCH_THRESHOLD` (default 1.0). One message per job; same job not sent again within `NOTIFICATION_COOLDOWN_SECONDS` (default 3600). `notified` set to 1 and a row added to `notifications` with type `instant`.
- **Digest**: Once per day at `DIGEST_TIME` (default 08:00). Select jobs with `match_score >= DIGEST_THRESHOLD` (default 0.75) and `digest_sent = 0`. Send one message listing them; then set `digest_sent = 1` and insert `notifications` with type `digest`.

## Scheduling logic

- **Pipeline**: Interval job, every 4 hours, first run at 06:00 on the day the app starts. So 6am, 10am, 2pm, 6pm, 10pm, 2am.
- **Digest**: Cron trigger at hour=8, minute=0 (or from `DIGEST_TIME` in config).
- Both jobs are wrapped in try/except so a single failure does not stop the scheduler.

## Security model

- All secrets in `.env`; never committed. `.env.example` documents keys only.
- No secrets in logs or code. No API keys in error messages.
- HTTP requests use `timeout=10`. API keys sent only over HTTPS to official API endpoints.
- Flask runs on 127.0.0.1:5000; not exposed to the network unless the user forwards the port.
- SQLite file `jobs.db` is local; parameterised queries prevent injection.
