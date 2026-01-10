"""Specific Aims analysis schemas."""

from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional, List
from enum import Enum


class GrantMechanism(str, Enum):
    """Grant mechanism types for specific aims analysis."""

    R01 = "R01"
    R21 = "R21"
    R03 = "R03"
    K01 = "K01"
    K08 = "K08"
    K23 = "K23"
    K99 = "K99"
    F31 = "F31"
    F32 = "F32"
    CAREER = "CAREER"  # NSF CAREER
    OTHER = "OTHER"


class ScopeStatus(str, Enum):
    """Scope assessment status for an aim."""

    TOO_BROAD = "too_broad"
    TOO_NARROW = "too_narrow"
    APPROPRIATE = "appropriate"
    UNCLEAR = "unclear"


class IssueType(str, Enum):
    """Types of issues detected in specific aims."""

    CIRCULAR_LOGIC = "circular_logic"
    OVERLAPPING_AIMS = "overlapping_aims"
    MISSING_CONTROLS = "missing_controls"
    MISSING_HYPOTHESIS = "missing_hypothesis"
    INTERDEPENDENCY = "interdependency"
    VAGUE_LANGUAGE = "vague_language"
    FEASIBILITY_CONCERN = "feasibility_concern"
    METHODOLOGY_GAP = "methodology_gap"
    INNOVATION_UNCLEAR = "innovation_unclear"
    SIGNIFICANCE_WEAK = "significance_weak"


class IssueSeverity(str, Enum):
    """Severity level of detected issues."""

    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    SUGGESTION = "suggestion"


# -----------------------------------------------------------------------------
# Request Models
# -----------------------------------------------------------------------------


class AimsAnalysisRequest(BaseModel):
    """Request to analyze a specific aims page."""

    text: str = Field(..., min_length=50, description="Full text of the Specific Aims page")
    mechanism: GrantMechanism = Field(..., description="Grant mechanism type")
    research_area: Optional[str] = Field(None, description="Research area for context")
    additional_context: Optional[str] = Field(None, description="Any additional context")


class ScopeCheckRequest(BaseModel):
    """Request to check scope of a single aim."""

    aim_text: str = Field(..., min_length=20, description="Text of the specific aim")
    mechanism: GrantMechanism = Field(..., description="Grant mechanism type")
    aim_number: Optional[int] = Field(None, ge=1, le=5, description="Aim number (1-5)")


class CompareToFundedRequest(BaseModel):
    """Request to compare aims structure to funded applications."""

    aims_text: str = Field(..., min_length=50, description="Full text of the Specific Aims")
    mechanism: GrantMechanism = Field(..., description="Grant mechanism type")
    research_area: Optional[str] = Field(None, description="Research area for better matching")


# -----------------------------------------------------------------------------
# Response Models
# -----------------------------------------------------------------------------


class AimStructure(BaseModel):
    """Parsed structure of a single aim."""

    aim_number: int = Field(..., ge=1, le=5)
    aim_text: str
    hypothesis: Optional[str] = None
    approach_summary: Optional[str] = None
    expected_outcomes: Optional[str] = None
    word_count: int
    has_hypothesis: bool = False
    has_approach: bool = False
    has_expected_outcome: bool = False


class ScopeAssessment(BaseModel):
    """Scope assessment for a single aim."""

    aim_number: int
    status: ScopeStatus
    explanation: str
    confidence: float = Field(ge=0.0, le=1.0)
    suggestions: List[str]


class DetectedIssue(BaseModel):
    """A detected issue in the specific aims."""

    issue_type: IssueType
    severity: IssueSeverity
    description: str
    location: Optional[str] = Field(None, description="Where in the text the issue was found")
    suggestion: str


class ImprovementSuggestion(BaseModel):
    """A specific improvement suggestion."""

    category: str = Field(..., description="Category of improvement (structure, clarity, scope, etc.)")
    current_issue: str
    suggested_change: str
    priority: int = Field(..., ge=1, le=5, description="Priority 1-5 (1 is highest)")
    example_text: Optional[str] = Field(None, description="Example of improved text")


class MechanismGuidelines(BaseModel):
    """Guidelines for specific aims based on mechanism."""

    mechanism: GrantMechanism
    recommended_aims_count: int
    min_aims: int
    max_aims: int
    focus_areas: List[str]
    key_requirements: List[str]
    common_pitfalls: List[str]
    word_count_guidance: str
    typical_structure: List[str]


class AimsAnalysisResponse(BaseModel):
    """Full analysis response for specific aims."""

    # Overall assessment
    overall_score: float = Field(ge=0.0, le=100.0, description="Overall quality score 0-100")
    overall_assessment: str
    mechanism: GrantMechanism

    # Structure analysis
    detected_aims_count: int
    recommended_aims_count: int
    aims_structure: List[AimStructure]

    # Scope assessments
    scope_assessments: List[ScopeAssessment]

    # Issues detected
    issues: List[DetectedIssue]
    critical_issues_count: int
    major_issues_count: int

    # Improvements
    suggestions: List[ImprovementSuggestion]

    # Word count analysis
    total_word_count: int
    recommended_word_count_min: int = 400
    recommended_word_count_max: int = 550
    word_count_status: str  # "within_range", "too_short", "too_long"

    # Strengths
    strengths: List[str]

    # Mechanism-specific feedback
    mechanism_specific_feedback: str

    # Session for follow-up
    session_id: Optional[UUID] = None
    analyzed_at: datetime


class ScopeCheckResponse(BaseModel):
    """Response for single aim scope check."""

    aim_number: Optional[int]
    aim_text: str
    mechanism: GrantMechanism
    scope_status: ScopeStatus
    explanation: str
    confidence: float = Field(ge=0.0, le=1.0)
    suggestions: List[str]
    word_count: int
    recommended_scope_for_mechanism: str


class MechanismTemplateResponse(BaseModel):
    """Template structure for a specific mechanism."""

    mechanism: GrantMechanism
    guidelines: MechanismGuidelines
    template_sections: List[str]
    example_opening_hooks: List[str]
    example_hypothesis_formats: List[str]
    transition_phrases: List[str]
    strong_action_verbs: List[str]
    template_outline: str


class FundedExampleSummary(BaseModel):
    """Summary of a funded grant's aims structure."""

    mechanism: GrantMechanism
    research_area: str
    aims_count: int
    structure_summary: str
    key_features: List[str]
    hypothesis_style: str


class CompareToFundedResponse(BaseModel):
    """Response comparing aims to funded applications."""

    mechanism: GrantMechanism
    similarity_score: float = Field(ge=0.0, le=100.0)
    structure_comparison: str
    alignment_with_funded: List[str]
    deviations_from_funded: List[str]
    funded_examples: List[FundedExampleSummary]
    recommendations: List[str]


# -----------------------------------------------------------------------------
# Follow-up conversation models
# -----------------------------------------------------------------------------


class AimsFollowUpRequest(BaseModel):
    """Follow-up question about aims analysis."""

    session_id: UUID
    message: str


class AimsFollowUpResponse(BaseModel):
    """Response to follow-up question."""

    session_id: UUID
    response: str
    revised_suggestions: Optional[List[ImprovementSuggestion]] = None
