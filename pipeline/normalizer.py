"""
Job normalisation for the Local AI Job Search Agent.
Cleans and normalises title, company, location, and description so that
filtering and scoring work on consistent, comparable values.
"""

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Regex to strip HTML tags from description
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
# Regex to strip non-alphanumeric for normalized_company (keep spaces for comparison)
_SPECIAL_CHARS_PATTERN = re.compile(r"[^\w\s]", re.UNICODE)


def normalize_job(job: dict[str, Any]) -> dict[str, Any]:
    """
    Normalise a job dict: lowercase and strip text fields, remove HTML from
    description, and add normalized_company and normalized_title for comparison.

    Args:
        job: Raw job dict with title, company, location, description.

    Returns:
        New dict with same keys plus normalized_company and normalized_title.
    """
    result = dict(job)

    # Lowercase and strip string fields; default to empty string if missing
    for key in ("title", "company", "location", "description"):
        val = result.get(key)
        if val is None:
            result[key] = ""
        elif isinstance(val, str):
            result[key] = val.strip().lower()
        else:
            result[key] = str(val).strip().lower()

    desc = result.get("description") or ""
    # Remove HTML tags from description
    result["description"] = _HTML_TAG_PATTERN.sub(" ", desc)
    # Collapse multiple spaces
    result["description"] = " ".join(result["description"].split())

    company_raw = result.get("company") or ""
    # Strip special characters for blacklist/comparison (keep letters, numbers, spaces)
    normalized_company = _SPECIAL_CHARS_PATTERN.sub("", company_raw)
    result["normalized_company"] = " ".join(normalized_company.split()).strip()

    title_raw = result.get("title") or ""
    result["normalized_title"] = title_raw.strip()

    return result
