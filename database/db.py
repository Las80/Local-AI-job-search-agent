"""
SQLite database layer for the Local AI Job Search Agent.
Provides a context manager for connections, schema creation, and all CRUD
operations for jobs, notifications, and blacklist. Uses parameterised queries
only and never logs secrets.
"""

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path

# Resolve project root (parent of this package) so jobs.db lives in project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DB_PATH = _PROJECT_ROOT / "jobs.db"

# Default request timeout for SQLite operations (seconds)
_DB_TIMEOUT_SECONDS = 10

logger = logging.getLogger(__name__)


@contextmanager
def get_connection(db_path: Path | None = None):
    """
    Context manager that yields a SQLite connection to jobs.db.
    Creates the database file and schema if they do not exist.
    Ensures connection is closed on exit.

    Args:
        db_path: Optional path to database file; defaults to project root jobs.db.

    Yields:
        sqlite3.Connection: Open connection for the duration of the context.
    """
    path = db_path or _DB_PATH
    conn = None
    try:
        conn = sqlite3.connect(str(path), timeout=_DB_TIMEOUT_SECONDS)
        conn.row_factory = sqlite3.Row
        init_schema(conn)
        yield conn
        conn.commit()
    except sqlite3.Error as e:
        logger.error("Database error in get_connection: %s", e)
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def init_schema(conn: sqlite3.Connection) -> None:
    """
    Create jobs, notifications, and blacklist tables if they do not exist.
    Safe to call on every connection; uses IF NOT EXISTS.

    Args:
        conn: An open SQLite connection.
    """
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT,
                description TEXT,
                url TEXT UNIQUE NOT NULL,
                salary_min INTEGER,
                salary_max INTEGER,
                source TEXT,
                match_score REAL,
                hash TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notified INTEGER DEFAULT 0,
                digest_sent INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER REFERENCES jobs(id),
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notification_type TEXT
            );
            CREATE TABLE IF NOT EXISTS blacklist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT UNIQUE NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
    except sqlite3.Error as e:
        logger.error("init_schema failed: %s", e)
        raise


def insert_job(job: dict) -> bool:
    """
    Insert a single job into the jobs table. Uses parameterised query.

    Args:
        job: Dict with keys title, company, location, description, url,
             salary_min, salary_max, source, match_score, hash.

    Returns:
        True if insert succeeded, False if duplicate (UNIQUE constraint on url/hash).
    """
    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO jobs (
                    title, company, location, description, url,
                    salary_min, salary_max, source, match_score, hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.get("title"),
                    job.get("company"),
                    job.get("location"),
                    job.get("description"),
                    job.get("url"),
                    job.get("salary_min"),
                    job.get("salary_max"),
                    job.get("source"),
                    job.get("match_score"),
                    job.get("hash"),
                ),
            )
        return True
    except sqlite3.IntegrityError:
        logger.debug("Insert skipped (duplicate url/hash): %s", job.get("url"))
        return False
    except sqlite3.Error as e:
        logger.error("insert_job failed: %s", e)
        raise


def job_exists(hash_value: str) -> bool:
    """
    Check whether a job with the given hash already exists in the database.

    Args:
        hash_value: The unique hash (e.g. SHA256 of URL) of the job.

    Returns:
        True if a row with this hash exists, False otherwise.
    """
    try:
        with get_connection() as conn:
            cur = conn.execute("SELECT 1 FROM jobs WHERE hash = ? LIMIT 1", (hash_value,))
            return cur.fetchone() is not None
    except sqlite3.Error as e:
        logger.error("job_exists failed: %s", e)
        raise


def get_unnotified_matches(threshold: float) -> list:
    """
    Return jobs with match_score >= threshold that have not yet been
    notified (notified = 0). Used for instant alerts and digest.

    Args:
        threshold: Minimum match_score (e.g. 1.0 for instant, 0.75 for digest).

    Returns:
        List of dicts with job fields including id, for each matching job.
    """
    try:
        with get_connection() as conn:
            cur = conn.execute(
                """
                SELECT id, title, company, location, description, url,
                       salary_min, salary_max, source, match_score, hash,
                       created_at, notified, digest_sent
                FROM jobs
                WHERE match_score >= ? AND notified = 0
                ORDER BY match_score DESC
                """,
                (threshold,),
            )
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logger.error("get_unnotified_matches failed: %s", e)
        raise


