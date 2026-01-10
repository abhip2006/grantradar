"""
Profile API Endpoints
Manage user lab profiles and onboarding.
"""

from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.models import LabProfile
from backend.schemas.profile import (
    LabProfileResponse,
    LabProfileUpdate,
    OnboardingData,
)

router = APIRouter(prefix="/api/profile", tags=["Profile"])


@router.get(
    "", response_model=LabProfileResponse, summary="Get user profile", description="Get the current user's lab profile."
)
async def get_profile(
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> LabProfileResponse:
    """
    Get the lab profile for the authenticated user.

    Returns 404 if no profile exists yet.
    """
    result = await db.execute(select(LabProfile).where(LabProfile.user_id == current_user.id))
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found. Complete onboarding to create a profile."
        )

    return LabProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        research_areas=profile.research_areas,
        methods=profile.methods,
        career_stage=profile.career_stage,
        citizenship_status=profile.citizenship_status,
        institution_type=profile.institution_type,
        is_pi_eligible=profile.is_pi_eligible,
        past_grants=profile.past_grants,
        publications=profile.publications,
        orcid=profile.orcid,
        has_embedding=profile.profile_embedding is not None,
        created_at=profile.created_at,
    )


@router.put(
    "",
    response_model=LabProfileResponse,
    summary="Update user profile",
    description="Update the current user's lab profile. Triggers re-embedding.",
)
async def update_profile(
    profile_data: LabProfileUpdate,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> LabProfileResponse:
    """
    Update the lab profile for the authenticated user.

    Changes to research areas, methods, or publications will trigger
    re-computation of the profile embedding.
    """
    result = await db.execute(select(LabProfile).where(LabProfile.user_id == current_user.id))
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found. Complete onboarding to create a profile."
        )

    # Track if embedding-relevant fields changed
    needs_reembedding = False
    embedding_fields = ["research_areas", "methods", "publications"]

    # Update profile fields
    update_data = profile_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if hasattr(profile, field):
            old_value = getattr(profile, field)
            if old_value != value:
                setattr(profile, field, value)
                if field in embedding_fields:
                    needs_reembedding = True

    # Clear embedding if re-embedding is needed
    if needs_reembedding:
        profile.profile_embedding = None
        # Trigger async task to re-compute embedding
        from backend.tasks.embeddings import compute_profile_embedding

        compute_profile_embedding.delay(str(profile.id))

    await db.flush()
    await db.refresh(profile)

    return LabProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        research_areas=profile.research_areas,
        methods=profile.methods,
        career_stage=profile.career_stage,
        citizenship_status=profile.citizenship_status,
        institution_type=profile.institution_type,
        is_pi_eligible=profile.is_pi_eligible,
        past_grants=profile.past_grants,
        publications=profile.publications,
        orcid=profile.orcid,
        has_embedding=profile.profile_embedding is not None,
        created_at=profile.created_at,
    )


@router.post(
    "/onboarding",
    response_model=LabProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Complete onboarding",
    description="Submit onboarding data to create user profile.",
)
async def complete_onboarding(
    onboarding_data: OnboardingData,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> LabProfileResponse:
    """
    Complete the onboarding process.

    Creates a lab profile and optionally updates user information.
    """
    # Check if profile already exists
    result = await db.execute(select(LabProfile).where(LabProfile.user_id == current_user.id))
    existing_profile = result.scalar_one_or_none()

    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Profile already exists. Use PUT /api/profile to update."
        )

    # Update user info if provided
    if onboarding_data.name:
        current_user.name = onboarding_data.name
    if onboarding_data.institution:
        current_user.institution = onboarding_data.institution
    if onboarding_data.phone:
        current_user.phone = onboarding_data.phone

    # Create lab profile
    profile = LabProfile(
        user_id=current_user.id,
        research_areas=onboarding_data.research_areas,
        methods=onboarding_data.methods,
        career_stage=onboarding_data.career_stage,
        citizenship_status=onboarding_data.citizenship_status,
        institution_type=onboarding_data.institution_type,
        is_pi_eligible=onboarding_data.is_pi_eligible or False,
        past_grants=onboarding_data.past_grants,
        publications=onboarding_data.publications,
        orcid=onboarding_data.orcid,
    )

    db.add(profile)
    await db.flush()
    await db.refresh(profile)

    # Trigger async task to compute profile embedding
    from backend.tasks.embeddings import compute_profile_embedding

    compute_profile_embedding.delay(str(profile.id))

    return LabProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        research_areas=profile.research_areas,
        methods=profile.methods,
        career_stage=profile.career_stage,
        citizenship_status=profile.citizenship_status,
        institution_type=profile.institution_type,
        is_pi_eligible=profile.is_pi_eligible,
        past_grants=profile.past_grants,
        publications=profile.publications,
        orcid=profile.orcid,
        has_embedding=False,  # Will be computed async
        created_at=profile.created_at,
    )


