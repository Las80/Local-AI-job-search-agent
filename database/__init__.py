"""
Database package for the Local AI Job Search Agent.
Exposes the SQLite connection manager and all database operations.
"""

from database.db import (
    get_connection,
    init_schema,
    insert_job,
    job_exists,
    get_unnotified_matches,
    get_digest_candidates,
    mark_notified,
    get_blacklist,
    add_to_blacklist,
    remove_from_blacklist,
    get_all_jobs,
)

__all__ = [
    "get_connection",
    "init_schema",
    "insert_job",
    "job_exists",
    "get_unnotified_matches",
    "get_digest_candidates",
    "mark_notified",
    "get_blacklist",
    "add_to_blacklist",
    "remove_from_blacklist",
    "get_all_jobs",
]
