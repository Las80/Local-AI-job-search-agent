"""
Adzuna API client for the Local AI Job Search Agent.
Fetches UK job listings for multiple keywords, merges results, and returns
normalised job dicts. Implements rate limiting between keyword searches.
"""

import logging
import time
from typing import Any

import requests

import config

# Base URL for Adzuna UK jobs API (page number appended as last path segment)
ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs/gb/search"
# Results per page (max allowed by API)
RESULTS_PER_PAGE = 50
# Delay in seconds between keyword requests to respect rate limits
RATE_LIMIT_DELAY_SECONDS = 1
# HTTP request timeout
REQUEST_TIMEOUT_SECONDS = 10

# Keywords to search in separate calls; results are merged
SEARCH_KEYWORDS = [
    "AI automation",
    "LLM engineer",
    "prompt engineer",
    "AI integration",
    "machine learning engineer junior",
    "AI developer junior",
]

logger = logging.getLogger(__name__)


def fetch_adzuna_jobs() -> list[dict[str, Any]]:
    """
    Fetch jobs from Adzuna UK API for each configured keyword and merge results.
    Each result is normalised to a dict with keys: title, company, location,
    description, url, salary_min, salary_max, source.

    Returns:
        List of job dicts; empty list on API or network error.
    """
    app_id = config.config["ADZUNA_APP_ID"]
    api_key = config.config["ADZUNA_API_KEY"]
    all_jobs: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for i, keyword in enumerate(SEARCH_KEYWORDS):
        if i > 0:
            time.sleep(RATE_LIMIT_DELAY_SECONDS)
        try:
            url = f"{ADZUNA_BASE_URL}/1"
            params = {
                "app_id": app_id,
                "app_key": api_key,
                "what": keyword,
                "results_per_page": RESULTS_PER_PAGE,
            }
            resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.warning("Adzuna API request failed for keyword '%s': %s", keyword, e)
            continue
        except (ValueError, KeyError) as e:
            logger.warning("Adzuna response parse error for keyword '%s': %s", keyword, e)
            continue

        results = data.get("results") or []
        for item in results:
            job = _parse_adzuna_item(item)
            if job and job.get("url") and job["url"] not in seen_urls:
                seen_urls.add(job["url"])
                all_jobs.append(job)
    logger.info("Adzuna returned %d unique jobs", len(all_jobs))
    return all_jobs


def _parse_adzuna_item(item: dict) -> dict[str, Any] | None:
    """
    Convert a single Adzuna API result into the normalised job dict.
    Handles missing fields with None defaults.

    Args:
        item: Raw result object from Adzuna API.

    Returns:
        Normalised job dict or None if required fields are missing.
    """
    try:
        # Adzuna uses 'redirect_url' or 'url' for the job link
        url = item.get("redirect_url") or item.get("url")
        if not url:
            return None
        title = (item.get("title") or "").strip() or None
        company = (item.get("company", {}).get("display_name") if isinstance(item.get("company"), dict) else item.get("company")) or ""
        location = (item.get("location", {}).get("display_name") if isinstance(item.get("location"), dict) else item.get("location")) or ""
        description = (item.get("description") or "").strip() or ""

        salary_min = item.get("salary_min")
        salary_max = item.get("salary_max")
        if salary_min is not None and not isinstance(salary_min, int):
            try:
                salary_min = int(salary_min)
            except (TypeError, ValueError):
                salary_min = None
        if salary_max is not None and not isinstance(salary_max, int):
            try:
                salary_max = int(salary_max)
            except (TypeError, ValueError):
                salary_max = None

        return {
            "title": title or "Untitled",
            "company": company,
            "location": location,
            "description": description,
            "url": url.strip(),
            "salary_min": salary_min,
            "salary_max": salary_max,
            "source": "adzuna",
        }
    except (AttributeError, TypeError) as e:
        logger.debug("Skip Adzuna item (parse error): %s", e)
        return None
