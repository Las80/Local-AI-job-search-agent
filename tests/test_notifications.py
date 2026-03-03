"""
Notification tests for the Local AI Job Search Agent.
Tests Telegram message formatting and digest logic with mocked _send_message
(no real messages sent).
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv()
os.environ.setdefault("ADZUNA_APP_ID", "t")
os.environ.setdefault("ADZUNA_API_KEY", "t")
os.environ.setdefault("REED_API_KEY", "t")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "t")
os.environ.setdefault("TELEGRAM_CHAT_ID", "t")

import notifications.telegram as telegram


def test_send_instant_alert_formats_correctly():
    """send_instant_alert produces message with title, company, location, url, source."""
    with patch.object(telegram, "_send_message", return_value=True), \
         patch.object(telegram, "db_mark_notified"):
        job = {
            "id": 1,
            "title": "AI Engineer",
            "company": "Tech Co",
            "location": "London",
            "url": "https://example.com/job/1",
            "salary_min": 35000,
            "salary_max": 45000,
            "source": "reed",
            "match_score": 1.0,
        }
        ok = telegram.send_instant_alert(job)
        if not ok:
            print("send_instant_alert (format): FAIL — returned False")
            return False
        call_args = telegram._send_message.call_args
        text = call_args[0][0]
        if "Match Found!" not in text or "AI Engineer" not in text or "Tech Co" not in text:
            print("send_instant_alert (format): FAIL — missing content")
            return False
        if "https://example.com/job/1" not in text or "reed" not in text:
            print("send_instant_alert (format): FAIL — missing url/source")
            return False
    print("send_instant_alert (format): PASS")
    return True


def test_send_digest_formats_correctly():
    """send_digest produces message with date, count, and job list."""
    with patch.object(telegram, "_send_message", return_value=True), \
         patch.object(telegram, "db_mark_notified"):
        jobs = [
            {"id": 1, "title": "Job A", "company": "Co A", "match_score": 0.85, "url": "https://a.com"},
            {"id": 2, "title": "Job B", "company": "Co B", "match_score": 0.78, "url": "https://b.com"},
        ]
        ok = telegram.send_digest(jobs)
        if not ok:
            print("send_digest (format): FAIL — returned False")
            return False
        call_args = telegram._send_message.call_args
        text = call_args[0][0]
        if "Daily" not in text or "Digest" not in text or "2" not in text:
            print("send_digest (format): FAIL — missing date/count")
            return False
        if "Job A" not in text or "Job B" not in text:
            print("send_digest (format): FAIL — missing job titles")
            return False
    print("send_digest (format): PASS")
    return True


def test_send_digest_skips_already_sent():
    """send_digest with empty list does not send (or sends empty message)."""
    with patch.object(telegram, "_send_message", return_value=True):
        ok = telegram.send_digest([])
        if not ok:
            print("send_digest (empty): FAIL — expected True for empty")
            return False
    print("send_digest (empty): PASS")
    return True


def main():
    results = [
        test_send_instant_alert_formats_correctly(),
        test_send_digest_formats_correctly(),
        test_send_digest_skips_already_sent(),
    ]
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
