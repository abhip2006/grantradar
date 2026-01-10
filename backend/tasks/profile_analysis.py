"""
GrantRadar Profile Analysis Tasks
Celery tasks for analyzing researcher profiles using web scraping and AI.
"""

import time
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.celery_app import celery_app
from backend.database import sync_engine
from backend.models import LabProfile, User

logger = structlog.get_logger().bind(module="profile_analysis_tasks")

# API endpoints for research data
PUBMED_API = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NIH_REPORTER_API = "https://api.reporter.nih.gov/v2"
NSF_AWARDS_API = "https://api.nsf.gov/services/v1/awards.json"
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"


# =============================================================================
# Helper Functions for Web Scraping
# =============================================================================


def search_pubmed(name: str, institution: Optional[str] = None) -> dict[str, Any]:
    """
    Search PubMed for publications by author name.

    Args:
        name: Author name to search
        institution: Optional institution to narrow search

    Returns:
        Dictionary with publications info
    """
    try:
        query = f"{name}[Author]"
        if institution:
            query += f" AND {institution}[Affiliation]"

        with httpx.Client(timeout=30) as client:
            # Search for publications
            search_response = client.get(
                f"{PUBMED_API}/esearch.fcgi",
                params={
                    "db": "pubmed",
                    "term": query,
                    "retmax": 50,
                    "retmode": "json",
                },
            )
            search_data = search_response.json()

            result = search_data.get("esearchresult", {})
            id_list = result.get("idlist", [])
            total_count = int(result.get("count", 0))

            publications = []
            if id_list:
                # Fetch details for top publications
                ids_str = ",".join(id_list[:20])
                details_response = client.get(
                    f"{PUBMED_API}/esummary.fcgi",
                    params={
                        "db": "pubmed",
                        "id": ids_str,
                        "retmode": "json",
                    },
                )
                details_data = details_response.json()

                for pmid in id_list[:20]:
                    pub_info = details_data.get("result", {}).get(pmid, {})
                    if pub_info and pub_info != "uids":
                        publications.append(
                            {
                                "pmid": pmid,
                                "title": pub_info.get("title", ""),
                                "source": pub_info.get("source", ""),
                                "pubdate": pub_info.get("pubdate", ""),
                                "authors": [a.get("name", "") for a in pub_info.get("authors", [])[:5]],
                            }
                        )

            return {
                "total_publications": total_count,
                "recent_publications": publications,
                "source": "pubmed",
            }

    except Exception as e:
        logger.error("pubmed_search_error", error=str(e))
        return {"error": str(e), "source": "pubmed"}


def search_nih_reporter(name: str, institution: Optional[str] = None) -> dict[str, Any]:
    """
    Search NIH Reporter for grants by PI name.

    Args:
        name: PI name to search
        institution: Optional institution

    Returns:
        Dictionary with funding info
    """
    try:
        with httpx.Client(timeout=30) as client:
            # Search for grants
            search_payload = {
                "criteria": {
                    "pi_names": [{"any_name": name}],
                    "use_relevance": True,
                },
                "offset": 0,
                "limit": 25,
            }

            if institution:
                search_payload["criteria"]["org_names"] = [institution]

            response = client.post(
                f"{NIH_REPORTER_API}/projects/search",
                json=search_payload,
            )
            data = response.json()

            grants = []
            total_funding = 0

            for project in data.get("results", []):
                award_amount = project.get("award_amount", 0) or 0
                total_funding += award_amount

                grants.append(
                    {
                        "project_num": project.get("project_num"),
                        "title": project.get("project_title"),
                        "award_amount": award_amount,
                        "fiscal_year": project.get("fiscal_year"),
                        "organization": project.get("organization", {}).get("org_name"),
                        "activity_code": project.get("activity_code"),
                        "project_start": project.get("project_start_date"),
                        "project_end": project.get("project_end_date"),
                    }
                )

            # Separate current vs past funding
            current_year = datetime.now().year
            current_grants = [g for g in grants if g.get("project_end") and int(g["project_end"][:4]) >= current_year]
            past_grants = [g for g in grants if g not in current_grants]

            return {
                "total_grants": len(grants),
                "total_funding": total_funding,
                "current_grants": current_grants,
                "past_grants": past_grants[:10],
                "source": "nih_reporter",
            }

    except Exception as e:
        logger.error("nih_reporter_search_error", error=str(e))
        return {"error": str(e), "source": "nih_reporter"}


