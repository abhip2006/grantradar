"""
ORCID API Service
Fetch researcher profile data from ORCID public API.
No authentication required for public profiles.
"""

import logging
import re
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# ORCID Public API endpoint
ORCID_API_BASE = "https://pub.orcid.org/v3.0"


def validate_orcid(orcid: str) -> Optional[str]:
    """
    Validate and normalize ORCID identifier.

    Args:
        orcid: ORCID string (may include URL prefix)

    Returns:
        Normalized ORCID (XXXX-XXXX-XXXX-XXXX) or None if invalid
    """
    # Extract ORCID from URL if provided
    # e.g., https://orcid.org/0000-0002-1825-0097
    url_pattern = r"orcid\.org/(\d{4}-\d{4}-\d{4}-\d{3}[\dX])"
    url_match = re.search(url_pattern, orcid, re.IGNORECASE)
    if url_match:
        orcid = url_match.group(1)

    # Validate format
    orcid_pattern = r"^(\d{4}-\d{4}-\d{4}-\d{3}[\dX])$"
    match = re.match(orcid_pattern, orcid.strip().upper())
    if match:
        return match.group(1)

    return None


async def fetch_orcid_profile(orcid: str) -> Optional[dict[str, Any]]:
    """
    Fetch researcher profile from ORCID public API.

    Args:
        orcid: ORCID identifier (XXXX-XXXX-XXXX-XXXX)

    Returns:
        Profile data dict or None if not found
    """
    validated_orcid = validate_orcid(orcid)
    if not validated_orcid:
        logger.warning(f"Invalid ORCID format: {orcid}")
        return None

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Fetch person data (name, bio, keywords)
            person_response = await client.get(
                f"{ORCID_API_BASE}/{validated_orcid}/person",
                headers={"Accept": "application/json"},
            )
            person_response.raise_for_status()
            person_data = person_response.json()

            # Fetch works (publications)
            works_response = await client.get(
                f"{ORCID_API_BASE}/{validated_orcid}/works",
                headers={"Accept": "application/json"},
            )
            works_response.raise_for_status()
            works_data = works_response.json()

            # Fetch fundings (grants)
            fundings_response = await client.get(
                f"{ORCID_API_BASE}/{validated_orcid}/fundings",
                headers={"Accept": "application/json"},
            )
            fundings_response.raise_for_status()
            fundings_data = fundings_response.json()

            return {
                "orcid": validated_orcid,
                "person": person_data,
                "works": works_data,
                "fundings": fundings_data,
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"ORCID not found: {validated_orcid}")
            else:
                logger.error(f"ORCID API error: {e}")
            return None
        except httpx.RequestError as e:
            logger.error(f"ORCID request failed: {e}")
            return None


def parse_orcid_name(person_data: dict) -> Optional[str]:
    """Extract name from ORCID person data."""
    try:
        name_obj = person_data.get("name")
        if not name_obj:
            return None

        given = name_obj.get("given-names", {}).get("value", "")
        family = name_obj.get("family-name", {}).get("value", "")

        if given and family:
            return f"{given} {family}"
        return given or family or None
    except Exception:
        return None


def parse_orcid_keywords(person_data: dict) -> list[str]:
    """Extract keywords from ORCID person data."""
    try:
        keywords_obj = person_data.get("keywords", {})
        keyword_list = keywords_obj.get("keyword", [])
        return [kw.get("content", "") for kw in keyword_list if kw.get("content")]
    except Exception:
        return []


def parse_orcid_biography(person_data: dict) -> Optional[str]:
    """Extract biography from ORCID person data."""
    try:
        bio_obj = person_data.get("biography", {})
        return bio_obj.get("content") if bio_obj else None
    except Exception:
        return None


def parse_orcid_works(works_data: dict, max_works: int = 20) -> list[dict]:
    """
    Extract publications from ORCID works data.

    Args:
        works_data: ORCID works response
        max_works: Maximum number of works to return

    Returns:
        List of publication dicts with title, journal, year
    """
    publications = []
    try:
        groups = works_data.get("group", [])

        for group in groups[:max_works]:
            work_summaries = group.get("work-summary", [])
            if not work_summaries:
                continue

            # Take first summary (they're grouped by similarity)
            summary = work_summaries[0]

            title_obj = summary.get("title", {})
            title = title_obj.get("title", {}).get("value", "")

            # Get publication year
            pub_date = summary.get("publication-date", {})
            year = pub_date.get("year", {}).get("value") if pub_date else None

            # Get journal
            journal = summary.get("journal-title", {})
            journal_name = journal.get("value") if journal else None

            # Get type
            work_type = summary.get("type", "").replace("-", " ").title()

            if title:
                publications.append(
                    {
                        "title": title,
                        "journal": journal_name,
                        "year": int(year) if year else None,
                        "type": work_type,
                    }
                )

    except Exception as e:
        logger.error(f"Error parsing ORCID works: {e}")

    return publications


