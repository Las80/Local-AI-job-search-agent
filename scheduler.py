"""
APScheduler setup for the Local AI Job Search Agent.
Runs the pipeline every 4 hours starting at 6am and the morning digest at 8am.
All jobs are wrapped in try/except so a single failure does not stop the scheduler.
"""

import logging
from datetime import date, datetime, time

from apscheduler.schedulers.blocking import BlockingScheduler

import config
from database import db
from notifications.telegram import send_digest

# Set by main.py before start_scheduler() to avoid circular import
run_pipeline = None

logger = logging.getLogger(__name__)


def send_morning_digest() -> None:
    """
    Fetch jobs eligible for digest (score >= DIGEST_THRESHOLD, not yet sent)
    and send a single Telegram digest message. Logs start, end, and duration.
    """
    start = datetime.utcnow()
    logger.info("Morning digest started at %s", start.isoformat())
    try:
        threshold = config.config.get("DIGEST_THRESHOLD", 0.75)
        jobs = db.get_digest_candidates(threshold)
        if jobs:
            send_digest(jobs)
            logger.info("Digest sent for %d jobs", len(jobs))
        else:
            logger.info("Digest skipped: no eligible jobs")
    except Exception as e:
        logger.exception("Morning digest failed: %s", e)
    end = datetime.utcnow()
    logger.info("Morning digest ended at %s (duration: %s)", end.isoformat(), end - start)


def _run_pipeline_safe() -> None:
    """Wrapper that runs the pipeline and catches any exception so the scheduler keeps running."""
    start = datetime.utcnow()
    logger.info("Pipeline run started at %s", start.isoformat())
    try:
        if run_pipeline is None:
            logger.error("run_pipeline not set; cannot run pipeline")
            return
        run_pipeline()
    except Exception as e:
        logger.exception("Pipeline run failed: %s", e)
    end = datetime.utcnow()
    logger.info("Pipeline run ended at %s (duration: %s)", end.isoformat(), end - start)


def start_scheduler() -> None:
    """
    Start the blocking APScheduler: pipeline every 4 hours from 6am, digest at 8am.
    Does not return until the scheduler is shut down.
    """
    sched = BlockingScheduler()
    # Pipeline: every 4 hours, first run at 06:00 today
    start_date = datetime.combine(date.today(), time(6, 0))
    sched.add_job(_run_pipeline_safe, "interval", hours=4, start_date=start_date, id="pipeline")
    # Digest: daily at 8am (use config DIGEST_TIME)
    digest_time = config.config.get("DIGEST_TIME", "08:00")
    parts = digest_time.split(":")
    hour = int(parts[0]) if len(parts) > 0 else 8
    minute = int(parts[1]) if len(parts) > 1 else 0
    sched.add_job(send_morning_digest, "cron", hour=hour, minute=minute, id="digest")
    logger.info("Scheduler started: pipeline every 4h from 6am, digest at %s", digest_time)
    sched.start()