def search_nsf_awards(name: str, institution: Optional[str] = None) -> dict[str, Any]:
    """
    Search NSF Awards for grants by PI name.

    Args:
        name: PI name to search
        institution: Optional institution

    Returns:
        Dictionary with NSF funding info
    """
    try:
        with httpx.Client(timeout=30) as client:
            params = {
                "pdPIName": name,
                "printFields": "id,title,piFirstName,piLastName,piEmail,awardeeName,fundProgramName,awardee,startDate,expDate,estimatedTotalAmt",
            }

            if institution:
                params["awardeeName"] = institution

            response = client.get(NSF_AWARDS_API, params=params)
            data = response.json()

            awards = []
            total_funding = 0

            for award in data.get("response", {}).get("award", []):
                amount = int(award.get("estimatedTotalAmt", 0) or 0)
                total_funding += amount

                awards.append(
                    {
                        "award_id": award.get("id"),
                        "title": award.get("title"),
                        "amount": amount,
                        "program": award.get("fundProgramName"),
                        "organization": award.get("awardeeName"),
                        "start_date": award.get("startDate"),
                        "end_date": award.get("expDate"),
                    }
                )

            return {
                "total_awards": len(awards),
                "total_funding": total_funding,
                "awards": awards[:15],
                "source": "nsf",
            }

    except Exception as e:
        logger.error("nsf_search_error", error=str(e))
        return {"error": str(e), "source": "nsf"}


def search_semantic_scholar(name: str) -> dict[str, Any]:
    """
    Search Semantic Scholar for author profile and publications.

    Args:
        name: Author name to search

    Returns:
        Dictionary with publications and citation metrics
    """
    try:
        with httpx.Client(timeout=30) as client:
            # Search for author
            search_response = client.get(
                f"{SEMANTIC_SCHOLAR_API}/author/search",
                params={"query": name, "limit": 3},
            )
            search_data = search_response.json()

            authors = search_data.get("data", [])
            if not authors:
                return {"error": "Author not found", "source": "semantic_scholar"}

            # Get first matching author
            author_id = authors[0].get("authorId")

            # Get author details with papers
            author_response = client.get(
                f"{SEMANTIC_SCHOLAR_API}/author/{author_id}",
                params={"fields": "name,paperCount,citationCount,hIndex,papers.title,papers.year,papers.citationCount"},
            )
            author_data = author_response.json()

            papers = author_data.get("papers", [])[:15]

            return {
                "author_name": author_data.get("name"),
                "total_papers": author_data.get("paperCount", 0),
                "total_citations": author_data.get("citationCount", 0),
                "h_index": author_data.get("hIndex", 0),
                "recent_papers": [
                    {
                        "title": p.get("title"),
                        "year": p.get("year"),
                        "citations": p.get("citationCount", 0),
                    }
                    for p in papers
                ],
                "source": "semantic_scholar",
            }

    except Exception as e:
        logger.error("semantic_scholar_error", error=str(e))
        return {"error": str(e), "source": "semantic_scholar"}


def search_lab_info(institution: str, lab_name: Optional[str] = None) -> dict[str, Any]:
    """
    Search for lab/research group information.

    This is a placeholder for more sophisticated lab scraping.
    In production, would integrate with institutional APIs or web scraping.

    Args:
        institution: Institution name
        lab_name: Optional lab/group name

    Returns:
        Dictionary with lab details
    """
    # Placeholder - in production would scrape lab websites
    return {
        "institution": institution,
        "lab_name": lab_name,
        "estimated_members": None,
        "website": None,
        "focus_areas": [],
        "note": "Lab scraping not yet implemented - manual entry recommended",
    }


# =============================================================================
# Main Profile Analysis Task
# =============================================================================


