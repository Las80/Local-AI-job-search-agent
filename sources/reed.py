"""
Reed.co.uk API client for the Local AI Job Search Agent.
Fetches UK job listings via HTTP Basic Auth, searches multiple keywords,
and returns normalised job dicts. Implements rate limiting between searches.
"""

import logging
import time
from typing import Any

import requests

import config

# Reed API search endpoint
REED_BASE_URL = "https://www.reed.co.uk/api/1.0/search"
# Results to take per keyword request
RESULTS_TO_TAKE = 100
# Delay in seconds between keyword requests
RATE_LIMIT_DELAY_SECONDS = 1
# HTTP request timeout
REQUEST_TIMEOUT_SECONDS = 10

SEARCH_KEYWORDS = [
    "AI automation",
    "LLM",
    "prompt engineer",
    "AI integration",
    "machine learning junior",
    "AI developer",
]

logger = logging.getLogger(__name__)


def fetch_reed_jobs() -> list[dict[str, Any]]:
    """
    Fetch jobs from Reed API for each keyword using HTTP Basic Auth
    (API key as username, empty password). Merges and deduplicates by URL.

    Returns:
        List of normalised job dicts; empty list on error.
    """
    api_key = config.config["REED_API_KEY"]
    all_jobs: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for i, keyword in enumerate(SEARCH_KEYWORDS):
        if i > 0:
            time.sleep(RATE_LIMIT_DELAY_SECONDS)
        try:
            params = {"keywords": keyword, "resultsToTake": RESULTS_TO_TAKE}
            resp = requests.get(
                REED_BASE_URL,
                params=params,
                auth=(api_key, ""),
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.warning("Reed API request failed for keyword '%s': %s", keyword, e)
            continue
        except (ValueError, KeyError) as e:
            logger.warning("Reed response parse error for keyword '%s': %s", keyword, e)
            continue

        results = data.get("results") or []
        for item in results:
            job = _parse_reed_item(item)
            if job and job.get("url") and job["url"] not in seen_urls:
                seen_urls.add(job["url"])
                all_jobs.append(job)
    logger.info("Reed returned %d unique jobs", len(all_jobs))
    return all_jobs


def _parse_reed_item(item: dict) -> dict[str, Any] | None:
    """
    Convert a single Reed API result into the normalised job dict.
    Reed returns jobId; we build the public job URL.

    Args:
        item: Raw result from Reed API.

    Returns:
        Normalised job dict or None if required fields missing.
    """
    try:
        job_id = item.get("jobId")
        if job_id is None:
            return None
        url = f"https://www.reed.co.uk/jobs/{job_id}"
        title = (item.get("jobTitle") or "").strip() or "Untitled"
        employer = (item.get("employerName") or "").strip()
        location = (item.get("locationName") or "").strip()
        description = (item.get("jobDescription") or "").strip()

        salary_min = item.get("minimumSalary")
        salary_max = item.get("maximumSalary")
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
            "title": title,
            "company": employer,
            "location": location,
            "description": description,
            "url": url,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "source": "reed",
        }
    except (AttributeError, TypeError) as e:
        logger.debug("Skip Reed item (parse error): %s", e)
        return None
