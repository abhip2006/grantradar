"""
Winners Intelligence API Endpoints.
Access to 2.6M+ funded NIH/NSF projects for pattern analysis.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.services.winners import get_winners_service
from backend.services.winners_analytics import get_winners_analytics_service
from backend.schemas.winners import (
    AbstractAnalysisRequest,
    AbstractAnalysisResponse,
    FundedProject,
    InstitutionsResponse,
    KeywordAnalysisRequest,
    KeywordAnalysisResponse,
    ProgramOfficersResponse,
    SuccessPredictionRequest,
    SuccessPredictionResponse,
    WinnersSearchRequest,
    WinnersSearchResponse,
)

router = APIRouter(prefix="/api/winners", tags=["Winners Intelligence"])


@router.get(
    "/search",
    response_model=WinnersSearchResponse,
    summary="Search funded projects",
    description="Search 2.6M+ funded NIH projects by keywords, activity codes, institutes, and more.",
)
async def search_funded_projects(
    current_user: CurrentUser,
    query: Optional[str] = Query(None, description="Keyword search in titles and abstracts"),
    activity_codes: Optional[str] = Query(
        None, description="Activity codes comma-separated (R01,R21,K08)"
    ),
    institute: Optional[str] = Query(None, description="NIH institute abbreviation (NCI, NIMH)"),
    fiscal_years: Optional[str] = Query(
        None, description="Fiscal years comma-separated (2024,2023,2022)"
    ),
    institution: Optional[str] = Query(None, description="Institution name search"),
    pi_name: Optional[str] = Query(None, description="PI name search"),
    state: Optional[str] = Query(None, description="State abbreviation (CA, NY, TX)"),
    min_amount: Optional[int] = Query(None, ge=0, description="Minimum award amount"),
    max_amount: Optional[int] = Query(None, description="Maximum award amount"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
) -> WinnersSearchResponse:
    """
    Search funded projects from NIH Reporter.

    Returns matching projects with aggregations by year, mechanism, and institute.
    Use this to find successful grants in your research area.
    """
    # Parse comma-separated values
    codes = activity_codes.split(",") if activity_codes else None
    years = [int(y.strip()) for y in fiscal_years.split(",")] if fiscal_years else None

    request = WinnersSearchRequest(
        query=query,
        activity_codes=codes,
        institute=institute,
        fiscal_years=years,
        institution=institution,
        pi_name=pi_name,
        state=state,
        min_amount=min_amount,
        max_amount=max_amount,
        page=page,
        limit=limit,
    )

    service = get_winners_service()
    try:
        return await service.search_projects(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get(
    "/project/{project_num}",
    response_model=FundedProject,
    summary="Get project details",
    description="Get detailed information about a specific funded project.",
)
async def get_project_details(
    current_user: CurrentUser,
    project_num: str,
) -> FundedProject:
    """
    Get details for a specific funded project by project number.

    The project number is the unique identifier from NIH Reporter
    (e.g., '5R01CA123456-02').
    """
    service = get_winners_service()

    # Search for specific project
    request = WinnersSearchRequest(query=project_num, page=1, limit=1)

    try:
        result = await service.search_projects(request)
        if result.results:
            return result.results[0]
        raise HTTPException(status_code=404, detail=f"Project {project_num} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch project: {str(e)}")


@router.get(
    "/program-officers",
    response_model=ProgramOfficersResponse,
    summary="Get program officers",
    description="Get NIH program officers with their funding patterns and recent projects.",
)
async def get_program_officers(
    current_user: CurrentUser,
    institute: Optional[str] = Query(None, description="NIH institute abbreviation (NCI, NIMH)"),
    research_area: Optional[str] = Query(None, description="Research area keywords"),
    limit: int = Query(20, ge=5, le=100, description="Maximum officers to return"),
) -> ProgramOfficersResponse:
    """
    Get program officers with their funding patterns.

    Use this to find program officers who fund research similar to yours.
    Returns their recent projects, top mechanisms, and funding totals.
    """
    service = get_winners_service()
    try:
        return await service.get_program_officers(
            institute=institute,
            research_area=research_area,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch officers: {str(e)}")


@router.get(
    "/institutions",
    response_model=InstitutionsResponse,
    summary="Get institution rankings",
    description="Get institution success statistics ranked by funding.",
)
async def get_institution_rankings(
    current_user: CurrentUser,
    research_area: Optional[str] = Query(None, description="Research area keywords"),
    mechanism: Optional[str] = Query(None, description="Activity code (R01, R21)"),
    fiscal_years: Optional[str] = Query(
        None, description="Fiscal years comma-separated (2024,2023)"
    ),
    limit: int = Query(50, ge=10, le=200, description="Maximum institutions to return"),
) -> InstitutionsResponse:
    """
    Get institutions ranked by funding success.

    Returns total awards, funding amounts, top mechanisms, and top PIs
    for each institution matching your criteria.
    """
    years = [int(y.strip()) for y in fiscal_years.split(",")] if fiscal_years else None

    service = get_winners_service()
    try:
        return await service.get_institution_stats(
            research_area=research_area,
            mechanism=mechanism,
            fiscal_years=years,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch institutions: {str(e)}")


@router.get(
    "/mechanisms",
    summary="Get mechanism statistics",
    description="Get statistics by activity code/mechanism.",
)
async def get_mechanism_stats(
    current_user: CurrentUser,
    institute: Optional[str] = Query(None, description="NIH institute abbreviation"),
    fiscal_years: Optional[str] = Query(None, description="Fiscal years comma-separated"),
) -> dict:
    """
    Get funding statistics by activity code (mechanism).

    Shows award counts, average sizes, and trends for each mechanism
    (R01, R21, K08, etc.).
    """
    years = [int(y.strip()) for y in fiscal_years.split(",")] if fiscal_years else None

    # Search with just the filters to get aggregations
    request = WinnersSearchRequest(
        institute=institute,
        fiscal_years=years,
        page=1,
        limit=1,  # We just need the aggregations
    )

    service = get_winners_service()
    try:
        result = await service.search_projects(request)
        return {
            "mechanisms": [m.model_dump() for m in result.aggregations.by_mechanism],
            "total_projects": result.total,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch mechanism stats: {str(e)}")


@router.get(
    "/institutes",
    summary="Get NIH institute statistics",
    description="Get funding statistics by NIH institute.",
)
async def get_institute_stats(
    current_user: CurrentUser,
    mechanism: Optional[str] = Query(None, description="Activity code (R01, R21)"),
    fiscal_years: Optional[str] = Query(None, description="Fiscal years comma-separated"),
) -> dict:
    """
    Get funding statistics by NIH institute (NCI, NIMH, NINDS, etc.).

    Shows award counts and funding totals for each institute.
    """
    years = [int(y.strip()) for y in fiscal_years.split(",")] if fiscal_years else None

    # Parse mechanism as list
    codes = [mechanism] if mechanism else None

    request = WinnersSearchRequest(
        activity_codes=codes,
        fiscal_years=years,
        page=1,
        limit=1,
    )

    service = get_winners_service()
    try:
        result = await service.search_projects(request)
        return {
            "institutes": [i.model_dump() for i in result.aggregations.by_institute],
            "total_projects": result.total,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch institute stats: {str(e)}")


@router.get(
    "/years",
    summary="Get fiscal year statistics",
    description="Get funding trends by fiscal year.",
)
async def get_year_stats(
    current_user: CurrentUser,
    institute: Optional[str] = Query(None, description="NIH institute abbreviation"),
    mechanism: Optional[str] = Query(None, description="Activity code (R01, R21)"),
    years_back: int = Query(5, ge=1, le=10, description="Number of years to include"),
) -> dict:
    """
    Get funding trends by fiscal year.

    Shows project counts and total funding for each year.
    """
    from datetime import datetime
    current_year = datetime.now().year
    years = list(range(current_year - years_back + 1, current_year + 1))

    codes = [mechanism] if mechanism else None

    request = WinnersSearchRequest(
        institute=institute,
        activity_codes=codes,
        fiscal_years=years,
        page=1,
        limit=1,
    )

    service = get_winners_service()
    try:
        result = await service.search_projects(request)
        return {
            "years": [y.model_dump() for y in result.aggregations.by_year],
            "total_projects": result.total,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch year stats: {str(e)}")


@router.get(
    "/similar",
    response_model=WinnersSearchResponse,
    summary="Find similar funded projects",
    description="Find funded projects similar to a research description.",
)
async def find_similar_projects(
    current_user: CurrentUser,
    research_description: str = Query(..., min_length=20, description="Your research description"),
    mechanism: Optional[str] = Query(None, description="Target activity code (R01, R21)"),
    institute: Optional[str] = Query(None, description="Target NIH institute"),
    limit: int = Query(10, ge=5, le=50, description="Number of similar projects"),
) -> WinnersSearchResponse:
    """
    Find funded projects similar to your research.

    Enter a description of your research area to find successful grants
    with similar topics. Useful for identifying potential reviewers,
    understanding competition, and learning from successful applications.
    """
    codes = [mechanism] if mechanism else None

    request = WinnersSearchRequest(
        query=research_description,
        activity_codes=codes,
        institute=institute,
        page=1,
        limit=limit,
    )

    service = get_winners_service()
    try:
        return await service.search_projects(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# =============================================================================
# Analytics Endpoints (AI-Powered)
# =============================================================================


@router.post(
    "/keywords/analysis",
    response_model=KeywordAnalysisResponse,
    summary="Analyze keywords in funded grants",
    description="Extract and analyze keywords from successful grants.",
)
async def analyze_keywords(
    current_user: CurrentUser,
    request: KeywordAnalysisRequest,
) -> KeywordAnalysisResponse:
    """
    Analyze keywords in funded projects.

    Identifies the most common keywords and phrases in successful grants
    for a given mechanism and institute. Optionally compares against
    your research profile keywords.
    """
    # Get user profile keywords if comparison requested
    user_keywords = None
    if request.compare_to_profile and current_user.focus_areas:
        user_keywords = current_user.focus_areas

    service = get_winners_analytics_service()
    try:
        return await service.analyze_keywords(request, user_keywords)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post(
    "/abstracts/analyze",
    response_model=AbstractAnalysisResponse,
    summary="Analyze abstract patterns",
    description="AI-powered analysis of successful abstract patterns and language.",
)
async def analyze_abstracts(
    current_user: CurrentUser,
    request: AbstractAnalysisRequest,
) -> AbstractAnalysisResponse:
    """
    AI-powered analysis of successful abstract patterns.

    Analyzes funded grants to identify common structural patterns,
    language usage, and key phrases. Optionally compares your draft
    abstract against successful ones.
    """
    service = get_winners_analytics_service()
    try:
        return await service.analyze_abstracts(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post(
    "/predict-success",
    response_model=SuccessPredictionResponse,
    summary="Predict success probability",
    description="Predict grant success probability based on historical patterns.",
)
async def predict_success(
    current_user: CurrentUser,
    request: SuccessPredictionRequest,
) -> SuccessPredictionResponse:
    """
    Predict success probability for a grant application.

    Uses historical funding data and AI analysis to estimate your
    probability of success. Returns contributing factors and
    recommendations for improving your chances.
    """
    service = get_winners_analytics_service()
    try:
        return await service.predict_success(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")
