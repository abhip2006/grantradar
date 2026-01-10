"""Writing assistant schemas."""

from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional, List, Dict
from enum import Enum


class FundingAgency(str, Enum):
    """Supported funding agencies."""

    NIH = "NIH"
    NSF = "NSF"
    DOE = "DOE"
    DOD = "DOD"
    OTHER = "OTHER"


class CriterionCategory(str, Enum):
    """Categories of review criteria."""

    SCIENTIFIC_MERIT = "scientific_merit"
    INNOVATION = "innovation"
    FEASIBILITY = "feasibility"
    IMPACT = "impact"
    TEAM = "team"
    RESOURCES = "resources"


class ReviewCriterion(BaseModel):
    """Single review criterion definition."""

    name: str = Field(..., description="Name of the criterion")
    description: str = Field(..., description="Description of what reviewers look for")
    weight: float = Field(ge=0.0, le=1.0, description="Relative weight/importance (0.0-1.0)")
    category: CriterionCategory = Field(..., description="Category of the criterion")
    scoring_guidance: str = Field(..., description="Guidance on how this is scored")
    common_weaknesses: List[str] = Field(default_factory=list, description="Common weaknesses reviewers note")
    tips: List[str] = Field(default_factory=list, description="Tips for addressing this criterion")


class MechanismCriteria(BaseModel):
    """Review criteria for a specific grant mechanism."""

    mechanism_code: str = Field(..., description="Grant mechanism code (e.g., R01, CAREER)")
    mechanism_name: str = Field(..., description="Full name of the mechanism")
    funding_agency: FundingAgency = Field(..., description="Funding agency")
    criteria: List[ReviewCriterion] = Field(..., description="List of review criteria")
    overall_guidance: str = Field(..., description="Overall guidance for the mechanism")
    page_limits: Optional[Dict[str, int]] = Field(default=None, description="Page limits for sections")


class CriteriaRequest(BaseModel):
    """Request for review criteria by mechanism."""

    mechanism: str = Field(..., description="Grant mechanism code (e.g., R01, CAREER)")


class SectionScore(BaseModel):
    """Score for a specific review criterion."""

    criterion_name: str = Field(..., description="Name of the criterion being scored")
    score: float = Field(ge=0.0, le=10.0, description="Score out of 10")
    score_label: str = Field(..., description="Score label (e.g., 'Strong', 'Moderate', 'Weak')")
    coverage: float = Field(ge=0.0, le=1.0, description="How well the criterion is covered (0.0-1.0)")
    strengths: List[str] = Field(default_factory=list, description="Identified strengths")
    gaps: List[str] = Field(default_factory=list, description="Identified gaps or missing elements")
    suggestions: List[str] = Field(default_factory=list, description="Specific improvement suggestions")


class WritingAnalysis(BaseModel):
    """Analysis result for a draft section."""

    overall_score: float = Field(ge=0.0, le=10.0, description="Overall score out of 10")
    overall_label: str = Field(..., description="Overall score label")
    section_scores: List[SectionScore] = Field(..., description="Scores for each criterion")
    structure_feedback: str = Field(..., description="Feedback on overall structure")
    clarity_score: float = Field(ge=0.0, le=10.0, description="Clarity and readability score")
    completeness_score: float = Field(ge=0.0, le=10.0, description="Completeness score")
    word_count: int = Field(..., description="Word count of the analyzed text")
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


class AnalyzeRequest(BaseModel):
    """Request to analyze draft text against review criteria."""

    text: str = Field(..., min_length=50, description="Draft text to analyze")
    mechanism: str = Field(..., description="Grant mechanism code")
    section_type: Optional[str] = Field(
        default=None, description="Type of section (e.g., 'specific_aims', 'significance', 'approach')"
    )
    grant_id: Optional[UUID] = Field(default=None, description="Optional grant ID for context")


class AnalyzeResponse(BaseModel):
    """Response from text analysis."""

    analysis: WritingAnalysis
    criteria_used: List[str] = Field(..., description="List of criteria names used in analysis")
    recommendations: List[str] = Field(..., description="Top recommendations for improvement")


class FeedbackRequest(BaseModel):
    """Request for AI-powered feedback on a draft section."""

    text: str = Field(..., min_length=50, description="Draft text to get feedback on")
    mechanism: str = Field(..., description="Grant mechanism code")
    section_type: str = Field(..., description="Type of section")
    focus_areas: Optional[List[str]] = Field(default=None, description="Specific areas to focus feedback on")
    grant_id: Optional[UUID] = Field(default=None, description="Optional grant ID for context")


class FeedbackResponse(BaseModel):
    """AI-powered feedback response."""

    overall_assessment: str = Field(..., description="Overall assessment of the draft")
    criterion_feedback: Dict[str, str] = Field(..., description="Feedback mapped to each review criterion")
    structural_suggestions: List[str] = Field(
        default_factory=list, description="Suggestions for structural improvements"
    )
    content_gaps: List[str] = Field(default_factory=list, description="Missing content that should be addressed")
    specific_improvements: List[Dict[str, str]] = Field(
        default_factory=list, description="Specific text improvements with before/after suggestions"
    )
    strengths: List[str] = Field(default_factory=list, description="What's working well")
    priority_actions: List[str] = Field(default_factory=list, description="Top priority actions to improve the draft")
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class SuggestionType(str, Enum):
    """Types of writing suggestions."""

    ADD_CONTENT = "add_content"
    REMOVE_CONTENT = "remove_content"
    RESTRUCTURE = "restructure"
    CLARIFY = "clarify"
    STRENGTHEN = "strengthen"


class WritingSuggestion(BaseModel):
    """Individual writing suggestion."""

    type: SuggestionType
    criterion: str = Field(..., description="Related review criterion")
    priority: str = Field(..., description="high, medium, or low")
    description: str = Field(..., description="What should be changed")
    rationale: str = Field(..., description="Why this change would help")
    example: Optional[str] = Field(default=None, description="Example of improved text")


class SuggestionsRequest(BaseModel):
    """Request for improvement suggestions based on gaps."""

    text: str = Field(..., min_length=50, description="Draft text to analyze")
    mechanism: str = Field(..., description="Grant mechanism code")
    section_type: str = Field(..., description="Type of section")
    max_suggestions: int = Field(default=10, ge=1, le=20, description="Maximum suggestions to return")


class SuggestionsResponse(BaseModel):
    """Response with improvement suggestions."""

    suggestions: List[WritingSuggestion]
    gaps_identified: List[str] = Field(..., description="Gaps in coverage identified")
    criteria_coverage: Dict[str, float] = Field(..., description="Coverage score (0-1) for each criterion")
