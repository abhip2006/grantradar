"""
Schemas for the Grant Winners Intelligence API.
Provides access to 2.6M+ funded NIH/NSF projects for pattern analysis.
"""

from typing import Optional

from pydantic import BaseModel, Field


# =============================================================================
# Core Data Models
# =============================================================================


class FundedProjectPI(BaseModel):
    """Principal investigator information for a funded project."""

    name: Optional[str] = Field(None, description="Full name of PI")
    email: Optional[str] = Field(None, description="PI email address")
    profile_id: Optional[int] = Field(None, description="NIH profile ID")


class FundedProjectOrg(BaseModel):
    """Organization/institution information for a funded project."""

    name: Optional[str] = Field(None, description="Organization name")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State abbreviation")
    country: Optional[str] = Field(None, description="Country")


class FundedProject(BaseModel):
    """A funded grant project from NIH or NSF."""

    project_num: str = Field(..., description="Unique project identifier")
    title: str = Field(..., description="Project title")
    abstract: Optional[str] = Field(None, description="Project abstract")

    # Funding details
    award_amount: Optional[int] = Field(None, description="Award amount in dollars")
    activity_code: Optional[str] = Field(None, description="Activity code (R01, R21, etc.)")
    mechanism: Optional[str] = Field(None, description="Funding mechanism")

    # Agency
    agency: str = Field(default="NIH", description="Funding agency (NIH, NSF)")
    institute: Optional[str] = Field(None, description="NIH institute abbreviation (NCI, NIMH)")
    institute_name: Optional[str] = Field(None, description="Full institute name")

    # Timeline
    fiscal_year: Optional[int] = Field(None, description="Fiscal year of award")
    start_date: Optional[str] = Field(None, description="Project start date (ISO format)")
    end_date: Optional[str] = Field(None, description="Project end date (ISO format)")
    award_date: Optional[str] = Field(None, description="Award notice date (ISO format)")

    # People and organizations
    principal_investigator: Optional[FundedProjectPI] = Field(None, description="Primary PI information")
    organization: Optional[FundedProjectOrg] = Field(None, description="Awardee organization")
    program_officer: Optional[str] = Field(None, description="NIH Program Officer name")

    # Keywords
    terms: Optional[str] = Field(None, description="Keywords/terms associated with project")

    # URLs
    source_url: Optional[str] = Field(None, description="Link to NIH Reporter or NSF page")


# =============================================================================
# Search Request/Response
# =============================================================================


class WinnersSearchRequest(BaseModel):
    """Search request for funded projects."""

    query: Optional[str] = Field(None, description="Keyword search in abstracts and titles")
    research_area: Optional[str] = Field(None, description="Research area for semantic search")
    activity_codes: Optional[list[str]] = Field(None, description="Activity codes to filter (R01, R21, K08, etc.)")
    agency: Optional[str] = Field(None, description="Filter by agency (NIH, NSF)")
    institute: Optional[str] = Field(None, description="NIH institute abbreviation (NCI, NIMH)")
    fiscal_years: Optional[list[int]] = Field(None, description="Fiscal years to include")
    institution: Optional[str] = Field(None, description="Search by institution name")
    pi_name: Optional[str] = Field(None, description="Search by PI name")
    state: Optional[str] = Field(None, description="Filter by state")
    min_amount: Optional[int] = Field(None, ge=0, description="Minimum award amount")
    max_amount: Optional[int] = Field(None, description="Maximum award amount")
    page: int = Field(default=1, ge=1, description="Page number")
    limit: int = Field(default=20, ge=1, le=100, description="Results per page")


class YearAggregation(BaseModel):
    """Aggregation by fiscal year."""

    year: int = Field(..., description="Fiscal year")
    count: int = Field(..., description="Number of projects")
    total_funding: int = Field(default=0, description="Total funding amount")


class MechanismAggregation(BaseModel):
    """Aggregation by activity code/mechanism."""

    code: str = Field(..., description="Activity code (R01, R21, etc.)")
    count: int = Field(..., description="Number of projects")
    avg_award: Optional[int] = Field(None, description="Average award amount")


class InstituteAggregation(BaseModel):
    """Aggregation by NIH institute."""

    abbreviation: str = Field(..., description="Institute abbreviation (NCI, NIMH)")
    name: Optional[str] = Field(None, description="Full institute name")
    count: int = Field(..., description="Number of projects")


class SearchAggregations(BaseModel):
    """Aggregations for search results."""

    by_year: list[YearAggregation] = Field(default_factory=list, description="Projects by fiscal year")
    by_mechanism: list[MechanismAggregation] = Field(default_factory=list, description="Projects by activity code")
    by_institute: list[InstituteAggregation] = Field(default_factory=list, description="Projects by NIH institute")


