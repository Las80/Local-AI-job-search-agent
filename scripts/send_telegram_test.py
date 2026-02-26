"""
One-off script to send a test message to the configured Telegram chat.
Run from project root: python scripts/send_telegram_test.py
"""

import sys
from pathlib import Path

# Ensure project root is on path when run from anywhere
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import config
from notifications.telegram import _send_message

TEST_MESSAGE = (
    "<b>🧪 Test from Job Search Agent</b>\n\n"
    "If you see this message, Telegram notifications are working correctly."
)


def main():
    if not config.config.get("TELEGRAM_BOT_TOKEN") or not config.config.get("TELEGRAM_CHAT_ID"):
        print("Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env")
        sys.exit(1)
    ok = _send_message(TEST_MESSAGE)
    if ok:
        print("Test message sent. Check your Telegram.")
        sys.exit(0)
    else:
        print("Failed to send message. Check logs or .env credentials.")
        sys.exit(1)


if __name__ == "__main__":
    main()
