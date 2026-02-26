# Slice Plan — Local AI Job Search Agent

Full breakdown of all 8 slices. Each slice has a goal, files created/modified, dependencies, UAT checklist (minimum 5 items), and definition of done.

---

## Slice 0 — Environment and connection tests

**Goal**: Validate that the environment is set up and that Adzuna, Reed, and Telegram are reachable with the provided credentials.

**Files created**  
- `tests/test_connections.py`  
- `.env.example`  
- `requirements.txt`  
- `.gitignore`  

**Files modified**  
- None (bootstrap).

**Dependencies**  
- Python 3.11+, `pip`, `.env` populated from `.env.example`.

**UAT checklist**  
1. Copy `.env.example` to `.env` and set required keys.  
2. Run `python tests/test_connections.py`; Adzuna shows PASS.  
3. Reed shows PASS.  
4. Telegram shows PASS.  
5. Script exits with code 0 when all required pass; exit code 1 if any required fails.

**Definition of done**  
- All required connection tests pass when credentials are valid; script exits with 0 or 1 as above.

---

## Slice 1 — SQLite database and schema

**Goal**: Provide a local SQLite database with jobs, notifications, and blacklist tables and all CRUD operations used by the rest of the app.

**Files created**  
- `database/__init__.py`  
- `database/db.py`  
- `config.py` (if not present; env loading and validation)  

**Files modified**  
- None from Slice 0.

**Dependencies**  
- Slice 0 (config/env for validation if config is used by tests).  
- `tests/test_db.py` (created in this or a test slice).

**UAT checklist**  
1. Run `python tests/test_db.py`; all DB tests pass.  
2. First run creates `jobs.db` and tables (jobs, notifications, blacklist).  
3. `insert_job` and `job_exists` behave correctly; duplicate url/hash does not insert twice.  
4. `get_unnotified_matches`, `mark_notified`, `get_blacklist`, `add_to_blacklist`, `remove_from_blacklist`, `get_all_jobs` behave as specified.  
5. Test DB is temporary and cleaned up after tests.

**Definition of done**  
- Schema and all specified DB functions implemented; test_db passes; no secrets in code.

---

## Slice 2 — Job aggregation (Adzuna, Reed)

**Goal**: Fetch job listings from Adzuna and Reed APIs, normalise to a common schema, and return lists of job dicts.

**Files created**  
- `sources/__init__.py`  
- `sources/adzuna.py`  
- `sources/reed.py`  

**Files modified**  
- None (sources are new).

**Dependencies**  
- Slice 0 (config for API keys).  
- `requests` in requirements.

**UAT checklist**  
1. Adzuna returns a list of dicts with keys: title, company, location, description, url, salary_min, salary_max, source (adzuna).  
2. Reed returns same structure with source "reed".  
3. Rate limiting (e.g. 1s between keyword requests) is in place.  
4. `tests/test_sources.py` passes (structure checks for all sources).

**Definition of done**  
- All source modules implemented; test_sources passes; API errors are caught and logged.

### Slice 2 extension — OpenAI web-search (optional source)

**Goal**: Discover UK job listings via OpenAI Chat Completions with web search (gpt-4o-search-preview), returning the same normalised job schema as other sources.

**Files created**  
- `sources/openai_web_search.py`

**Files modified**  
- `config.py` — added optional `OPENAI_API_KEY`.  
- `.env.example` — documented `OPENAI_API_KEY`.  
- `main.py` — calls `fetch_openai_web_search_jobs()` when key is set; includes "OpenAI web-search" in sources_enabled.  
- `sources/__init__.py` — exports `fetch_openai_web_search_jobs`.  
- `tests/test_sources.py` — added `test_openai_web_search_structure()`.

**Dependencies**  
- Slice 0 (config).  
- `openai` in requirements.

**UAT**  
- When `OPENAI_API_KEY` is set, pipeline fetches from OpenAI web search; jobs have `source="openai_web_search"`. When key is empty, source is skipped.  
- `tests/test_sources.py` includes OpenAI web-search structure check.

---

## Slice 3 — Normalisation and hard filtering

**Goal**: Normalise job text (lowercase, strip HTML, normalized_company / normalized_title) and apply hard filters (blacklist, salary, location, keywords, seniority).

**Files created**  
- `pipeline/__init__.py`  
- `pipeline/normalizer.py`  
- `pipeline/hard_filter.py`  

**Files modified**  
- None.

**Dependencies**  
- Slice 1 (blacklist from DB when used in pipeline).  
- Slice 2 (job dict schema).

