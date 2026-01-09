"""
Writing Assistant API Endpoints
Provides endpoints for analyzing and improving grant application drafts.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.database import get_db
from backend.models import User
from backend.schemas.writing import (
    AnalyzeRequest,
    AnalyzeResponse,
    CriteriaRequest,
    FeedbackRequest,
    FeedbackResponse,
    MechanismCriteria,
    SuggestionsRequest,
    SuggestionsResponse,
)
from backend.services.review_criteria import review_criteria_service
from backend.services.writing_assistant import writing_assistant

router = APIRouter(prefix="/api/writing", tags=["writing"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_draft(
    request: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalyzeResponse:
    """
    Analyze draft text against a grant's review criteria.

    Evaluates the draft against the review criteria for the specified
    grant mechanism, focusing on structure and completeness rather than
    subjective content quality.

    Args:
        request: Contains the draft text, mechanism code, and optional section type

    Returns:
        Analysis with scores for each criterion and recommendations
    """
    try:
        return await writing_assistant.analyze_text(
            db=db,
            text=request.text,
            mechanism=request.mechanism,
            section_type=request.section_type,
            grant_id=request.grant_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


@router.get("/criteria/{mechanism}", response_model=MechanismCriteria)
async def get_review_criteria(
    mechanism: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MechanismCriteria:
    """
    Get review criteria for a specific grant mechanism.

    Returns the standard review criteria used to evaluate applications
    for the specified mechanism (e.g., R01, R21, CAREER), including
    descriptions, weights, and tips for each criterion.

    Args:
        mechanism: Grant mechanism code (e.g., R01, R21, CAREER)

    Returns:
        Complete review criteria for the mechanism
    """
    try:
        # Try to get enriched criteria from database
        criteria = await review_criteria_service.get_criteria_from_db(db, mechanism)

        if not criteria:
            # Fall back to predefined criteria
            criteria = review_criteria_service.get_criteria_for_mechanism(mechanism)

        return criteria
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve criteria: {str(e)}"
        )


@router.post("/feedback", response_model=FeedbackResponse)
async def get_draft_feedback(
    request: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FeedbackResponse:
    """
    Get AI-powered feedback on a draft section.

    Provides structured feedback mapped to review criteria, including
    specific suggestions for improvement, identified gaps, and
    priority actions.

    Args:
        request: Contains draft text, mechanism, section type, and optional focus areas

    Returns:
        Structured feedback with criterion-specific guidance
    """
    try:
        return await writing_assistant.get_feedback(
            db=db,
            text=request.text,
            mechanism=request.mechanism,
            section_type=request.section_type,
            focus_areas=request.focus_areas,
            grant_id=request.grant_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Feedback generation failed: {str(e)}"
        )


@router.post("/suggestions", response_model=SuggestionsResponse)
async def get_improvement_suggestions(
    request: SuggestionsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SuggestionsResponse:
    """
    Get specific improvement suggestions based on criteria gaps.

    Analyzes the draft and returns actionable suggestions for
    improving coverage of review criteria.

    Args:
        request: Contains draft text, mechanism, section type, and max suggestions

    Returns:
        List of prioritized suggestions and gap analysis
    """
    try:
        return await writing_assistant.suggest_improvements(
            db=db,
            text=request.text,
            mechanism=request.mechanism,
            section_type=request.section_type,
            max_suggestions=request.max_suggestions,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Suggestions generation failed: {str(e)}"
        )


@router.get("/criteria/{mechanism}/tips/{criterion}")
async def get_criterion_tips(
    mechanism: str,
    criterion: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get tips for a specific review criterion.

    Returns helpful tips for addressing a particular criterion
    in the specified mechanism.

    Args:
        mechanism: Grant mechanism code
        criterion: Name of the criterion

    Returns:
        Tips and common weaknesses for the criterion
    """
    tips = review_criteria_service.get_criterion_tips(mechanism, criterion)

    if not tips:
        # Try to get from criteria object
        criteria = review_criteria_service.get_criteria_for_mechanism(mechanism)
        for c in criteria.criteria:
            if c.name.lower() == criterion.lower():
                return {
                    "criterion": c.name,
                    "tips": c.tips,
                    "common_weaknesses": c.common_weaknesses,
                    "scoring_guidance": c.scoring_guidance,
                }

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Criterion '{criterion}' not found for mechanism '{mechanism}'"
        )

    return {
        "criterion": criterion,
        "tips": tips,
    }


@router.get("/mechanisms")
async def list_supported_mechanisms(
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    List all supported grant mechanisms.

    Returns a list of mechanism codes and names that the writing
    assistant can provide criteria and analysis for.

    Returns:
        Dictionary of mechanism codes to names by agency
    """
    return {
        "NIH": {
            "R01": "Research Project Grant",
            "R21": "Exploratory/Developmental Research Grant",
            "R03": "Small Grant Program",
            "R15": "Academic Research Enhancement Award",
            "K01": "Mentored Research Scientist Development Award",
            "K08": "Mentored Clinical Scientist Development Award",
            "K23": "Mentored Patient-Oriented Research Career Development Award",
            "K99": "Pathway to Independence Award",
            "F31": "Predoctoral Individual NRSA",
            "F32": "Postdoctoral Individual NRSA",
        },
        "NSF": {
            "CAREER": "Faculty Early Career Development Program",
            "Standard": "NSF Standard Research Grant",
            "SBIR/STTR": "Small Business Innovation Research",
        },
    }


@router.get("/section-types/{mechanism}")
async def get_section_types(
    mechanism: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get section types for a mechanism.

    Returns the common section types used in applications for
    the specified mechanism.

    Args:
        mechanism: Grant mechanism code

    Returns:
        List of section types with descriptions
    """
    agency = review_criteria_service.get_agency_from_mechanism(mechanism)

    if agency.value == "NIH":
        return {
            "sections": [
                {"type": "specific_aims", "name": "Specific Aims", "page_limit": 1},
                {"type": "significance", "name": "Significance", "page_limit": None},
                {"type": "innovation", "name": "Innovation", "page_limit": None},
                {"type": "approach", "name": "Approach", "page_limit": None},
                {"type": "research_strategy", "name": "Research Strategy", "page_limit": 12},
                {"type": "environment", "name": "Environment & Resources", "page_limit": None},
            ],
            "mechanism": mechanism,
            "agency": "NIH",
        }
    elif agency.value == "NSF":
        return {
            "sections": [
                {"type": "project_description", "name": "Project Description", "page_limit": 15},
                {"type": "intellectual_merit", "name": "Intellectual Merit", "page_limit": None},
                {"type": "broader_impacts", "name": "Broader Impacts", "page_limit": None},
            ],
            "mechanism": mechanism,
            "agency": "NSF",
        }
    else:
        return {
            "sections": [
                {"type": "abstract", "name": "Abstract", "page_limit": None},
                {"type": "research_strategy", "name": "Research Strategy", "page_limit": None},
            ],
            "mechanism": mechanism,
            "agency": agency.value,
        }
