"""
Profile schemas for lab profile management and onboarding.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class LabProfileCreate(BaseModel):
    """Schema for creating a new lab profile."""

    research_areas: list[str] = Field(..., min_length=1, max_length=20, description="Primary research areas/topics")
    methods: Optional[list[str]] = Field(None, max_length=20, description="Research methodologies")
    career_stage: Optional[str] = Field(
        None, pattern="^(early_career|mid_career|established|senior)$", description="Career stage"
    )
    citizenship_status: Optional[str] = Field(
        None,
        pattern="^(us_citizen|permanent_resident|visa_holder|international)$",
        description="Citizenship/visa status for eligibility filtering",
    )
    institution_type: Optional[str] = Field(
        None,
        pattern="^(r1_university|r2_university|liberal_arts|community_college|nonprofit|industry|government|hbcu|msi|other)$",
        description="Type of institution",
    )
    is_pi_eligible: Optional[bool] = Field(False, description="Whether user is eligible to be a Principal Investigator")
    past_grants: Optional[dict[str, Any]] = Field(None, description="Historical grant awards")
    publications: Optional[dict[str, Any]] = Field(None, description="Publication history")
    orcid: Optional[str] = Field(None, pattern="^\\d{4}-\\d{4}-\\d{4}-\\d{3}[0-9X]$", description="ORCID identifier")


class LabProfileUpdate(BaseModel):
    """Schema for updating an existing lab profile."""

    research_areas: Optional[list[str]] = Field(None, max_length=20, description="Primary research areas")
    methods: Optional[list[str]] = Field(None, max_length=20, description="Research methodologies")
    career_stage: Optional[str] = Field(
        None, pattern="^(early_career|mid_career|established|senior)$", description="Career stage"
    )
    citizenship_status: Optional[str] = Field(
        None,
        pattern="^(us_citizen|permanent_resident|visa_holder|international)$",
        description="Citizenship/visa status for eligibility filtering",
    )
    institution_type: Optional[str] = Field(
        None,
        pattern="^(r1_university|r2_university|liberal_arts|community_college|nonprofit|industry|government|hbcu|msi|other)$",
        description="Type of institution",
    )
    is_pi_eligible: Optional[bool] = Field(None, description="Whether user is eligible to be a Principal Investigator")
    past_grants: Optional[dict[str, Any]] = Field(None, description="Historical grant awards")
    publications: Optional[dict[str, Any]] = Field(None, description="Publication history")
    orcid: Optional[str] = Field(None, pattern="^\\d{4}-\\d{4}-\\d{4}-\\d{3}[0-9X]$", description="ORCID identifier")


class LabProfileResponse(BaseModel):
    """Schema for lab profile response."""

    id: UUID = Field(..., description="Profile ID")
    user_id: UUID = Field(..., description="User ID")
    research_areas: Optional[list[str]] = Field(None, description="Research areas")
    methods: Optional[list[str]] = Field(None, description="Methods")
    career_stage: Optional[str] = Field(None, description="Career stage")
    citizenship_status: Optional[str] = Field(None, description="Citizenship/visa status")
    institution_type: Optional[str] = Field(None, description="Type of institution")
    is_pi_eligible: bool = Field(default=False, description="Whether user is PI eligible")
    past_grants: Optional[dict[str, Any]] = Field(None, description="Past grants")
    publications: Optional[dict[str, Any]] = Field(None, description="Publications")
    orcid: Optional[str] = Field(None, description="ORCID")
    has_embedding: bool = Field(default=False, description="Whether embedding exists")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True


class OnboardingData(BaseModel):
    """Schema for complete onboarding data submission."""

    # User info updates
    name: Optional[str] = Field(None, description="User's full name")
    institution: Optional[str] = Field(None, description="Institution")
    phone: Optional[str] = Field(None, description="Phone for SMS alerts")

    # Profile data
    research_areas: list[str] = Field(..., min_length=1, max_length=20, description="Research areas")
    methods: Optional[list[str]] = Field(None, description="Methods")
    career_stage: Optional[str] = Field(None, pattern="^(early_career|mid_career|established|senior)$")
    citizenship_status: Optional[str] = Field(
        None,
        pattern="^(us_citizen|permanent_resident|visa_holder|international)$",
        description="Citizenship/visa status for eligibility filtering",
    )
    institution_type: Optional[str] = Field(
        None,
        pattern="^(r1_university|r2_university|liberal_arts|community_college|nonprofit|industry|government|hbcu|msi|other)$",
        description="Type of institution",
    )
    is_pi_eligible: Optional[bool] = Field(False, description="Whether user is eligible to be a Principal Investigator")
    past_grants: Optional[dict[str, Any]] = Field(None, description="Past grants")
    publications: Optional[dict[str, Any]] = Field(None, description="Publications")
    orcid: Optional[str] = Field(None, pattern="^\\d{4}-\\d{4}-\\d{4}-\\d{3}[0-9X]$")

    # Preferences
    notification_preferences: Optional[dict[str, bool]] = Field(None, description="Email/SMS notification preferences")
