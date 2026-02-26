"""
Hard filter for the Local AI Job Search Agent.
Applies candidate-specific rules: blacklist, salary floor, location, keywords,
and seniority. A job must pass all rules to be included.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Salary floor in GBP (candidate requirement)
SALARY_FLOOR_GBP = 30000

# Non-UK country names that cause rejection when present in location
NON_UK_COUNTRIES = [
    "germany", "france", "united states", "usa", "australia", "canada",
    "ireland", "netherlands", "spain", "italy", "india", "singapore",
]

# At least one of these must appear in title or description (case-insensitive)
REQUIRED_KEYWORDS = [
    "ai", "artificial intelligence", "llm", "machine learning", "ml",
    "automation", "python", "prompt", "nlp", "gpt", "langchain",
    "openai", "sap", "integration", "workflow",
]

# Reject if title contains any of these (unless also junior/associate)
SENIORITY_REJECT_WORDS = [
    "senior", "lead", "principal", "head of", "director", "vp ",
    "vice president", "manager", "staff engineer", "architect",
]
# If title contains any of these, do NOT reject for seniority
JUNIOR_ASSOCIATE_WORDS = ["junior", "associate"]


def passes_hard_filter(job: dict[str, Any], blacklist: list[str]) -> bool:
    """
    Apply all hard filters. Job must pass every rule.

    Args:
        job: Normalised job dict (must have normalized_company, normalized_title, etc.).
        blacklist: List of blacklisted company names (normalized, lowercased).

    Returns:
        True if job passes all filters, False otherwise.
    """
    # 1. Blacklist: company not in blacklist (case-insensitive via normalized_company)
    norm_company = (job.get("normalized_company") or "").strip()
    blacklist_normalized = [c.strip().lower() for c in blacklist if c]
    for bl in blacklist_normalized:
        bl_clean = "".join(c for c in bl if c.isalnum() or c.isspace()).strip()
        if bl_clean and (bl_clean in norm_company or norm_company in bl_clean):
            logger.debug("Rejected (blacklist): company=%s", job.get("company"))
            return False

    # 2. Salary: if salary_min present, must be >= SALARY_FLOOR_GBP
    salary_min = job.get("salary_min")
    if salary_min is not None:
        try:
            val = int(salary_min)
            if val < SALARY_FLOOR_GBP:
                logger.debug("Rejected (salary): salary_min=%s", salary_min)
                return False
        except (TypeError, ValueError):
            pass

    # 3. Location: reject only if explicitly non-UK
    location = (job.get("location") or "").lower()
    for country in NON_UK_COUNTRIES:
        if country in location:
            logger.debug("Rejected (location): location=%s", job.get("location"))
            return False

    # 4. Keywords: title or description must contain at least one required keyword
    title = (job.get("title") or "").lower()
    desc = (job.get("description") or "").lower()
    combined = f"{title} {desc}"
    if not any(kw in combined for kw in REQUIRED_KEYWORDS):
        logger.debug("Rejected (no AI keywords): title=%s", job.get("title"))
        return False

    # 5. Seniority: reject if title has seniority words but not junior/associate
    title_lower = (job.get("normalized_title") or job.get("title") or "").lower()
    has_junior_associate = any(w in title_lower for w in JUNIOR_ASSOCIATE_WORDS)
    if not has_junior_associate:
        for word in SENIORITY_REJECT_WORDS:
            if word in title_lower:
                logger.debug("Rejected (seniority): title=%s", job.get("title"))
                return False

    return True