# =============================================================================
# Profile Import Endpoints
# =============================================================================


class ORCIDImportRequest(BaseModel):
    """Request schema for ORCID import."""

    orcid: str = Field(
        ..., description="ORCID identifier (e.g., 0000-0002-1825-0097 or https://orcid.org/0000-0002-1825-0097)"
    )


class ImportPreviewResponse(BaseModel):
    """Response schema for import preview."""

    name: Optional[str] = Field(None, description="Extracted name")
    institution: Optional[str] = Field(None, description="Extracted institution")
    research_areas: list[str] = Field(default_factory=list, description="Extracted research areas")
    methods: list[str] = Field(default_factory=list, description="Extracted methods")
    publications: list[dict] = Field(default_factory=list, description="Extracted publications")
    past_grants: list[dict] = Field(default_factory=list, description="Extracted grants")
    career_stage: Optional[str] = Field(None, description="Inferred career stage")
    keywords: list[str] = Field(default_factory=list, description="Extracted keywords")
    orcid: Optional[str] = Field(None, description="ORCID identifier")
    source: str = Field(..., description="Import source (orcid or cv)")


@router.post(
    "/import/orcid",
    response_model=ImportPreviewResponse,
    summary="Import profile from ORCID",
    description="Fetch and parse researcher data from ORCID public API.",
)
async def import_from_orcid(
    request: ORCIDImportRequest,
    current_user: CurrentUser,
) -> ImportPreviewResponse:
    """
    Import profile data from ORCID.

    Fetches public profile data from ORCID and extracts:
    - Research areas from keywords and publications
    - Methods from publication analysis
    - Publication history
    - Grant/funding history

    Returns a preview that can be used to populate onboarding.
    No AI credits used - uses keyword matching only.
    """
    from backend.services.orcid import import_from_orcid as orcid_import

    result = await orcid_import(request.orcid)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not fetch ORCID profile. Check the ORCID ID and ensure the profile is public.",
        )

    return ImportPreviewResponse(
        name=result.get("name"),
        institution=None,  # ORCID doesn't always have this
        research_areas=result.get("research_areas", []),
        methods=result.get("methods", []),
        publications=result.get("publications", []),
        past_grants=result.get("past_grants", []),
        career_stage=None,  # Inferred from other data
        keywords=result.get("keywords", []),
        orcid=result.get("orcid"),
        source="orcid",
    )


