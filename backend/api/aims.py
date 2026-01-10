"""Specific Aims analysis API endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.api.deps import get_current_user
from backend.models import User
from backend.schemas.aims import (
    GrantMechanism,
    AimsAnalysisRequest,
    AimsAnalysisResponse,
    ScopeCheckRequest,
    ScopeCheckResponse,
    CompareToFundedRequest,
    CompareToFundedResponse,
    MechanismTemplateResponse,
    FundedExampleSummary,
    AimsFollowUpRequest,
    AimsFollowUpResponse,
)
from backend.services.specific_aims import (
    SpecificAimsAnalyzer,
    get_mechanism_template,
    get_funded_examples,
)

router = APIRouter(prefix="/api/aims", tags=["aims"])

aims_analyzer = SpecificAimsAnalyzer()


@router.post("/analyze", response_model=AimsAnalysisResponse)
async def analyze_aims(
    request: AimsAnalysisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AimsAnalysisResponse:
    """
    Full analysis of specific aims text.

    Analyzes the structure, scope, and content of a Specific Aims page
    and provides detailed feedback including:
    - Overall quality score
    - Structure analysis for each aim
    - Scope assessments
    - Issue detection (circular logic, overlapping aims, missing elements)
    - Actionable improvement suggestions
    - Mechanism-specific feedback

    The analysis creates a chat session for follow-up questions.
    """
    try:
        return await aims_analyzer.analyze_aims_structure(
            db=db,
            user=current_user,
            text=request.text,
            mechanism=request.mechanism,
            research_area=request.research_area,
            additional_context=request.additional_context,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Aims analysis failed: {str(e)}")


@router.post("/scope-check", response_model=ScopeCheckResponse)
async def check_scope(
    request: ScopeCheckRequest,
    current_user: User = Depends(get_current_user),
) -> ScopeCheckResponse:
    """
    Quick scope assessment for a single aim.

    Evaluates whether a specific aim is appropriately scoped
    for the given grant mechanism. Returns:
    - Scope status (too_broad, too_narrow, appropriate, unclear)
    - Detailed explanation
    - Specific suggestions for scope adjustment
    """
    try:
        return await aims_analyzer.check_aim_scope(
            aim_text=request.aim_text,
            mechanism=request.mechanism,
            aim_number=request.aim_number,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Scope check failed: {str(e)}")


@router.get("/template/{mechanism}", response_model=MechanismTemplateResponse)
async def get_template(
    mechanism: GrantMechanism,
    current_user: User = Depends(get_current_user),
) -> MechanismTemplateResponse:
    """
    Get template structure for a specific grant mechanism.

    Returns:
    - Mechanism-specific guidelines (aims count, focus areas, requirements)
    - Template sections and structure
    - Example opening hooks and hypothesis formats
    - Transition phrases and strong action verbs
    - Full template outline

    Supported mechanisms: R01, R21, R03, K01, K08, K23, K99, F31, F32, CAREER
    """
    try:
        return get_mechanism_template(mechanism)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get template: {str(e)}"
        )


@router.get("/examples/{mechanism}", response_model=List[FundedExampleSummary])
async def get_examples(
    mechanism: GrantMechanism,
    current_user: User = Depends(get_current_user),
) -> List[FundedExampleSummary]:
    """
    Get example structures from funded grants.

    Returns anonymized patterns from successful applications including:
    - Number of aims used
    - Structure summary
    - Key features that contributed to success
    - Hypothesis style used
    """
    try:
        examples = get_funded_examples(mechanism)
        return examples
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get examples: {str(e)}"
        )


@router.post("/compare", response_model=CompareToFundedResponse)
async def compare_to_funded(
    request: CompareToFundedRequest,
    current_user: User = Depends(get_current_user),
) -> CompareToFundedResponse:
    """
    Compare aims structure to successful funded applications.

    Analyzes how the submitted aims align with patterns from
    funded applications and provides:
    - Similarity score
    - Structure comparison
    - Alignment points with funded applications
    - Deviations from typical successful patterns
    - Recommendations based on funded patterns
    """
    try:
        return await aims_analyzer.compare_to_funded(
            aims_text=request.aims_text,
            mechanism=request.mechanism,
            research_area=request.research_area,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Comparison failed: {str(e)}")


@router.post("/follow-up", response_model=AimsFollowUpResponse)
async def aims_follow_up(
    request: AimsFollowUpRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AimsFollowUpResponse:
    """
    Continue conversation with follow-up question about aims analysis.

    Use this endpoint to ask follow-up questions after receiving
    an initial aims analysis. The session_id from the analysis
    response is required.
    """
    try:
        return await aims_analyzer.follow_up(
            db=db,
            user=current_user,
            session_id=request.session_id,
            message=request.message,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Follow-up failed: {str(e)}")


@router.get("/mechanisms", response_model=List[dict])
async def list_mechanisms(
    current_user: User = Depends(get_current_user),
) -> List[dict]:
    """
    List all supported grant mechanisms with brief descriptions.

    Returns information about each supported mechanism including
    recommended aims count and focus areas.
    """
    from backend.services.specific_aims import MECHANISM_GUIDELINES

    mechanisms = []
    for mechanism, guidelines in MECHANISM_GUIDELINES.items():
        mechanisms.append(
            {
                "mechanism": mechanism.value,
                "recommended_aims": guidelines.recommended_aims_count,
                "aims_range": f"{guidelines.min_aims}-{guidelines.max_aims}",
                "focus_areas": guidelines.focus_areas[:3],  # Top 3 focus areas
                "word_count_guidance": guidelines.word_count_guidance,
            }
        )

    return mechanisms


@router.get("/guidelines/{mechanism}")
async def get_guidelines(
    mechanism: GrantMechanism,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get detailed guidelines for a specific mechanism.

    Returns comprehensive guidelines including:
    - Recommended aims count and range
    - Focus areas and key requirements
    - Common pitfalls to avoid
    - Typical structure outline
    """
    from backend.services.specific_aims import MECHANISM_GUIDELINES

    guidelines = MECHANISM_GUIDELINES.get(mechanism)
    if not guidelines:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Guidelines not found for mechanism: {mechanism.value}"
        )

    return {
        "mechanism": guidelines.mechanism.value,
        "recommended_aims_count": guidelines.recommended_aims_count,
        "min_aims": guidelines.min_aims,
        "max_aims": guidelines.max_aims,
        "focus_areas": guidelines.focus_areas,
        "key_requirements": guidelines.key_requirements,
        "common_pitfalls": guidelines.common_pitfalls,
        "word_count_guidance": guidelines.word_count_guidance,
        "typical_structure": guidelines.typical_structure,
    }