def mark_notified(job_id: int, notification_type: str) -> None:
    """
    Record that a notification was sent for this job and set notified/digest_sent flags.

    Args:
        job_id: Primary key of the job in the jobs table.
        notification_type: One of 'instant' or 'digest'.
    """
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO notifications (job_id, notification_type) VALUES (?, ?)",
                (job_id, notification_type),
            )
            if notification_type == "instant":
                conn.execute("UPDATE jobs SET notified = 1 WHERE id = ?", (job_id,))
            elif notification_type == "digest":
                conn.execute("UPDATE jobs SET digest_sent = 1 WHERE id = ?", (job_id,))
    except sqlite3.Error as e:
        logger.error("mark_notified failed: %s", e)
        raise


def get_blacklist() -> list:
    """
    Return the list of blacklisted company names (normalized for comparison).

    Returns:
        List of company strings from the blacklist table.
    """
    try:
        with get_connection() as conn:
            cur = conn.execute("SELECT company FROM blacklist ORDER BY company")
            return [row[0] for row in cur.fetchall()]
    except sqlite3.Error as e:
        logger.error("get_blacklist failed: %s", e)
        raise


def add_to_blacklist(company: str) -> bool:
    """
    Add a company to the blacklist. Ignores duplicates (UNIQUE constraint).

    Args:
        company: Company name to blacklist.

    Returns:
        True if added, False if already present.
    """
    try:
        with get_connection() as conn:
            conn.execute("INSERT INTO blacklist (company) VALUES (?)", (company.strip(),))
        return True
    except sqlite3.IntegrityError:
        logger.debug("Blacklist add skipped (already exists): %s", company)
        return False
    except sqlite3.Error as e:
        logger.error("add_to_blacklist failed: %s", e)
        raise


def remove_from_blacklist(company: str) -> bool:
    """
    Remove a company from the blacklist.

    Args:
        company: Company name to remove.

    Returns:
        True if a row was deleted, False if not found.
    """
    try:
        with get_connection() as conn:
            cur = conn.execute("DELETE FROM blacklist WHERE company = ?", (company.strip(),))
            return cur.rowcount > 0
    except sqlite3.Error as e:
        logger.error("remove_from_blacklist failed: %s", e)
        raise


def get_digest_candidates(threshold: float) -> list:
    """
    Return jobs with match_score >= threshold that have not yet been included
    in a digest (digest_sent = 0). Used for the daily 8am digest.

    Args:
        threshold: Minimum match_score (e.g. 0.75).

    Returns:
        List of dicts with job fields including id.
    """
    try:
        with get_connection() as conn:
            cur = conn.execute(
                """
                SELECT id, title, company, location, url, salary_min, salary_max,
                       source, match_score, created_at
                FROM jobs
                WHERE match_score >= ? AND digest_sent = 0
                ORDER BY match_score DESC
                """,
                (threshold,),
            )
            return [dict(row) for row in cur.fetchall()]
    except sqlite3.Error as e:
        logger.error("get_digest_candidates failed: %s", e)
        raise


def get_all_jobs(limit: int = 100) -> list:
    """
    Return all stored jobs sorted by match_score descending, for the UI.

    Args:
        limit: Maximum number of jobs to return.

    Returns:
        List of dicts with job fields.
    """
    try:
        with get_connection() as conn:
            cur = conn.execute(
                """
                SELECT id, title, company, location, url, salary_min, salary_max,
                       source, match_score, created_at
                FROM jobs
                ORDER BY match_score DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(row) for row in cur.fetchall()]
    except sqlite3.Error as e:
        logger.error("get_all_jobs failed: %s", e)
        raise
