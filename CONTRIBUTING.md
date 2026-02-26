# Contributing to Local AI Job Search Agent

Guidance for adding features and changing behaviour.

---

## Adding a new job source

1. **Create a new module** in `sources/` (e.g. `sources/newsource.py`).
2. **Implement a fetch function** that returns a list of dicts with the same keys as existing sources: `title`, `company`, `location`, `description`, `url`, `salary_min`, `salary_max`, `source` (use a unique value like `"newsource"`).
3. **Use config** for API keys; add a new optional key (e.g. `NEWSOURCE_API_KEY`) and document it in `.env.example`.
4. **Handle errors** with try/except and logging; return an empty list on failure.
5. **Call the new fetcher** from `main.py` in `run_pipeline()` (step 1: fetch from all sources) and gate it on the presence of the API key if optional.
6. **Add tests** in `tests/test_sources.py` for the new module (structure and optional skip).

---

## Modifying filtering rules

- **Hard filter** (salary, location, keywords, seniority): edit `pipeline/hard_filter.py`. Use named constants for salary floor, keyword lists, and seniority words; do not hardcode magic numbers.
- **Blacklist**: the list is loaded from the database in `run_pipeline()` and passed to `passes_hard_filter`. To change how blacklist is matched (e.g. normalisation), update both `pipeline/normalizer.py` (if you add fields) and the blacklist comparison in `hard_filter.py`.
- After changes, run `tests/test_pipeline.py` and extend tests if you add new rules.

---

## Adjusting scoring weights

- **Keyword vs TF-IDF**: in `pipeline/scorer.py`, change `KEYWORD_WEIGHT` (default 0.3) and `TFIDF_WEIGHT` (default 0.7). Ensure they sum to 1.0 if you want the final score in [0, 1].
- **Keyword list**: edit `KEYWORDS_FOR_SCORE` and optionally `KEYWORD_MATCH_CAP` in `scorer.py`.
- **Candidate profile**: edit `CANDIDATE_PROFILE` in `scorer.py` to change the TF-IDF target text.
- Run `tests/test_pipeline.py` to ensure `score_job` still returns a float in [0, 1].

---

## Adding a notification channel

1. **Add config keys** in `config.py` and `.env.example` (e.g. email, webhook URL). Do not commit secrets.
2. **Create a sender function** (e.g. in `notifications/` or alongside `telegram.py`) that takes the same kind of input (job dict or list of jobs) and sends one message. Use try/except and logging; respect rate limits and message length.
3. **Integrate** in `run_pipeline()` for instant alerts (after saving jobs) and/or in `scheduler.py` for the digest, depending on the channel.
4. **Record** sent notifications in the DB if you need cooldown or “already sent” logic (reuse or extend the `notifications` table).
5. **Tests**: mock the send function and test message format and behaviour in `tests/test_notifications.py` or a new test file.

---

## Code style

- **Docstrings**: every module and every function has a docstring (purpose, args, returns).
- **Comments**: inline comments on non-obvious logic.
- **Naming**: clear, descriptive names; constants in UPPER_SNAKE.
- **Imports**: group standard library, then third-party, then local; one per line or grouped logically.
- **Line length**: prefer &lt; 100 characters where readable; break long lines sensibly.

---

## Git commit message format

- Use present tense and imperative: “Add X”, “Fix Y”, “Update Z”.
- First line: short summary (about 50 chars). Optionally follow with a blank line and a longer description.
- Reference slice or patch when fixing a completed slice: “Patch slice 3: allow None salary_min”.

Example:

```
Add a new optional job source (e.g. OpenAI web-search)

- New module in sources/ and optional env key in config.
- Pipeline skips the source when key is empty.
- test_sources.py extended for structure and optional skip.
```
