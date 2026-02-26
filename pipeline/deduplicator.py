"""
Deduplication for the Local AI Job Search Agent.
Uses a SHA256 hash of the job URL as the unique key. Removes duplicates
within a batch and filters out jobs already stored in the database.
"""

import hashlib
import logging
from typing import Any

from database import db

logger = logging.getLogger(__name__)


def generate_hash(job: dict[str, Any]) -> str:
    """
    Generate a unique hash for the job from its URL (normalised and stripped).
    Used as the primary deduplication key in the database.

    Args:
        job: Job dict with a 'url' key.

    Returns:
        SHA256 hex digest of the URL string.
    """
    url = (job.get("url") or "").strip()
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def is_duplicate(job: dict[str, Any]) -> bool:
    """
    Check whether this job already exists in the database by hash.

    Args:
        job: Job dict (must have url; hash is computed if not present).

    Returns:
        True if job exists in DB, False otherwise.
    """
    hash_value = job.get("hash") or generate_hash(job)
    return db.job_exists(hash_value)


def deduplicate_batch(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Remove duplicates within the batch (by URL) and exclude jobs already
    in the database. Each returned job will have a 'hash' key set.

    Args:
        jobs: List of job dicts (normalised, with url).

    Returns:
        List of unique, new jobs (not in DB), each with 'hash' set.
    """
    seen_hashes: set[str] = set()
    result: list[dict[str, Any]] = []

    for job in jobs:
        url = (job.get("url") or "").strip()
        if not url:
            continue
        h = generate_hash(job)
        # Skip duplicate within batch
        if h in seen_hashes:
            continue
        seen_hashes.add(h)
        # Skip if already in database
        if db.job_exists(h):
            continue
        job_with_hash = dict(job)
        job_with_hash["hash"] = h
        result.append(job_with_hash)

    logger.info("Deduplicated batch: %d in, %d new unique", len(jobs), len(result))
    return result
