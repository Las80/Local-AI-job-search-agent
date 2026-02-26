"""
Entry point for the Local AI Job Search Agent.
Starts the Flask UI in a daemon thread and the APScheduler on the main thread.
Configures logging to logs/agent.log and runs the full pipeline on schedule.
"""

import logging
import os
import sys
import threading
from pathlib import Path

import config
from database import db
from pipeline import (
    normalize_job,
    passes_hard_filter,
    score_job,
    generate_hash,
    deduplicate_batch,
)
from notifications.telegram import send_instant_alert
from sources.adzuna import fetch_adzuna_jobs
from sources.reed import fetch_reed_jobs
from sources.openai_web_search import fetch_openai_web_search_jobs

# Project root and log directory
PROJECT_ROOT = Path(__file__).resolve().parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "agent.log"

# Configure logging: file handler to logs/agent.log, INFO level
def _setup_logging() -> None:
    """Configure root logger to write to logs/agent.log with daily rotation."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    from logging.handlers import TimedRotatingFileHandler
    file_handler = TimedRotatingFileHandler(
        LOG_FILE,
        when="midnight",
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    file_handler.setFormatter(formatter)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    # Optionally log to console for local runs
    if os.getenv("CONSOLE_LOG"):
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(formatter)
        root.addHandler(console)


def run_pipeline() -> None:
    """
    Run the full job pipeline: fetch from all sources, normalise, hard filter,
    deduplicate, score, save to DB, and send instant alerts for 100% matches.
    """
    logger = logging.getLogger(__name__)
    # 1. Fetch from all sources
    jobs = []
    try:
        jobs.extend(fetch_adzuna_jobs())
    except Exception as e:
        logger.exception("Adzuna fetch failed: %s", e)
    try:
        jobs.extend(fetch_reed_jobs())
    except Exception as e:
        logger.exception("Reed fetch failed: %s", e)
    if config.config.get("OPENAI_API_KEY"):
        try:
            jobs.extend(fetch_openai_web_search_jobs())
        except Exception as e:
            logger.exception("OpenAI web-search fetch failed: %s", e)
    logger.info("Fetched %d raw jobs from sources", len(jobs))

    # 2. Normalise
    normalised = [normalize_job(j) for j in jobs]
    logger.info("Normalised %d jobs", len(normalised))

    # 3. Hard filter (fetch blacklist from DB)
    blacklist = db.get_blacklist()
    filtered = [j for j in normalised if passes_hard_filter(j, blacklist)]
    logger.info("After hard filter: %d jobs", len(filtered))

    # 4. Generate hash and deduplicate (in-batch + DB)
    unique = deduplicate_batch(filtered)
    logger.info("After deduplication: %d new jobs", len(unique))

    # 5. Score and save
    threshold_instant = config.config.get("MATCH_THRESHOLD", 1.0)
    for job in unique:
        job["match_score"] = score_job(job)
        if db.insert_job(job):
            # Only check for instant alert for newly inserted jobs
            if job["match_score"] >= threshold_instant:
                # Fetch the row to get id for mark_notified
                with db.get_connection() as conn:
                    cur = conn.execute(
                        "SELECT id, title, company, location, url, salary_min, salary_max, source, match_score FROM jobs WHERE hash = ?",
                        (job["hash"],),
                    )
                    row = cur.fetchone()
                if row:
                    job_with_id = dict(row)
                    send_instant_alert(job_with_id)

    logger.info("Pipeline run complete: %d new jobs saved", len(unique))


def main() -> None:
    """Start logging, UI thread, and scheduler."""
    _setup_logging()
    logger = logging.getLogger(__name__)

    # Log startup (no API keys)
    sources_enabled = ["Adzuna", "Reed"]
    if config.config.get("OPENAI_API_KEY"):
        sources_enabled.append("OpenAI web-search")
    logger.info(
        "Local AI Job Search Agent starting — sources: %s",
        ", ".join(sources_enabled),
    )

    # Start Flask UI in daemon thread
    from ui.app import run_ui
    ui_thread = threading.Thread(target=run_ui, daemon=True)
    ui_thread.start()
    logger.info("Flask UI running on http://127.0.0.1:5000")

    # Inject run_pipeline into scheduler and start (blocks)
    import scheduler
    scheduler.run_pipeline = run_pipeline
    scheduler.start_scheduler()


if __name__ == "__main__":
    main()
