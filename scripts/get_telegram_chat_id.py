"""
Get your Telegram chat_id using the Bot API (official solution for "chat not found").

Telegram returns "chat not found" when the user has never started a chat with the bot.
Bots cannot message you until you open the bot and send /start.

Steps:
  1. Run this script once to see your bot's username.
  2. In Telegram: search for that bot (e.g. t.me/YourBotUsername) and send /start.
  3. Run this script again; it will print the chat_id to put in .env as TELEGRAM_CHAT_ID.

Run from project root: python scripts/get_telegram_chat_id.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import os
import requests

TELEGRAM_API_BASE = "https://api.telegram.org/bot"
TIMEOUT = 10


def main():
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not set in .env")
        sys.exit(1)

    base = f"{TELEGRAM_API_BASE}{token}"

    # 1) Get bot info so user knows which bot to message
    r_me = requests.get(f"{base}/getMe", timeout=TIMEOUT)
    if not r_me.ok:
        print("Could not reach Telegram: check TELEGRAM_BOT_TOKEN.")
        sys.exit(1)
    me = r_me.json()
    if not me.get("ok"):
        print("Invalid bot token:", me.get("description", "unknown"))
        sys.exit(1)
    result = me.get("result", {})
    bot_username = result.get("username") or "unknown"
    bot_name = result.get("first_name") or "Bot"

    # 2) Get recent updates (messages sent to the bot, e.g. /start)
    r_up = requests.get(f"{base}/getUpdates", timeout=TIMEOUT)
    if not r_up.ok:
        print("Could not get updates from Telegram.")
        sys.exit(1)
    data = r_up.json()
    if not data.get("ok"):
        print("getUpdates failed:", data.get("description", "unknown"))
        sys.exit(1)
    updates = data.get("result") or []

    # 3) Extract chat_id from the most recent message
    chat_ids = []
    for u in updates:
        msg = u.get("message") or u.get("edited_message")
        if not msg:
            continue
        chat = msg.get("chat")
        if not chat:
            continue
        cid = chat.get("id")
        if cid is not None and cid not in chat_ids:
            chat_ids.append(cid)

    if chat_ids:
        # Use the most recent chat (last in list)
        chat_id = chat_ids[-1]
        print("Bot:", bot_name, f"(@{bot_username})")
        print("Chat ID(s) that have started this bot:", chat_ids)
        print()
        print("Use this in your .env as TELEGRAM_CHAT_ID:")
        print("  TELEGRAM_CHAT_ID=", chat_id, sep="")
        print()
        print("Then run: python scripts/send_telegram_test.py")
        return

    # No updates: user has not started the bot
    print("Bot:", bot_name, f"(@{bot_username})")
    print()
    print('No chat found. Telegram returns "chat not found" until you start the bot.')
    print()
    print("Do this:")
    print("  1. Open Telegram and go to: https://t.me/" + bot_username)
    print("  2. Tap 'START' or send: /start")
    print("  3. Run this script again: python scripts/get_telegram_chat_id.py")
    print()
    sys.exit(1)


if __name__ == "__main__":
    main()
