"""
Job source adapters for the Local AI Job Search Agent.
Each module fetches from a specific API (Adzuna, Reed, OpenAI web search)
and returns a list of normalised job dicts with a consistent schema.
"""

from sources.adzuna import fetch_adzuna_jobs
from sources.reed import fetch_reed_jobs
from sources.openai_web_search import fetch_openai_web_search_jobs

__all__ = [
    "fetch_adzuna_jobs",
    "fetch_reed_jobs",
    "fetch_openai_web_search_jobs",
]