class WinnersSearchResponse(BaseModel):
    """Response from funded projects search."""

    results: list[FundedProject] = Field(default_factory=list, description="Matching funded projects")
    total: int = Field(..., description="Total matching projects")
    page: int = Field(..., description="Current page number")
    pages: int = Field(..., description="Total number of pages")
    aggregations: SearchAggregations = Field(default_factory=SearchAggregations, description="Result aggregations")


# =============================================================================
# Program Officer Models
# =============================================================================


class ProgramOfficerProject(BaseModel):
    """Simplified project for program officer listings."""

    project_num: str = Field(..., description="Project number")
    title: str = Field(..., description="Project title")
    award_amount: Optional[int] = Field(None, description="Award amount")
    fiscal_year: Optional[int] = Field(None, description="Fiscal year")
    activity_code: Optional[str] = Field(None, description="Activity code")


class ProgramOfficer(BaseModel):
    """Program officer with funding patterns."""

    name: str = Field(..., description="Program officer name")
    email: Optional[str] = Field(None, description="Email address")
    institute: str = Field(..., description="NIH institute abbreviation")
    institute_name: Optional[str] = Field(None, description="Full institute name")

    # Funding stats
    total_projects: int = Field(..., description="Total projects funded")
    total_funding: int = Field(default=0, description="Total funding amount")
    avg_award_size: Optional[int] = Field(None, description="Average award size")

    # Patterns
    top_mechanisms: list[str] = Field(default_factory=list, description="Most common activity codes")
    research_themes: list[str] = Field(default_factory=list, description="Inferred research themes from abstracts")

    # Recent activity
    recent_projects: list[ProgramOfficerProject] = Field(default_factory=list, description="Recent funded projects")


class ProgramOfficersResponse(BaseModel):
    """Response with program officer directory."""

    officers: list[ProgramOfficer] = Field(default_factory=list, description="Program officers matching criteria")
    total: int = Field(..., description="Total matching officers")


# =============================================================================
# Institution Analytics Models
# =============================================================================


class InstitutionStats(BaseModel):
    """Institution success metrics."""

    name: str = Field(..., description="Institution name")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State")

    # Funding metrics
    total_awards: int = Field(..., description="Total number of awards")
    total_funding: int = Field(default=0, description="Total funding received")
    avg_award_size: Optional[int] = Field(None, description="Average award size")

    # Breakdown
    top_mechanisms: list[str] = Field(default_factory=list, description="Most successful activity codes")
    top_pis: list[str] = Field(default_factory=list, description="Top principal investigators")

    # Success metrics
    rank: Optional[int] = Field(None, description="Ranking within results")


class InstitutionsResponse(BaseModel):
    """Response with institution analytics."""

    institutions: list[InstitutionStats] = Field(default_factory=list, description="Institution statistics")
    total: int = Field(..., description="Total institutions in dataset")


# =============================================================================
# Keyword Analysis Models
# =============================================================================


class KeywordItem(BaseModel):
    """Individual keyword with statistics."""

    keyword: str = Field(..., description="The keyword or phrase")
    frequency: int = Field(..., description="Number of occurrences")
    percentage: float = Field(..., ge=0, le=100, description="Percentage of projects containing this keyword")
    trending: Optional[str] = Field(None, description="Trend direction: 'up', 'down', 'stable'")


class KeywordCluster(BaseModel):
    """Cluster of related keywords."""

    theme: str = Field(..., description="Theme or topic name")
    keywords: list[str] = Field(default_factory=list, description="Keywords in this cluster")
    project_count: int = Field(..., description="Projects matching this cluster")


class ProfileKeywordComparison(BaseModel):
    """Comparison of user's profile keywords vs. successful grants."""

    matching_keywords: list[str] = Field(
        default_factory=list, description="Keywords present in both profile and successful grants"
    )
    missing_keywords: list[str] = Field(
        default_factory=list, description="High-frequency keywords missing from profile"
    )
    match_score: float = Field(..., ge=0, le=100, description="Overall keyword alignment score")


class KeywordAnalysisRequest(BaseModel):
    """Request for keyword analysis."""

    mechanism: Optional[str] = Field(None, description="Activity code to analyze (R01, R21)")
    institute: Optional[str] = Field(None, description="NIH institute to focus on")
    fiscal_years: Optional[list[int]] = Field(None, description="Years to analyze")
    compare_to_profile: bool = Field(default=False, description="Compare against user's research profile")
    top_n: int = Field(default=50, ge=10, le=200, description="Number of keywords to return")


