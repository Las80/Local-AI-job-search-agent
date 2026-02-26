"""
Configuration loader for the Local AI Job Search Agent.
Loads environment variables from .env, validates required keys, and exports
a single config dict for use across the application. Fails fast on import
if any required variable is missing.
"""

import os
from dotenv import load_dotenv

# Load .env from project root so keys are available to all modules
load_dotenv()

# Keys that must be present in the environment
REQUIRED_KEYS = [
    "ADZUNA_APP_ID",
    "ADZUNA_API_KEY",
    "REED_API_KEY",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
]


def _get_float(key: str, default: float) -> float:
    """Read float from env or return default."""
    val = os.getenv(key)
    if val is None or val.strip() == "":
        return default
    try:
        return float(val)
    except ValueError:
        return default


def _get_int(key: str, default: int) -> int:
    """Read int from env or return default."""
    val = os.getenv(key)
    if val is None or val.strip() == "":
        return default
    try:
        return int(val)
    except ValueError:
        return default


def _get_blacklist() -> list:
    """Parse comma-separated BLACKLISTED_COMPANIES into a list of stripped strings."""
    raw = os.getenv("BLACKLISTED_COMPANIES", "")
    if not raw or not raw.strip():
        return []
    return [c.strip() for c in raw.split(",") if c.strip()]


def _validate_required() -> None:
    """Ensure all REQUIRED_KEYS exist and are non-empty; raise EnvironmentError if not."""
    missing = [k for k in REQUIRED_KEYS if not os.getenv(k) or not str(os.getenv(k)).strip()]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Copy .env.example to .env and set all required keys."
        )


# Validate before building config so the app fails fast
_validate_required()

# Single config dict exported for the rest of the application
config = {
    "ADZUNA_APP_ID": os.getenv("ADZUNA_APP_ID", "").strip(),
    "ADZUNA_API_KEY": os.getenv("ADZUNA_API_KEY", "").strip(),
    "REED_API_KEY": os.getenv("REED_API_KEY", "").strip(),
    "OPENAI_API_KEY": (os.getenv("OPENAI_API_KEY") or "").strip(),
    "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
    "TELEGRAM_CHAT_ID": os.getenv("TELEGRAM_CHAT_ID", "").strip(),
    "MATCH_THRESHOLD": _get_float("MATCH_THRESHOLD", 1.0),
    "DIGEST_THRESHOLD": _get_float("DIGEST_THRESHOLD", 0.75),
    "NOTIFICATION_COOLDOWN_SECONDS": _get_int("NOTIFICATION_COOLDOWN_SECONDS", 3600),
    "DIGEST_TIME": (os.getenv("DIGEST_TIME") or "08:00").strip(),
    "BLACKLISTED_COMPANIES": _get_blacklist(),
}
