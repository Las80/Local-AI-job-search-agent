"""
Telegram notification layer for the Local AI Job Search Agent.
Sends instant alerts for 100% matches and a daily digest for 75%+ matches
via the Telegram Bot API. Implements cooldown to avoid duplicate alerts.
"""

import logging
import time
from datetime import datetime
from typing import Any

import requests

import config
from database import get_connection, mark_notified as db_mark_notified

logger = logging.getLogger(__name__)

# Telegram Bot API base URL (token appended)
TELEGRAM_API_BASE = "https://api.telegram.org/bot"
# Maximum message length allowed by Telegram
TELEGRAM_MAX_MESSAGE_LENGTH = 4096
# HTTP request timeout
REQUEST_TIMEOUT_SECONDS = 10


def _send_message(text: str) -> bool:
    """
    Send a single message to the configured Telegram chat. Truncates to 4096 chars.
    Does not enforce cooldown; caller must check before sending instant alerts.

    Args:
        text: Message body (HTML or plain). Will be truncated if over limit.

    Returns:
        True if the API returned success, False otherwise.
    """
    token = config.config["TELEGRAM_BOT_TOKEN"]
    chat_id = config.config["TELEGRAM_CHAT_ID"]
    if not token or not chat_id:
        logger.warning("Telegram not configured; skip send")
        return False
    if len(text) > TELEGRAM_MAX_MESSAGE_LENGTH:
        text = text[: TELEGRAM_MAX_MESSAGE_LENGTH - 3] + "..."
    url = f"{TELEGRAM_API_BASE}{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        logger.error("Telegram send failed: %s", e)
        return False


def _recently_notified(job_id: int) -> bool:
    """Return True if this job was sent an instant alert within cooldown window."""
    cooldown = config.config.get("NOTIFICATION_COOLDOWN_SECONDS", 3600)
    try:
        with get_connection() as conn:
            cur = conn.execute(
                """
                SELECT 1 FROM notifications
                WHERE job_id = ? AND notification_type = 'instant'
                  AND (strftime('%s', 'now') - strftime('%s', sent_at)) < ?
                LIMIT 1
                """,
                (job_id, cooldown),
            )
            return cur.fetchone() is not None
    except Exception as e:
        logger.warning("Cooldown check failed: %s", e)
        return True


def send_instant_alert(job: dict[str, Any]) -> bool:
    """
    Send an instant Telegram alert for a 100% match. Respects cooldown per job_id.
    Message includes title, company, location, salary, url, source.

    Args:
        job: Job dict with id, title, company, location, url, salary_min, salary_max, source.

    Returns:
        True if message was sent successfully, False otherwise.
    """
    job_id = job.get("id")
    if job_id is not None and _recently_notified(job_id):
        logger.debug("Skip instant alert for job_id=%s (cooldown)", job_id)
        return False
    salary_min = job.get("salary_min")
    salary_max = job.get("salary_max")
    salary_str = "N/A"
    if salary_min is not None or salary_max is not None:
        parts = []
        if salary_min is not None:
            parts.append(str(salary_min))
        else:
            parts.append("?")
        parts.append(" - ")
        if salary_max is not None:
            parts.append(str(salary_max))
        else:
            parts.append("?")
        salary_str = "".join(parts)
    title = (job.get("title") or "").replace("<", "&lt;").replace(">", "&gt;")
    company = (job.get("company") or "").replace("<", "&lt;").replace(">", "&gt;")
    location = (job.get("location") or "").replace("<", "&lt;").replace(">", "&gt;")
    url = job.get("url") or ""
    source = (job.get("source") or "").replace("<", "&lt;").replace(">", "&gt;")
    text = (
        "🎯 <b>100% Match Found!</b>\n\n"
        f"💼 {title}\n"
        f"🏢 {company}\n"
        f"📍 {location}\n"
        f"💰 {salary_str}\n"
        f"🔗 {url}\n\n"
        f"Source: {source}"
    )
    if _send_message(text):
        if job_id is not None:
            db_mark_notified(job_id, "instant")
        return True
    return False


def send_digest(jobs: list[dict[str, Any]]) -> bool:
    """
    Send the daily digest of jobs (score >= 0.75, not yet in digest).
    Marks each included job as digest_sent. Skips jobs already in digest.

    Args:
        jobs: List of job dicts (each with id, title, company, match_score, url).

    Returns:
        True if the digest message was sent successfully, False otherwise.
    """
    if not jobs:
        logger.info("Digest skipped: no jobs to send")
        return True
    date_str = datetime.now().strftime("%Y-%m-%d")
    lines = [f"📋 <b>Daily Job Digest — {date_str}</b>", f"{len(jobs)} matches above 75%\n"]
    for j in jobs:
        score_pct = (j.get("match_score") or 0) * 100
        title = (j.get("title") or "").replace("<", "&lt;").replace(">", "&gt;")
        company = (j.get("company") or "").replace("<", "&lt;").replace(">", "&gt;")
        url = j.get("url") or ""
        lines.append(f"• {score_pct:.0f}% — {title} at {company}")
        lines.append(f"  {url}")
    text = "\n".join(lines)
    success = _send_message(text)
    if success:
        for j in jobs:
            job_id = j.get("id")
            if job_id is not None:
                db_mark_notified(job_id, "digest")
    return success
