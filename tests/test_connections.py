"""
Connection tests for the Local AI Job Search Agent (Slice 0).
Verifies that Adzuna, Reed, and Telegram are reachable and credentials work.
Exits with code 1 if any required connection fails.
"""

import os
import sys

# Allow importing from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load env before config so .env is present
from dotenv import load_dotenv
load_dotenv()

def test_adzuna():
    """Test Adzuna API connectivity and credentials."""
    import requests
    app_id = os.getenv("ADZUNA_APP_ID")
    api_key = os.getenv("ADZUNA_API_KEY")
    if not app_id or not api_key:
        print("Adzuna: FAIL (missing ADZUNA_APP_ID or ADZUNA_API_KEY)")
        return False
    url = "https://api.adzuna.com/v1/api/jobs/gb/search/1"
    try:
        r = requests.get(url, params={"app_id": app_id, "app_key": api_key, "what": "python", "results_per_page": 1}, timeout=10)
        r.raise_for_status()
        print("Adzuna: PASS")
        return True
    except Exception as e:
        print(f"Adzuna: FAIL — {e}")
        return False


def test_reed():
    """Test Reed API connectivity and credentials."""
    import requests
    api_key = os.getenv("REED_API_KEY")
    if not api_key:
        print("Reed: FAIL (missing REED_API_KEY)")
        return False
    try:
        r = requests.get(
            "https://www.reed.co.uk/api/1.0/search",
            params={"keywords": "python", "resultsToTake": 1},
            auth=(api_key, ""),
            timeout=10,
        )
        r.raise_for_status()
        print("Reed: PASS")
        return True
    except Exception as e:
        print(f"Reed: FAIL — {e}")
        return False


def test_telegram():
    """Test Telegram Bot API connectivity and credentials."""
    import requests
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Telegram: FAIL (missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID)")
        return False
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{token}/getMe",
            timeout=10,
        )
        r.raise_for_status()
        print("Telegram: PASS")
        return True
    except Exception as e:
        print(f"Telegram: FAIL — {e}")
        return False


def main():
    """Run all connection tests. Exit 1 if any required test fails."""
    a = test_adzuna()
    r = test_reed()
    t = test_telegram()
    required_ok = a and r and t
    if not required_ok:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
