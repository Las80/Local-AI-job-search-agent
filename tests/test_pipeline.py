"""
Pipeline tests for the Local AI Job Search Agent.
Tests normalizer, hard_filter, scorer, and deduplicator with hardcoded sample jobs.
No API or database calls (except deduplicate_batch which uses DB; we mock or use test DB).
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv()
os.environ.setdefault("ADZUNA_APP_ID", "t")
os.environ.setdefault("ADZUNA_API_KEY", "t")
os.environ.setdefault("REED_API_KEY", "t")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "t")
os.environ.setdefault("TELEGRAM_CHAT_ID", "t")

from pipeline.normalizer import normalize_job
from pipeline.hard_filter import passes_hard_filter
from pipeline.scorer import score_job
from pipeline.deduplicator import generate_hash, deduplicate_batch


def test_normalize_cleans_html_and_lowercases():
    """normalize_job strips HTML and lowercases text fields."""
    job = {
        "title": "  AI Engineer  ",
        "company": "Test Co",
        "location": "London",
        "description": "<p>We use <b>Python</b> and ML.</p>",
    }
    out = normalize_job(job)
    if "normalized_company" not in out or "normalized_title" not in out:
        print("normalize_job (fields): FAIL")
        return False
    if "<" in (out.get("description") or ""):
        print("normalize_job (HTML): FAIL")
        return False
    if (out.get("title") or "").strip() != "ai engineer" or (out.get("company") or "").strip() != "test co":
        print("normalize_job (lowercase): FAIL")
        return False
    print("normalize_job (HTML, lowercase): PASS")
    return True


def test_hard_filter_rejects_senior():
    """passes_hard_filter rejects senior/lead titles (unless junior/associate)."""
    job = {
        "title": "Senior AI Engineer",
        "normalized_title": "senior ai engineer",
        "company": "Co",
        "normalized_company": "co",
        "location": "UK",
        "description": "We do AI and Python.",
        "salary_min": 50000,
    }
    if passes_hard_filter(job, []):
        print("passes_hard_filter (reject senior): FAIL")
        return False
    job["title"] = "Junior AI Engineer"
    job["normalized_title"] = "junior ai engineer"
    if not passes_hard_filter(job, []):
        print("passes_hard_filter (accept junior): FAIL")
        return False
    print("passes_hard_filter (seniority): PASS")
    return True


def test_hard_filter_rejects_blacklist():
    """passes_hard_filter rejects blacklisted companies."""
    job = {
        "title": "AI Developer",
        "normalized_title": "ai developer",
        "company": "Bad Corp",
        "normalized_company": "bad corp",
        "location": "UK",
        "description": "Python and AI.",
        "salary_min": 35000,
    }
    if passes_hard_filter(job, ["bad corp"]):
        print("passes_hard_filter (blacklist): FAIL")
        return False
    if not passes_hard_filter(job, []):
        print("passes_hard_filter (no blacklist): FAIL")
        return False
    print("passes_hard_filter (blacklist): PASS")
    return True


def test_hard_filter_rejects_no_keywords():
    """passes_hard_filter rejects jobs with no AI-related keywords."""
    job = {
        "title": "Office Administrator",
        "normalized_title": "office administrator",
        "company": "Co",
        "normalized_company": "co",
        "location": "UK",
        "description": "Filing and phones.",
        "salary_min": 25000,
    }
    if passes_hard_filter(job, []):
        print("passes_hard_filter (no keywords): FAIL")
        return False
    print("passes_hard_filter (no keywords): PASS")
    return True


def test_hard_filter_accepts_valid_junior():
    """passes_hard_filter accepts a valid junior AI role."""
    job = {
        "title": "Junior AI Automation Specialist",
        "normalized_title": "junior ai automation specialist",
        "company": "Good Co",
        "normalized_company": "good co",
        "location": "Remote UK",
        "description": "Python, LLM, automation and workflow.",
        "salary_min": 32000,
    }
    if not passes_hard_filter(job, []):
        print("passes_hard_filter (valid junior): FAIL")
        return False
    print("passes_hard_filter (valid junior): PASS")
    return True


def test_score_job_range():
    """score_job returns float in [0, 1]."""
    job = {
        "title": "AI Engineer",
        "description": "Python, machine learning, automation, integration, workflow.",
    }
    s = score_job(job)
    if not isinstance(s, float) or s < 0.0 or s > 1.0:
        print("score_job (range): FAIL")
        return False
    print("score_job (range): PASS")
    return True


def test_generate_hash_consistent():
    """generate_hash returns same hash for same URL."""
    job = {"url": "https://example.com/job/1"}
    h1 = generate_hash(job)
    h2 = generate_hash(job)
    if h1 != h2 or len(h1) != 64:
        print("generate_hash (consistent): FAIL")
        return False
    print("generate_hash (consistent): PASS")
    return True


def test_deduplicate_batch_removes_duplicate_urls():
    """deduplicate_batch removes duplicate URLs within the batch."""
    # Use a fresh test DB so nothing exists yet
    import database.db as db_module
    test_db = Path(__file__).resolve().parent.parent / "test_pipeline.db"
    orig = db_module._DB_PATH
    db_module._DB_PATH = test_db
    if test_db.exists():
        test_db.unlink()
    try:
        jobs = [
            {"url": "https://example.com/a", "title": "A", "company": "C", "location": "", "description": ""},
            {"url": "https://example.com/a", "title": "A2", "company": "C", "location": "", "description": ""},
            {"url": "https://example.com/b", "title": "B", "company": "C", "location": "", "description": ""},
        ]
        out = deduplicate_batch(jobs)
        if len(out) != 2:
            print("deduplicate_batch (within batch): FAIL — expected 2, got %s" % len(out))
            return False
        urls = [j["url"] for j in out]
        if len(set(urls)) != 2:
            print("deduplicate_batch (within batch): FAIL — duplicate URL in result")
            return False
        print("deduplicate_batch (within batch): PASS")
        return True
    finally:
        db_module._DB_PATH = orig
        if test_db.exists():
            try:
                test_db.unlink()
            except OSError:
                pass


def main():
    results = [
        test_normalize_cleans_html_and_lowercases(),
        test_hard_filter_rejects_senior(),
        test_hard_filter_rejects_blacklist(),
        test_hard_filter_rejects_no_keywords(),
        test_hard_filter_accepts_valid_junior(),
        test_score_job_range(),
        test_generate_hash_consistent(),
        test_deduplicate_batch_removes_duplicate_urls(),
    ]
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