def parse_orcid_fundings(fundings_data: dict, max_fundings: int = 20) -> list[dict]:
    """
    Extract grant history from ORCID fundings data.

    Args:
        fundings_data: ORCID fundings response
        max_fundings: Maximum number of fundings to return

    Returns:
        List of grant dicts with title, funder, amount, dates
    """
    grants = []
    try:
        groups = fundings_data.get("group", [])

        for group in groups[:max_fundings]:
            funding_summaries = group.get("funding-summary", [])
            if not funding_summaries:
                continue

            summary = funding_summaries[0]

            title_obj = summary.get("title", {})
            title = title_obj.get("title", {}).get("value", "")

            # Get funder
            org = summary.get("organization", {})
            funder = org.get("name", "") if org else ""

            # Get funding type
            funding_type = summary.get("type", "").replace("_", " ").title()

            # Get dates
            start_date = summary.get("start-date", {})
            start_year = start_date.get("year", {}).get("value") if start_date else None

            end_date = summary.get("end-date", {})
            end_year = end_date.get("year", {}).get("value") if end_date else None

            if title:
                grants.append(
                    {
                        "title": title,
                        "funder": funder,
                        "type": funding_type,
                        "start_year": int(start_year) if start_year else None,
                        "end_year": int(end_year) if end_year else None,
                    }
                )

    except Exception as e:
        logger.error(f"Error parsing ORCID fundings: {e}")

    return grants


def extract_research_areas_from_orcid(
    keywords: list[str],
    publications: list[dict],
    bio: Optional[str] = None,
) -> list[str]:
    """
    Extract research areas from ORCID data using keyword analysis.
    No AI required - uses keyword matching and frequency analysis.

    Args:
        keywords: ORCID keywords
        publications: Parsed publications
        bio: Biography text

    Returns:
        List of research area strings
    """
    research_areas = set()

    # Add direct keywords
    for kw in keywords:
        if kw and len(kw) > 2:
            research_areas.add(kw.lower())

    # Extract common research terms from publication titles
    common_research_terms = {
        "machine learning",
        "deep learning",
        "artificial intelligence",
        "neural network",
        "natural language processing",
        "computer vision",
        "data science",
        "bioinformatics",
        "genomics",
        "proteomics",
        "cancer",
        "immunology",
        "neuroscience",
        "genetics",
        "molecular biology",
        "cell biology",
        "biochemistry",
        "pharmacology",
        "epidemiology",
        "climate change",
        "environmental",
        "ecology",
        "sustainability",
        "renewable energy",
        "materials science",
        "nanotechnology",
        "quantum",
        "physics",
        "chemistry",
        "psychology",
        "cognitive",
        "behavioral",
        "social science",
        "economics",
        "public health",
        "healthcare",
        "clinical",
        "therapeutics",
        "diagnostics",
    }

    # Check publication titles for research terms
    for pub in publications:
        title_lower = pub.get("title", "").lower()
        for term in common_research_terms:
            if term in title_lower:
                research_areas.add(term)

    # Check bio for research terms
    if bio:
        bio_lower = bio.lower()
        for term in common_research_terms:
            if term in bio_lower:
                research_areas.add(term)

    # Capitalize properly
    return [area.title() for area in list(research_areas)[:15]]


def extract_methods_from_orcid(publications: list[dict]) -> list[str]:
    """
    Extract research methods from publication titles.
    No AI required - uses keyword matching.
    """
    methods = set()

    common_methods = {
        "statistical analysis",
        "regression",
        "machine learning",
        "deep learning",
        "survey",
        "interview",
        "ethnography",
        "case study",
        "experiment",
        "randomized controlled trial",
        "meta-analysis",
        "systematic review",
        "simulation",
        "modeling",
        "computational",
        "quantitative",
        "qualitative",
        "sequencing",
        "mass spectrometry",
        "microscopy",
        "spectroscopy",
        "chromatography",
        "pcr",
        "elisa",
        "western blot",
        "flow cytometry",
        "clinical trial",
        "cohort study",
        "cross-sectional",
        "longitudinal",
    }

    for pub in publications:
        title_lower = pub.get("title", "").lower()
        for method in common_methods:
            if method in title_lower:
                methods.add(method)

    return [m.title() for m in list(methods)[:10]]


async def import_from_orcid(orcid: str) -> Optional[dict[str, Any]]:
    """
    Import researcher profile data from ORCID.

    Args:
        orcid: ORCID identifier

    Returns:
        Dict with parsed profile data ready for GrantRadar, or None if failed
    """
    raw_data = await fetch_orcid_profile(orcid)
    if not raw_data:
        return None

    person = raw_data.get("person", {})
    works = raw_data.get("works", {})
    fundings = raw_data.get("fundings", {})

    # Parse components
    name = parse_orcid_name(person)
    keywords = parse_orcid_keywords(person)
    bio = parse_orcid_biography(person)
    publications = parse_orcid_works(works)
    grants = parse_orcid_fundings(fundings)

    # Extract research areas and methods
    research_areas = extract_research_areas_from_orcid(keywords, publications, bio)
    methods = extract_methods_from_orcid(publications)

    return {
        "orcid": raw_data["orcid"],
        "name": name,
        "research_areas": research_areas,
        "methods": methods,
        "keywords": keywords,
        "publications": publications,
        "past_grants": grants,
        "biography": bio,
    }