**UAT checklist**  
1. `normalize_job` strips HTML and lowercases; adds `normalized_company` and `normalized_title`.  
2. Jobs with company in blacklist are rejected.  
3. Jobs with salary_min < 30000 are rejected; salary_min None is allowed.  
4. Jobs with no AI-related keyword in title/description are rejected.  
5. Senior/lead titles are rejected unless "junior" or "associate" present.  
6. `tests/test_pipeline.py` (normalizer and hard_filter parts) pass.

**Definition of done**  
- Normaliser and hard filter implemented; tests pass; no magic numbers (use constants).

---

## Slice 4 — TF-IDF scoring and deduplication

**Goal**: Score each job (keyword + TF-IDF vs candidate profile), generate URL hash, and deduplicate within batch and against DB.

**Files created**  
- `pipeline/scorer.py`  
- `pipeline/deduplicator.py`  

**Files modified**  
- `pipeline/__init__.py` (export scorer and deduplicator).

**Dependencies**  
- Slice 1 (db.job_exists, hash stored in jobs).  
- Slice 3 (normalised job dict).

**UAT checklist**  
1. `score_job` returns a float in [0, 1].  
2. `generate_hash` is deterministic for same URL.  
3. `deduplicate_batch` removes duplicate URLs within the list.  
4. `deduplicate_batch` excludes jobs already present in DB (by hash).  
5. `tests/test_pipeline.py` (scorer and deduplicator) pass.

**Definition of done**  
- Scorer and deduplicator implemented; tests pass; DB used only via parameterised queries.

---

## Slice 5 — Telegram notifications (instant + digest)

**Goal**: Send instant Telegram alert for 100% match (with cooldown) and daily digest for 75%+ matches; record notifications in DB.

**Files created**  
- `notifications/__init__.py`  
- `notifications/telegram.py`  

**Files modified**  
- Slice 1: ensure `notifications` table and `mark_notified` / digest flags exist.  
- Optional: `database/db.py` — add `get_digest_candidates(threshold)` if not present.

**Dependencies**  
- Slice 1 (notifications table, job id, digest_sent/notified).  
- Config: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, NOTIFICATION_COOLDOWN_SECONDS, DIGEST_THRESHOLD.

**UAT checklist**  
1. Instant alert format includes title, company, location, salary, url, source.  
2. Cooldown prevents duplicate instant alerts for the same job within the configured window.  
3. Digest format includes date, count, and per-job score/title/company/url.  
4. Digest only includes jobs with digest_sent = 0; after send, digest_sent is set.  
5. `tests/test_notifications.py` pass with mocked _send_message (no real messages sent).

**Definition of done**  
- Instant and digest sending implemented; tests pass; message length capped at 4096.

---

## Slice 6 — Scheduler and main pipeline

**Goal**: Run the full pipeline on a schedule (every 4 hours from 6am) and send morning digest at 8am; wire pipeline to DB and Telegram.

**Files created**  
- `main.py`  
- `scheduler.py`  

**Files modified**  
- None (or minimal: scheduler imports run_pipeline from main or vice versa via injection).

**Dependencies**  
- Slices 1–5.  
- APScheduler, logging to `logs/agent.log`.

**UAT checklist**  
1. `python main.py` starts without error; Flask UI is up on 127.0.0.1:5000.  
2. Pipeline runs at 6am and then every 4 hours (manual or time-mock).  
3. Pipeline flow: fetch → normalise → hard filter → dedupe → score → save → instant alerts for 100%.  
4. Digest runs at 8am and sends one message for 75%+ jobs not yet in digest.  
5. Logs show pipeline and digest start/end and duration; single failure does not stop scheduler.

**Definition of done**  
- main.py and scheduler.py implemented; pipeline and digest run as specified; logging in place.

---

## Slice 7 — Flask blacklist UI and jobs viewer

**Goal**: Provide a local web UI for managing the company blacklist and viewing stored jobs.

**Files created**  
- `ui/__init__.py`  
- `ui/app.py`  
- `ui/templates/blacklist.html`  
- `ui/templates/jobs.html`  

**Files modified**  
- `main.py` (start Flask in daemon thread).

**Dependencies**  
- Slice 1 (get_blacklist, add_to_blacklist, remove_from_blacklist, get_all_jobs).  
- Slice 6 (main starts UI thread).

**UAT checklist**  
1. GET / redirects to /blacklist.  
2. GET /blacklist shows current blacklist and form to add company; POST /blacklist/add adds and redirects.  
3. POST /blacklist/remove removes company and redirects.  
4. GET /jobs shows jobs with score, title, company, source, date, link; sorted by match_score desc.  
5. GET /health returns JSON with status and timestamp.  
6. UI is minimal HTML, no external CSS; blacklist and jobs pages have navigation to each other.

**Definition of done**  
- All routes work; blacklist and jobs viewer are usable; UI runs in thread and does not block scheduler.
