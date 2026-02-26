"""
TF-IDF and keyword scoring for the Local AI Job Search Agent.
Combines a keyword match score (weight 0.3) with TF-IDF cosine similarity
to the candidate profile (weight 0.7) to produce a final match score.
"""

import logging
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# Candidate profile text used for TF-IDF similarity
CANDIDATE_PROFILE = (
    "Career transitioner into AI automation and integration with 10+ years in enterprise "
    "SAP support. Experienced in LLM workflow design, prompt engineering, AI API integration, "
    "Python, and low-code automation tools. Built AI-assisted content generation pipelines "
    "and conversational AI applications. Strong background in process analysis, system "
    "validation, stakeholder coordination, and documentation in enterprise environments. "
    "Seeking junior or associate AI automation, LLM integration, or prompt engineering "
    "roles in the UK."
)

# Keywords for layer 1; matches counted in title + description
KEYWORDS_FOR_SCORE = [
    "ai", "llm", "automation", "prompt", "integration", "python",
    "machine learning", "workflow", "artificial intelligence", "nlp",
    "gpt", "langchain", "openai", "sap", "low-code", "no-code", "api",
]

# Cap keyword matches at this count for normalising to 1.0
KEYWORD_MATCH_CAP = 5
# Weight for keyword score in final score
KEYWORD_WEIGHT = 0.3
# Weight for TF-IDF score in final score
TFIDF_WEIGHT = 0.7
# Decimal places for final score
SCORE_DECIMALS = 4


def score_job(job: dict[str, Any]) -> float:
    """
    Compute a match score between 0.0 and 1.0 using keyword count and TF-IDF
    cosine similarity to the candidate profile.

    Args:
        job: Normalised job dict with title and description.

    Returns:
        Float in [0.0, 1.0], rounded to 4 decimal places.
    """
    text = f"{job.get('title') or ''} {job.get('description') or ''}".lower()

    # Layer 1: keyword score (cap at 1.0)
    matches = sum(1 for kw in KEYWORDS_FOR_SCORE if kw in text)
    keyword_score = min(matches / KEYWORD_MATCH_CAP, 1.0)

    # Layer 2: TF-IDF cosine similarity
    doc_description = (job.get("description") or "").strip()
    if not doc_description:
        tfidf_score = 0.0
    else:
        try:
            vectorizer = TfidfVectorizer()
            # Fit on profile and job description (two documents)
            matrix = vectorizer.fit_transform([CANDIDATE_PROFILE, doc_description])
            sim = cosine_similarity(matrix[0:1], matrix[1:2])[0][0]
            tfidf_score = max(0.0, min(1.0, float(sim)))
        except Exception as e:
            logger.debug("TF-IDF scoring failed: %s", e)
            tfidf_score = 0.0

    final = (keyword_score * KEYWORD_WEIGHT) + (tfidf_score * TFIDF_WEIGHT)
    return round(final, SCORE_DECIMALS)
