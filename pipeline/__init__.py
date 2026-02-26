"""
Pipeline package for the Local AI Job Search Agent.
Normalisation, hard filtering, TF-IDF scoring, and deduplication of job listings.
"""

from pipeline.normalizer import normalize_job
from pipeline.hard_filter import passes_hard_filter
from pipeline.scorer import score_job
from pipeline.deduplicator import generate_hash, is_duplicate, deduplicate_batch

__all__ = [
    "normalize_job",
    "passes_hard_filter",
    "score_job",
    "generate_hash",
    "is_duplicate",
    "deduplicate_batch",
]
