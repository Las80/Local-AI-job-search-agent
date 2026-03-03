"""
Send a test Telegram message and print the submission history log.
Run from project root: python scripts/telegram_test_and_log.py

Submission history is appended to logs/telegram_submissions.log (and to this output).
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import config
from notifications.telegram import _send_message

# Path to submission log (same as in telegram.py)
SUBMISSIONS_LOG = PROJECT_ROOT / "logs" / "telegram_submissions.log"

TEST_MESSAGE = (
    "<b>🧪 Test from Job Search Agent</b>\n\n"
    "If you see this message, Telegram notifications are working correctly."
)


def main():
    if not config.config.get("TELEGRAM_BOT_TOKEN") or not config.config.get("TELEGRAM_CHAT_ID"):
        print("Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env")
        sys.exit(1)

    print("Sending test message to Telegram...")
    ok = _send_message(TEST_MESSAGE, "test")
    if ok:
        print("Test message sent. Check your Telegram.")
    else:
        print("Failed to send message. See submission log below for details.")

    # Print submission history
    print("\n--- Submission history (logs/telegram_submissions.log) ---")
    if SUBMISSIONS_LOG.exists():
        lines = SUBMISSIONS_LOG.read_text(encoding="utf-8").strip()
        print(lines if lines else "(no entries yet)")
    else:
        print("(log file not created yet)")
    print("---")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