@celery_app.task(
    bind=True,
    queue="default",
    priority=5,
    soft_time_limit=180,  # 3 minutes soft limit
    time_limit=240,  # 4 minutes hard limit
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def analyze_user_profile(self, user_id: str) -> dict[str, Any]:
    """
    Analyze a user's profile by scraping the web for their information.

    This task:
    1. Fetches user info (name, institution, lab_name)
    2. Searches PubMed for publications
    3. Searches NIH Reporter for federal funding
    4. Searches NSF Awards for NSF funding
    5. Searches Semantic Scholar for citation metrics
    6. Stores results in LabProfile model

    Args:
        user_id: UUID string of the user to analyze

    Returns:
        Dictionary with analysis results and statistics
    """
    start_time = time.time()
    task_id = self.request.id

    logger.info(
        "profile_analysis_started",
        task_id=task_id,
        user_id=user_id,
    )

    # Validate user_id
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        logger.error("invalid_user_id", user_id=user_id)
        raise ValueError(f"Invalid user_id format: {user_id}")

    with Session(sync_engine) as session:
        # Fetch user
        user = session.execute(select(User).where(User.id == user_uuid)).scalar_one_or_none()

        if not user:
            logger.error("user_not_found", user_id=user_id)
            raise ValueError(f"User not found: {user_id}")

        # Fetch or create lab profile
        profile = session.execute(select(LabProfile).where(LabProfile.user_id == user_uuid)).scalar_one_or_none()

        if not profile:
            profile = LabProfile(
                user_id=user_uuid,
                analysis_status="in_progress",
                analysis_started_at=datetime.utcnow(),
            )
            session.add(profile)
        else:
            profile.analysis_status = "in_progress"
            profile.analysis_started_at = datetime.utcnow()

        session.commit()

        # Get search parameters
        name = user.name or ""
        institution = user.institution
        lab_name = user.lab_name

        if not name:
            logger.warning("no_user_name", user_id=user_id)
            profile.analysis_status = "failed"
            profile.analysis_completed_at = datetime.utcnow()
            session.commit()
            return {"error": "User name is required for profile analysis"}

        # Run web searches
        results = {}

        # 1. Search PubMed
        logger.info("searching_pubmed", name=name)
        pubmed_results = search_pubmed(name, institution)
        results["pubmed"] = pubmed_results

        # 2. Search NIH Reporter
        logger.info("searching_nih_reporter", name=name)
        nih_results = search_nih_reporter(name, institution)
        results["nih_reporter"] = nih_results

        # 3. Search NSF Awards
        logger.info("searching_nsf", name=name)
        nsf_results = search_nsf_awards(name, institution)
        results["nsf"] = nsf_results

        # 4. Search Semantic Scholar
        logger.info("searching_semantic_scholar", name=name)
        ss_results = search_semantic_scholar(name)
        results["semantic_scholar"] = ss_results

        # 5. Search for lab info
        if institution:
            logger.info("searching_lab_info", institution=institution)
            lab_results = search_lab_info(institution, lab_name)
            results["lab_info"] = lab_results

        # Consolidate results into profile fields

        # Publications
        publications = {
            "total_count": pubmed_results.get("total_publications", 0),
            "h_index": ss_results.get("h_index"),
            "total_citations": ss_results.get("total_citations"),
            "pubmed": pubmed_results.get("recent_publications", []),
            "semantic_scholar": ss_results.get("recent_papers", []),
        }

        # Past grants (combine NIH and NSF)
        past_grants = {
            "nih": nih_results.get("past_grants", []),
            "nsf": nsf_results.get("awards", []),
            "total_count": nih_results.get("total_grants", 0) + nsf_results.get("total_awards", 0),
            "total_funding": nih_results.get("total_funding", 0) + nsf_results.get("total_funding", 0),
        }

        # Current funding
        current_funding = {
            "nih": nih_results.get("current_grants", []),
            "active_count": len(nih_results.get("current_grants", [])),
        }

        # Lab details
        lab_details = results.get("lab_info", {})

        # Update profile
        profile.publications = publications
        profile.past_grants = past_grants
        profile.current_funding = current_funding
        profile.lab_details = lab_details
        profile.analysis_status = "completed"
        profile.analysis_completed_at = datetime.utcnow()

        session.commit()

        processing_time = time.time() - start_time

        logger.info(
            "profile_analysis_completed",
            task_id=task_id,
            user_id=user_id,
            processing_time_seconds=processing_time,
            total_publications=publications.get("total_count", 0),
            total_grants=past_grants.get("total_count", 0),
        )

        return {
            "user_id": user_id,
            "status": "completed",
            "processing_time_seconds": processing_time,
            "publications_found": publications.get("total_count", 0),
            "grants_found": past_grants.get("total_count", 0),
            "h_index": publications.get("h_index"),
            "total_citations": publications.get("total_citations"),
            "total_funding": past_grants.get("total_funding", 0),
        }


@celery_app.task(
    bind=True,
    queue="default",
    priority=3,
)
def analyze_cv_content(self, user_id: str) -> dict[str, Any]:
    """
    Analyze uploaded CV content for a user.

    Uses the stored CV file to extract additional information
    that wasn't captured by the initial parse.

    Args:
        user_id: UUID string of the user

    Returns:
        Dictionary with CV analysis results
    """
    logger.info("cv_analysis_started", user_id=user_id)

    try:
        user_uuid = UUID(user_id)
    except ValueError:
        return {"error": f"Invalid user_id: {user_id}"}

    with Session(sync_engine) as session:
        user = session.execute(select(User).where(User.id == user_uuid)).scalar_one_or_none()

        if not user or not user.cv_path:
            return {"error": "No CV found for user"}

        # Read CV file
        try:
            with open(user.cv_path, "rb") as f:
                cv_content = f.read()
        except FileNotFoundError:
            return {"error": "CV file not found"}

        # Parse CV
        from backend.services.cv_parser import parse_cv
        import asyncio

        result = asyncio.get_event_loop().run_until_complete(parse_cv(cv_content))

        if not result:
            return {"error": "Could not parse CV"}

        # Update profile with CV analysis
        profile = session.execute(select(LabProfile).where(LabProfile.user_id == user_uuid)).scalar_one_or_none()

        if profile:
            profile.cv_analysis = {
                "name": result.get("name"),
                "email": result.get("email"),
                "institution": result.get("institution"),
                "research_areas": result.get("research_areas", []),
                "methods": result.get("methods", []),
                "publications": result.get("publications", []),
                "past_grants": result.get("past_grants", []),
                "career_stage": result.get("career_stage"),
                "analyzed_at": datetime.utcnow().isoformat(),
            }
            session.commit()

        logger.info("cv_analysis_completed", user_id=user_id)

        return {
            "user_id": user_id,
            "status": "completed",
            "research_areas": result.get("research_areas", []),
            "methods": result.get("methods", []),
            "publications_count": len(result.get("publications", [])),
            "grants_count": len(result.get("past_grants", [])),
        }