class KeywordAnalysisResponse(BaseModel):
    """Response with keyword analysis."""

    top_keywords: list[KeywordItem] = Field(default_factory=list, description="Most frequent keywords")
    keyword_clusters: list[KeywordCluster] = Field(default_factory=list, description="Grouped keyword themes")
    profile_comparison: Optional[ProfileKeywordComparison] = Field(
        None, description="Comparison with user profile (if requested)"
    )
    projects_analyzed: int = Field(..., description="Number of projects in analysis")


# =============================================================================
# Abstract Pattern Analysis Models (AI-Powered)
# =============================================================================


class AbstractPattern(BaseModel):
    """Pattern found in successful abstracts."""

    pattern_type: str = Field(..., description="Type of pattern (structure, language, approach)")
    description: str = Field(..., description="Description of the pattern")
    examples: list[str] = Field(default_factory=list, description="Example phrases or structures")
    frequency: float = Field(..., ge=0, le=100, description="Percentage of abstracts using this pattern")


class LanguageInsights(BaseModel):
    """Insights about language usage in successful abstracts."""

    avg_length: int = Field(..., description="Average abstract length in words")
    avg_sentences: int = Field(..., description="Average number of sentences")
    key_phrases: list[str] = Field(default_factory=list, description="Common impactful phrases")
    action_verbs: list[str] = Field(default_factory=list, description="Frequently used action verbs")
    avoided_phrases: list[str] = Field(default_factory=list, description="Phrases rarely seen in successful abstracts")


class UserAbstractComparison(BaseModel):
    """Comparison of user's abstract against patterns."""

    strengths: list[str] = Field(default_factory=list, description="Strong aspects of the abstract")
    gaps: list[str] = Field(default_factory=list, description="Missing elements or weaknesses")
    similarity_score: float = Field(..., ge=0, le=100, description="Similarity to successful abstracts")
    suggestions: list[str] = Field(default_factory=list, description="Specific improvement suggestions")


class AbstractAnalysisRequest(BaseModel):
    """Request for abstract pattern analysis."""

    mechanism: str = Field(..., description="Activity code to analyze (R01, R21)")
    institute: Optional[str] = Field(None, description="NIH institute to focus on")
    fiscal_years: Optional[list[int]] = Field(None, description="Years to analyze")
    user_abstract: Optional[str] = Field(None, description="User's draft abstract for comparison")


class AbstractAnalysisResponse(BaseModel):
    """Response with AI-powered abstract analysis."""

    common_patterns: list[AbstractPattern] = Field(
        default_factory=list, description="Common patterns in successful abstracts"
    )
    language_insights: LanguageInsights = Field(..., description="Language usage insights")
    recommendations: list[str] = Field(default_factory=list, description="General recommendations")
    user_comparison: Optional[UserAbstractComparison] = Field(
        None, description="Comparison with user's abstract (if provided)"
    )
    abstracts_analyzed: int = Field(..., description="Number of abstracts in analysis")


# =============================================================================
# Success Prediction Models
# =============================================================================


class PredictionFactor(BaseModel):
    """Factor contributing to success prediction."""

    factor: str = Field(..., description="Factor name")
    impact: str = Field(..., description="Impact level: positive, negative, neutral")
    weight: float = Field(..., ge=0, le=1, description="Weight in prediction (0-1)")
    explanation: str = Field(..., description="Explanation of this factor's role")


class SuccessPredictionRequest(BaseModel):
    """Request for success probability prediction."""

    mechanism: str = Field(..., description="Target activity code (R01, R21)")
    institute: str = Field(..., description="Target NIH institute")
    research_area: str = Field(..., description="Research area description")
    keywords: list[str] = Field(default_factory=list, description="Key terms from proposal")
    institution: Optional[str] = Field(None, description="Applicant institution name")
    draft_abstract: Optional[str] = Field(None, description="Draft abstract for analysis")
    pi_previous_awards: int = Field(default=0, ge=0, description="Number of previous awards held by PI")


class SuccessPredictionResponse(BaseModel):
    """Response with success probability prediction."""

    probability: float = Field(..., ge=0, le=100, description="Predicted success probability (0-100%)")
    confidence: str = Field(..., description="Confidence level: low, medium, high")
    factors: list[PredictionFactor] = Field(default_factory=list, description="Factors contributing to prediction")
    similar_funded: list[FundedProject] = Field(default_factory=list, description="Similar projects that were funded")
    recommendations: list[str] = Field(default_factory=list, description="Recommendations to improve chances")
    historical_rate: Optional[float] = Field(None, description="Historical success rate for this mechanism/institute")
