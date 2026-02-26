"""
Database layer tests for the Local AI Job Search Agent.
Uses a temporary test database (test.db in project root for tests) and cleans up after.
All DB functions are tested in isolation. Uses print for PASS/FAIL as specified.
"""

import os
import sys
from pathlib import Path

# Project root on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load env so config is valid
from dotenv import load_dotenv
load_dotenv()

# Point db at test database
import database.db as db_module
TEST_DB = Path(__file__).resolve().parent.parent / "test.db"
_original_path = db_module._DB_PATH
db_module._DB_PATH = TEST_DB


def cleanup():
    """Remove test database file if it exists."""
    if TEST_DB.exists():
        try:
            TEST_DB.unlink()
        except OSError:
            pass


def test_insert_and_exists():
    """Test insert_job and job_exists."""
    cleanup()
    job = {
        "title": "Test Job",
        "company": "Test Co",
        "location": "London",
        "description": "Test desc",
        "url": "https://example.com/job/1",
        "salary_min": 35000,
        "salary_max": 45000,
        "source": "test",
        "match_score": 0.9,
        "hash": "a" * 64,
    }
    ok = db_module.insert_job(job)
    if not ok:
        print("insert_job (first): FAIL")
        return False
    if not db_module.job_exists(job["hash"]):
        print("job_exists (after insert): FAIL")
        return False
    ok2 = db_module.insert_job(job)
    if ok2:
        print("insert_job (duplicate): FAIL — should have failed")
        return False
    print("insert_job, job_exists: PASS")
    return True


def test_get_unnotified_matches():
    """Test get_unnotified_matches returns jobs above threshold with notified=0."""
    cleanup()  # fresh DB so we only have the one job we insert
    job = {
        "title": "Match Job",
        "company": "Match Co",
        "location": "UK",
        "description": "AI role",
        "url": "https://example.com/job/2",
        "salary_min": 40000,
        "salary_max": 50000,
        "source": "test",
        "match_score": 1.0,
        "hash": "b" * 64,
    }
    db_module.insert_job(job)
    matches = db_module.get_unnotified_matches(0.75)
    if len(matches) != 1 or matches[0]["match_score"] < 0.75:
        print("get_unnotified_matches: FAIL")
        return False
    print("get_unnotified_matches: PASS")
    return True


def test_mark_notified():
    """Test mark_notified updates notifications and job flags."""
    cleanup()
    job = {
        "title": "Notify Job",
        "company": "Notify Co",
        "location": "Remote",
        "description": "Python",
        "url": "https://example.com/job/3",
        "salary_min": 30000,
        "salary_max": 40000,
        "source": "test",
        "match_score": 0.8,
        "hash": "c" * 64,
    }
    db_module.insert_job(job)
    with db_module.get_connection() as conn:
        cur = conn.execute("SELECT id FROM jobs WHERE hash = ?", (job["hash"],))
        row = cur.fetchone()
    if not row:
        print("mark_notified (setup): FAIL")
        return False
    job_id = row[0]
    db_module.mark_notified(job_id, "instant")
    matches = db_module.get_unnotified_matches(0.5)
    if any(m["id"] == job_id for m in matches):
        print("mark_notified: FAIL — job still in unnotified")
        return False
    print("mark_notified: PASS")
    return True


def test_blacklist():
    """Test get_blacklist, add_to_blacklist, remove_from_blacklist."""
    cleanup()  # fresh DB for blacklist tests
    bl = db_module.get_blacklist()
    if bl:
        print("get_blacklist (initial): FAIL — expected empty")
        return False
    added = db_module.add_to_blacklist("Bad Corp")
    if not added:
        print("add_to_blacklist: FAIL")
        return False
    added2 = db_module.add_to_blacklist("Bad Corp")
    if added2:
        print("add_to_blacklist (duplicate): FAIL")
        return False
    bl = db_module.get_blacklist()
    if "Bad Corp" not in bl:
        print("get_blacklist (after add): FAIL")
        return False
    removed = db_module.remove_from_blacklist("Bad Corp")
    if not removed:
        print("remove_from_blacklist: FAIL")
        return False
    bl = db_module.get_blacklist()
    if bl:
        print("get_blacklist (after remove): FAIL")
        return False
    print("get_blacklist, add_to_blacklist, remove_from_blacklist: PASS")
    return True


def test_get_all_jobs():
    """Test get_all_jobs returns jobs sorted by match_score."""
    cleanup()  # fresh DB for get_all_jobs
    for i in range(3):
        db_module.insert_job({
            "title": f"Job {i}",
            "company": "Co",
            "location": "",
            "description": "",
            "url": f"https://example.com/job/{i}",
            "salary_min": None,
            "salary_max": None,
            "source": "test",
            "match_score": 0.5 + i * 0.2,
            "hash": str(i) * 64,
        })
    jobs = db_module.get_all_jobs(limit=10)
    if len(jobs) != 3:
        print("get_all_jobs (count): FAIL")
        return False
    scores = [j["match_score"] for j in jobs]
    if scores != sorted(scores, reverse=True):
        print("get_all_jobs (order): FAIL")
        return False
    print("get_all_jobs: PASS")
    return True


def main():
    """Run all DB tests and cleanup."""
    db_module._DB_PATH = TEST_DB
    results = [
        test_insert_and_exists(),
        test_get_unnotified_matches(),
        test_mark_notified(),
        test_blacklist(),
        test_get_all_jobs(),
    ]
    cleanup()
    db_module._DB_PATH = _original_path
    if not all(results):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
