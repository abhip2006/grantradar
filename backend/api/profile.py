"""
Profile API Endpoints
Manage user lab profiles and onboarding.
"""
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.models import LabProfile, User
from backend.schemas.profile import (
    LabProfileCreate,
    LabProfileResponse,
    LabProfileUpdate,
    OnboardingData,
)

router = APIRouter(prefix="/api/profile", tags=["Profile"])


@router.get(
    "",
    response_model=LabProfileResponse,
    summary="Get user profile",
    description="Get the current user's lab profile."
)
async def get_profile(
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> LabProfileResponse:
    """
    Get the lab profile for the authenticated user.

    Returns 404 if no profile exists yet.
    """
    result = await db.execute(
        select(LabProfile).where(LabProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Complete onboarding to create a profile."
        )

    return LabProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        research_areas=profile.research_areas,
        methods=profile.methods,
        career_stage=profile.career_stage,
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
    description="Update the current user's lab profile. Triggers re-embedding."
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
    result = await db.execute(
        select(LabProfile).where(LabProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Complete onboarding to create a profile."
        )

    # Track if embedding-relevant fields changed
    needs_reembedding = False
    embedding_fields = ['research_areas', 'methods', 'publications']

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
    description="Submit onboarding data to create user profile."
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
    result = await db.execute(
        select(LabProfile).where(LabProfile.user_id == current_user.id)
    )
    existing_profile = result.scalar_one_or_none()

    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile already exists. Use PUT /api/profile to update."
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
        past_grants=profile.past_grants,
        publications=profile.publications,
        orcid=profile.orcid,
        has_embedding=False,  # Will be computed async
        created_at=profile.created_at,
    )