@router.post(
    "/import/cv",
    response_model=ImportPreviewResponse,
    summary="Import profile from CV",
    description="Upload and parse CV/resume PDF to extract profile data.",
)
async def import_from_cv(
    current_user: CurrentUser,
    db: AsyncSessionDep,
    file: UploadFile = File(..., description="CV/resume PDF file"),
    save_file: bool = True,
    trigger_analysis: bool = True,
) -> ImportPreviewResponse:
    """
    Import profile data from uploaded CV.

    Parses PDF to extract:
    - Name and contact info
    - Research areas/interests
    - Methods/techniques
    - Publications list
    - Grant history
    - Career stage

    If save_file=True, stores the CV and updates user.cv_path.
    If trigger_analysis=True, triggers the profile analysis workflow.

    Returns a preview that can be used to populate onboarding.
    """
    import os
    import uuid as uuid_lib

    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are supported")

    # Check file size (max 10MB)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File too large. Maximum size is 10MB.")

    from backend.services.cv_parser import parse_cv

    result = await parse_cv(content)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not parse CV. Ensure the PDF contains extractable text.",
        )

    # Save CV file if requested
    cv_path = None
    if save_file:
        # Create uploads directory if it doesn't exist
        uploads_dir = os.path.join(os.getcwd(), "uploads", "cvs")
        os.makedirs(uploads_dir, exist_ok=True)

        # Generate unique filename
        file_ext = os.path.splitext(file.filename)[1] if file.filename else ".pdf"
        unique_filename = f"{current_user.id}_{uuid_lib.uuid4()}{file_ext}"
        cv_path = os.path.join(uploads_dir, unique_filename)

        # Write file
        with open(cv_path, "wb") as f:
            f.write(content)

        # Update user record with CV path
        current_user.cv_path = cv_path
        await db.flush()

    # Trigger profile analysis workflow if requested
    if trigger_analysis:
        from backend.tasks.profile_analysis import analyze_user_profile

        analyze_user_profile.delay(str(current_user.id))

    return ImportPreviewResponse(
        name=result.get("name"),
        institution=result.get("institution"),
        research_areas=result.get("research_areas", []),
        methods=result.get("methods", []),
        publications=result.get("publications", []),
        past_grants=result.get("past_grants", []),
        career_stage=result.get("career_stage"),
        keywords=[],
        orcid=None,
        source="cv",
    )


class ProfileAnalysisStatus(BaseModel):
    """Status of profile analysis."""

    status: str = Field(..., description="Status: pending, in_progress, completed, failed")
    started_at: Optional[str] = Field(None, description="When analysis started")
    completed_at: Optional[str] = Field(None, description="When analysis completed")
    lab_details: Optional[dict] = Field(None, description="Analyzed lab details")
    current_funding: Optional[dict] = Field(None, description="Current funding info")
    publications: Optional[dict] = Field(None, description="Publications info")


@router.get(
    "/analysis/status",
    response_model=ProfileAnalysisStatus,
    summary="Get profile analysis status",
    description="Check the status of the user's profile analysis.",
)
async def get_analysis_status(
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> ProfileAnalysisStatus:
    """Get the status of the user's profile analysis workflow."""
    result = await db.execute(select(LabProfile).where(LabProfile.user_id == current_user.id))
    profile = result.scalar_one_or_none()

    if not profile:
        return ProfileAnalysisStatus(status="no_profile")

    return ProfileAnalysisStatus(
        status=profile.analysis_status or "not_started",
        started_at=profile.analysis_started_at.isoformat() if profile.analysis_started_at else None,
        completed_at=profile.analysis_completed_at.isoformat() if profile.analysis_completed_at else None,
        lab_details=profile.lab_details,
        current_funding=profile.current_funding,
        publications=profile.publications,
    )


@router.post(
    "/analysis/trigger",
    summary="Trigger profile analysis",
    description="Manually trigger profile analysis for the current user.",
)
async def trigger_analysis(
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> dict:
    """
    Trigger profile analysis workflow.

    Analyzes the user's profile to gather:
    - Publications from web sources
    - Past and current funding
    - Lab details and team info
    - Research focus areas
    """
    # Get or create profile
    result = await db.execute(select(LabProfile).where(LabProfile.user_id == current_user.id))
    profile = result.scalar_one_or_none()

    if not profile:
        # Create a basic profile to store analysis results
        profile = LabProfile(
            user_id=current_user.id,
            analysis_status="pending",
        )
        db.add(profile)
        await db.flush()
    else:
        profile.analysis_status = "pending"
        await db.flush()

    # Trigger Celery task
    from backend.tasks.profile_analysis import analyze_user_profile

    task = analyze_user_profile.delay(str(current_user.id))

    return {"message": "Profile analysis started", "task_id": task.id, "status": "pending"}
