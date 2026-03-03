"""
Telegram notification layer for the Local AI Job Search Agent.
Sends instant alerts for matches >= MATCH_THRESHOLD (default 50%) and a daily digest for 50%+ matches
via the Telegram Bot API. Implements cooldown to avoid duplicate alerts.
"""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

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

# Submission history log (project root / logs / telegram_submissions.log)
_SUBMISSIONS_LOG = Path(__file__).resolve().parent.parent / "logs" / "telegram_submissions.log"


def _log_submission(chat_id: str, message_type: str, success: bool, detail: Optional[str] = None) -> None:
    """Append one line to logs/telegram_submissions.log for submission history."""
    try:
        _SUBMISSIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "OK" if success else "FAIL"
        line = f"{ts} | chat_id={chat_id} | type={message_type} | {status}"
        if detail:
            line += f" | {detail}"
        line += "\n"
        with open(_SUBMISSIONS_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        logger.warning("Could not write submission log: %s", e)


def _send_message(text: str, message_type: str = "send") -> bool:
    """
    Send a single message to the configured Telegram chat. Truncates to 4096 chars.
    Does not enforce cooldown; caller must check before sending instant alerts.
    Logs each attempt to logs/telegram_submissions.log for submission history.

    Args:
        text: Message body (HTML or plain). Will be truncated if over limit.
        message_type: Label for submission log (e.g. "test", "instant", "digest").

    Returns:
        True if the API returned success, False otherwise.
    """
    token = config.config["TELEGRAM_BOT_TOKEN"]
    chat_id = str(config.config["TELEGRAM_CHAT_ID"]).strip()
    if not token or not chat_id:
        logger.warning("Telegram not configured; skip send")
        _log_submission(chat_id or "(empty)", message_type, False, "not configured")
        return False
    if len(text) > TELEGRAM_MAX_MESSAGE_LENGTH:
        text = text[: TELEGRAM_MAX_MESSAGE_LENGTH - 3] + "..."
    url = f"{TELEGRAM_API_BASE}{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        resp.raise_for_status()
        _log_submission(chat_id, message_type, True)
        return True
    except requests.RequestException as e:
        detail = str(e)
        try:
            if hasattr(e, "response") and e.response is not None:
                body = e.response.text
                if body:
                    detail = f"{e.response.status_code} {body}"
        except Exception:
            pass
        logger.error("Telegram send failed: %s", e)
        _log_submission(chat_id, message_type, False, detail)
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
    Send an instant Telegram alert when match score >= MATCH_THRESHOLD. Respects cooldown per job_id.
    Message includes score, title, company, location, salary, url, source.

    Args:
        job: Job dict with id, title, company, location, url, salary_min, salary_max, source, match_score.

    Returns:
        True if message was sent successfully, False otherwise.
    """
    job_id = job.get("id")
    if job_id is not None and _recently_notified(job_id):
        logger.debug("Skip instant alert for job_id=%s (cooldown)", job_id)
        return False
    score_pct = int((job.get("match_score") or 0) * 100)
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
        f"🎯 <b>{score_pct}% Match Found!</b>\n\n"
        f"💼 {title}\n"
        f"🏢 {company}\n"
        f"📍 {location}\n"
        f"💰 {salary_str}\n"
        f"🔗 {url}\n\n"
        f"Source: {source}"
    )
    if _send_message(text, "instant"):
        if job_id is not None:
            db_mark_notified(job_id, "instant")
        return True
    return False


def send_digest(jobs: list[dict[str, Any]]) -> bool:
    """
    Send the daily digest of jobs (score >= configured DIGEST_THRESHOLD, not yet in digest).
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
    threshold_pct = int(config.config.get("DIGEST_THRESHOLD", 0.5) * 100)
    lines = [
        f"📋 <b>Daily Job Digest — {date_str}</b>",
        f"{len(jobs)} matches at or above {threshold_pct}%\n",
    ]
    for j in jobs:
        score_pct = (j.get("match_score") or 0) * 100
        title = (j.get("title") or "").replace("<", "&lt;").replace(">", "&gt;")
        company = (j.get("company") or "").replace("<", "&lt;").replace(">", "&gt;")
        url = j.get("url") or ""
        lines.append(f"• {score_pct:.0f}% — {title} at {company}")
        lines.append(f"  {url}")
    text = "\n".join(lines)
    success = _send_message(text, "digest")
    if success:
        for j in jobs:
            job_id = j.get("id")
            if job_id is not None:
                db_mark_notified(job_id, "digest")
    return success
