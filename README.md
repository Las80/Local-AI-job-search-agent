# Local AI Job Search Agent

> Aggregates UK tech job listings from multiple APIs, scores them with TF-IDF against a candidate profile, and sends Telegram alerts for strong matches. Runs locally with no cloud hosting required.

**Tech stack:** Python 3.11+ · Flask · SQLite · APScheduler · OpenAI API · Telegram Bot API · scikit-learn (TF-IDF)

<!-- Optional: add a screenshot of the Flask UI (e.g. blacklist or jobs page) for portfolio impact:
![Web UI](docs/screenshot.png)
-->

---

A fully local Python application that aggregates job listings from Adzuna, Reed, and (optionally) OpenAI web search, scores them against a candidate profile using TF-IDF and keyword matching, and sends Telegram notifications for strong matches. No cloud hosting required.

## What it does

- **Fetches jobs** from Adzuna, Reed, and (optionally) OpenAI web search using UK-focused searches for AI, automation, and related roles.
- **Filters** listings by salary floor (£30k), location (UK only), required keywords (AI, Python, LLM, etc.), and seniority (excludes senior/lead unless junior/associate).
- **Scores** each job with a mix of keyword count and TF-IDF similarity to a candidate profile (junior/associate AI automation, LLM integration, prompt engineering).
- **Stores** everything in a local SQLite database (`jobs.db`) and supports a **company blacklist** so you can hide recruiters or employers you don’t want to see.
- **Notifies** via Telegram:
  - **Instant alert** when a job scores at or above the configured threshold (default 50%).
  - **Daily digest** at 8am for all jobs scoring 50% or above that haven’t been in a digest yet.
- **Runs on a schedule** every 4 hours from 6am (6am, 10am, 2pm, 6pm, 10pm, 2am) using APScheduler.
- **Web UI** on `http://localhost:5000` for managing the blacklist and viewing stored jobs.

## Prerequisites

- **Python 3.11+**
- API keys and tokens (see Setup below):
  - Adzuna (App ID + API Key)
  - Reed (API Key)
  - OpenAI (API Key, optional — for web-search job discovery)
  - Telegram (Bot Token + Chat ID)

## Setup

1. **Clone or download** the project into a folder (e.g. `job-search-agent`).

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   # or: source .venv/bin/activate   # macOS/Linux
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   - Copy `.env.example` to `.env`.
   - Fill in all required keys (see comments in `.env.example`):
     - `ADZUNA_APP_ID`, `ADZUNA_API_KEY` — from [Adzuna Developer](https://developer.adzuna.com/).
     - `REED_API_KEY` — from [Reed API](https://www.reed.co.uk/developers).
     - `OPENAI_API_KEY` — optional; leave empty to skip OpenAI web-search source.
     - `TELEGRAM_BOT_TOKEN` — from [@BotFather](https://t.me/BotFather).
     - `TELEGRAM_CHAT_ID` — your chat ID (e.g. from [@userinfobot](https://t.me/userinfobot)).

5. **Run connection tests** (optional but recommended):
   ```bash
   python tests/test_connections.py
   ```
   You should see `PASS` for Adzuna, Reed, and Telegram.

6. **Start the application**:
   ```bash
   python main.py
   ```
   - The Flask UI will be available at **http://127.0.0.1:5000**.
   - The scheduler will run in the foreground (pipelines every 4 hours, digest at 8am).

## Blacklist UI (localhost:5000)

- Open **http://127.0.0.1:5000** (or **http://127.0.0.1:5000/blacklist**).
- **Add** a company: type the name and click “Add”. That company will be excluded from all future results.
- **Remove** a company: click “Remove” next to its name.
- Use the link to **View jobs** to see all stored jobs with score, title, company, source, and date.

## Notifications

- **Instant alert**: when a new job is saved with a match score at or above the configured threshold (default 50%), the agent sends one Telegram message with title, company, location, salary, and link. The same job is not re-sent within the cooldown window (default 1 hour).
- **Daily digest**: every day at 8am (configurable via `DIGEST_TIME`), the agent sends one message listing all jobs with score ≥ 50% that have not yet been included in a digest, with score, title, company, and link.

## Project structure

- `.env.example` — Example environment variables (copy to `.env`).
- `.gitignore` — Ignores `.env`, `*.db`, `logs/`, `.venv/`, etc.
- `config.py` — Loads and validates `.env`, exports `config` dict.
- `main.py` — Entry point: logging, UI thread, scheduler.
- `scheduler.py` — APScheduler: pipeline every 4h, digest at 8am.
- `database/` — SQLite schema and CRUD (`db.py`).
- `sources/` — Adzuna, Reed, OpenAI web-search clients.
- `pipeline/` — Normaliser, hard filter, scorer, deduplicator.
- `notifications/` — Telegram instant alert and digest.
- `ui/` — Flask app and templates (blacklist, jobs list).
- `tests/` — Connection, DB, sources, pipeline, notifications tests.
- `logs/` — Application log file (`agent.log`).
- `README.md`, `ARCHITECTURE.md`, `BEST_PRACTICES.md`, `SLICE_PLAN.md`, `CONTRIBUTING.md`.

## Running tests

From the project root:

```bash
python tests/test_connections.py   # API and Telegram connectivity
python tests/test_db.py             # Database operations
python tests/test_sources.py        # Source adapters (structure)
python tests/test_pipeline.py       # Normaliser, filter, scorer, dedupe
python tests/test_notifications.py # Telegram formatting (mocked)
```

Each script prints PASS/FAIL and exits with code 1 if any test fails.

## Troubleshooting

- **Missing required environment variables**: Copy `.env.example` to `.env` and set every required key. The app will raise `EnvironmentError` on startup if any are missing.
- **Adzuna/Reed/Telegram FAIL in test_connections.py**: Check API keys and network. Ensure no firewall blocks the APIs.
- **No jobs appearing**: Confirm keywords and filters in `pipeline/hard_filter.py` and `sources/*.py` match the roles you want. Check `logs/agent.log` for fetch and filter counts.
- **Telegram not receiving messages**: Verify `TELEGRAM_CHAT_ID` is correct and you have started a chat with the bot (e.g. sent `/start`).
- **Database locked**: Only one process should run `main.py`. Close any other instance or tools that have `jobs.db` open.
