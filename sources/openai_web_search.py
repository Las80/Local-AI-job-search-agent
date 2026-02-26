"""
OpenAI Chat Completions web-search job source for the Local AI Job Search Agent.
Uses gpt-4o-search-preview to find UK job listings via the OpenAI web search tool.
Returns normalised job dicts consistent with other sources. Optional: only runs
when OPENAI_API_KEY is set.
"""

import logging
from typing import Any

import config

logger = logging.getLogger(__name__)

# Model that supports web search in Chat Completions
OPENAI_WEB_SEARCH_MODEL = "gpt-4o-search-preview"
# Source label for jobs from this provider
SOURCE_LABEL = "openai_web_search"
# Request timeout in seconds
REQUEST_TIMEOUT_SECONDS = 60


def fetch_openai_web_search_jobs() -> list[dict[str, Any]]:
    """
    Fetch job listings via OpenAI Chat Completions with web search.
    Asks the model to find UK jobs for junior/associate AI automation, prompt
    engineering, LLM integration, etc., then parses the response and citations
    into normalised job dicts.

    Returns:
        List of job dicts with keys: title, company, location, description,
        url, salary_min, salary_max, source. Empty list if key not set or on error.
    """
    api_key = (config.config.get("OPENAI_API_KEY") or "").strip()
    if not api_key:
        logger.debug("OpenAI API key not set; skipping web-search source")
        return []

    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("openai package not installed; skipping OpenAI web-search source")
        return []

    client = OpenAI(api_key=api_key)
    prompt = _build_prompt()
    # Optional: bias search to UK (format may vary by API version)
    web_search_options: dict[str, Any] = {}
    try:
        web_search_options = {
            "user_location": {
                "type": "approximate",
                "approximate": {
                    "country": "GB",
                    "city": "London",
                    "region": "London",
                },
            },
        }
    except Exception:
        pass

    try:
        completion = client.chat.completions.create(
            model=OPENAI_WEB_SEARCH_MODEL,
            web_search_options=web_search_options,
            messages=[{"role": "user", "content": prompt}],
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except Exception as e:
        logger.warning("OpenAI web-search request failed: %s", e)
        return []

    return _parse_completion_to_jobs(completion)


def _build_prompt() -> str:
    """Build the user prompt for job search (UK, target roles)."""
    return (
        "Search the web for current job listings in the United Kingdom for these roles: "
        "junior or associate AI automation, prompt engineer, LLM integration engineer, "
        "AI workflow developer, low-code AI developer, SAP and AI hybrid. "
        "For each job you find, output exactly one line in this format: "
        "Job Title | Company Name | Location "
        "(e.g. London, Remote, Manchester, Hybrid). "
        "Cite the job application URL for each job so I can visit the link. "
        "List up to 20 different jobs, one per line."
    )


def _parse_completion_to_jobs(completion: Any) -> list[dict[str, Any]]:
    """
    Parse Chat Completions response into normalised job dicts.
    Uses message.content for text and message.annotations for URL citations.
    """
    jobs: list[dict[str, Any]] = []
    try:
        choice = completion.choices[0] if completion.choices else None
        if not choice or not choice.message:
            return jobs
        msg = choice.message
        content = msg.content or ""
        annotations: list[Any] = []
        # Chat Completions: content can be str or list of content blocks
        if isinstance(content, list):
            text_parts = []
            for part in content:
                if hasattr(part, "text"):
                    text_parts.append(part.text or "")
                elif isinstance(part, dict):
                    if part.get("type") == "output_text":
                        text_parts.append(part.get("text", ""))
                    # Annotations may live on the first content block
                    anns = part.get("annotations") or []
                    if anns and not annotations:
                        annotations = anns
                if hasattr(part, "annotations") and part.annotations and not annotations:
                    annotations = list(part.annotations)
            content = "\n".join(text_parts)
        if not isinstance(content, str):
            content = str(content)
        content = content.strip()
        if not annotations:
            annotations = getattr(msg, "annotations", None) or []
        if not content:
            return jobs
        # Collect cited URLs (and titles) from annotations
        citations = _extract_citations(msg, annotations)
        # Parse lines like "Title | Company | Location"
        lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
        seen_urls: set[str] = set()
        for i, line in enumerate(lines):
            job = _parse_job_line(line, citations, i)
            if job and job.get("url") and job["url"] not in seen_urls:
                seen_urls.add(job["url"])
                jobs.append(job)
    except (AttributeError, IndexError, TypeError) as e:
        logger.debug("OpenAI response parse error: %s", e)
    logger.info("OpenAI web-search returned %d unique jobs", len(jobs))
    return jobs


def _extract_citations(msg: Any, annotations: list) -> list[tuple[str, str]]:
    """Extract (url, title) pairs from message annotations (url_citation)."""
    citations: list[tuple[str, str]] = []
    for ann in annotations:
        if isinstance(ann, dict):
            if ann.get("type") == "url_citation":
                uc = ann.get("url_citation") or ann
                url = (uc.get("url") or ann.get("url") or "").strip()
                title = (uc.get("title") or ann.get("title") or "").strip()
                if url:
                    citations.append((url, title))
        elif hasattr(ann, "type") and getattr(ann, "type", None) == "url_citation":
            uc = getattr(ann, "url_citation", ann)
            url = (getattr(uc, "url", None) or (uc.get("url") if isinstance(uc, dict) else None) or "").strip()
            title = (getattr(uc, "title", None) or (uc.get("title") if isinstance(uc, dict) else None) or "").strip()
            if url:
                citations.append((url, title))
    return citations


def _parse_job_line(
    line: str, citations: list[tuple[str, str]], line_index: int
) -> dict[str, Any] | None:
    """
    Parse a single "Title | Company | Location" line and attach URL from citations.
    """
    # Split by pipe; allow for extra pipes in job title or company
    parts = [p.strip() for p in line.split("|")]
    if len(parts) < 3:
        # Fallback: treat whole line as title if we have a citation
        if citations and line_index < len(citations):
            url, title = citations[line_index]
            return {
                "title": line or title or "Untitled",
                "company": "",
                "location": "",
                "description": "",
                "url": url,
                "salary_min": None,
                "salary_max": None,
                "source": SOURCE_LABEL,
            }
        return None
    title = parts[0] or "Untitled"
    company = parts[1] if len(parts) > 1 else ""
    location = parts[2] if len(parts) > 2 else ""
    url = ""
    if line_index < len(citations):
        url, _ = citations[line_index]
    if not url:
        return None
    return {
        "title": title,
        "company": company,
        "location": location,
        "description": "",
        "url": url,
        "salary_min": None,
        "salary_max": None,
        "source": SOURCE_LABEL,
    }
