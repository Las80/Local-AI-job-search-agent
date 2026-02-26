"""
Job source adapter tests for the Local AI Job Search Agent.
Verifies that Adzuna, Reed, and OpenAI web-search return normalised job dicts
with expected keys. May make real API calls if credentials are set.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv()

# Avoid config validation failure when keys missing (e.g. in CI)
os.environ.setdefault("ADZUNA_APP_ID", "test")
os.environ.setdefault("ADZUNA_API_KEY", "test")
os.environ.setdefault("REED_API_KEY", "test")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test")
os.environ.setdefault("TELEGRAM_CHAT_ID", "test")

REQUIRED_KEYS = ["title", "company", "location", "description", "url", "salary_min", "salary_max", "source"]


def test_adzuna_structure():
    """Adzuna returns list of dicts with required keys (may be empty if API fails)."""
    import sources.adzuna as adzuna
    try:
        jobs = adzuna.fetch_adzuna_jobs()
    except Exception as e:
        print(f"Adzuna fetch: FAIL — {e}")
        return False
    if not isinstance(jobs, list):
        print("Adzuna structure: FAIL — not a list")
        return False
    for j in jobs:
        if not all(k in j for k in REQUIRED_KEYS):
            print("Adzuna structure: FAIL — missing keys in job")
            return False
        if j.get("source") != "adzuna":
            print("Adzuna structure: FAIL — wrong source")
            return False
    print("Adzuna structure: PASS")
    return True


def test_reed_structure():
    """Reed returns list of dicts with required keys."""
    import sources.reed as reed
    try:
        jobs = reed.fetch_reed_jobs()
    except Exception as e:
        print(f"Reed fetch: FAIL — {e}")
        return False
    if not isinstance(jobs, list):
        print("Reed structure: FAIL — not a list")
        return False
    for j in jobs:
        if not all(k in j for k in REQUIRED_KEYS):
            print("Reed structure: FAIL — missing keys")
            return False
        if j.get("source") != "reed":
            print("Reed structure: FAIL — wrong source")
            return False
    print("Reed structure: PASS")
    return True


def test_openai_web_search_structure():
    """OpenAI web-search returns list of dicts when key set; empty when not."""
    import sources.openai_web_search as openai_src
    try:
        jobs = openai_src.fetch_openai_web_search_jobs()
    except Exception as e:
        print(f"OpenAI web-search fetch: FAIL — {e}")
        return False
    if not isinstance(jobs, list):
        print("OpenAI web-search structure: FAIL — not a list")
        return False
    for j in jobs:
        if not all(k in j for k in REQUIRED_KEYS):
            print("OpenAI web-search structure: FAIL — missing keys")
            return False
        if j.get("source") != "openai_web_search":
            print("OpenAI web-search structure: FAIL — wrong source")
            return False
    print("OpenAI web-search structure: PASS")
    return True


def main():
    results = [
        test_adzuna_structure(),
        test_reed_structure(),
        test_openai_web_search_structure(),
    ]
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
