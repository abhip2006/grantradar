"""
Matching Agent Pydantic Models
Data models for the grant matching engine.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MatchResult(BaseModel):
    """
    Result of LLM-based match evaluation between a grant and user profile.

    Contains detailed scoring and reasoning for the match quality.
    """

    match_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Overall match score from 0-100",
    )
    reasoning: str = Field(
        ...,
        description="Detailed explanation of the match evaluation",
    )
    key_strengths: list[str] = Field(
        default_factory=list,
        description="Key strengths that make this a good match",
    )
    concerns: list[str] = Field(
        default_factory=list,
        description="Potential concerns or weaknesses in the match",
    )
    predicted_success: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Predicted success rate for the application (0-100)",
    )


class ProfileEmbedding(BaseModel):
    """
    User profile embedding for vector similarity matching.

    Generated from user onboarding data including research areas,
    methods, and past grants.
    """

    user_id: UUID = Field(..., description="User identifier")
    embedding: list[float] = Field(
        ...,
        description="Vector embedding from text-embedding-3-small (1536 dimensions)",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the embedding was generated",
    )
    source_text_hash: Optional[str] = Field(
        default=None,
        description="Hash of source text for cache invalidation",
    )


class UserProfile(BaseModel):
    """
    User profile data used for matching.

    Contains the profile information needed for embedding generation
    and LLM evaluation.
    """

    user_id: UUID = Field(..., description="User identifier")
    research_areas: list[str] = Field(
        default_factory=list,
        description="Primary research areas and disciplines",
    )
    methods: list[str] = Field(
        default_factory=list,
        description="Research methods and techniques used",
    )
    past_grants: list[str] = Field(
        default_factory=list,
        description="Summaries of past grant awards",
    )
    institution: Optional[str] = Field(
        default=None,
        description="Research institution name",
    )
    department: Optional[str] = Field(
        default=None,
        description="Department or lab name",
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Additional keywords describing expertise",
    )

    def to_embedding_text(self) -> str:
        """
        Generate text representation for embedding.

        Returns:
            Combined text of profile fields for embedding generation.
        """
        parts = []

        if self.research_areas:
            parts.append(f"Research areas: {', '.join(self.research_areas)}")

        if self.methods:
            parts.append(f"Methods: {', '.join(self.methods)}")

        if self.past_grants:
            parts.append(f"Past grants: {'; '.join(self.past_grants)}")

        if self.institution:
            parts.append(f"Institution: {self.institution}")

        if self.department:
            parts.append(f"Department: {self.department}")

        if self.keywords:
            parts.append(f"Keywords: {', '.join(self.keywords)}")

        return "\n".join(parts)


class GrantData(BaseModel):
    """
    Grant data used for matching.

    Subset of grant information needed for matching evaluation.
    """

    grant_id: UUID = Field(..., description="Grant identifier")
    title: str = Field(..., description="Grant title")
    description: str = Field(..., description="Grant description/abstract")
    funding_agency: Optional[str] = Field(
        default=None,
        description="Funding agency name",
    )
    funding_amount: Optional[float] = Field(
        default=None,
        description="Funding amount in USD",
    )
    deadline: Optional[datetime] = Field(
        default=None,
        description="Application deadline",
    )
    eligibility_criteria: list[str] = Field(
        default_factory=list,
        description="Eligibility requirements",
    )
    categories: list[str] = Field(
        default_factory=list,
        description="Grant categories",
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Grant keywords",
    )
    embedding: Optional[list[float]] = Field(
        default=None,
        description="Grant embedding vector",
    )

    def to_matching_text(self) -> str:
        """
        Generate text representation for LLM matching.

        Returns:
            Formatted grant information for LLM evaluation.
        """
        parts = [
            f"Title: {self.title}",
            f"Description: {self.description}",
        ]

        if self.funding_agency:
            parts.append(f"Funding Agency: {self.funding_agency}")

        if self.funding_amount:
            parts.append(f"Funding Amount: ${self.funding_amount:,.2f}")

        if self.deadline:
            parts.append(f"Deadline: {self.deadline.strftime('%Y-%m-%d')}")

        if self.eligibility_criteria:
            parts.append(f"Eligibility: {'; '.join(self.eligibility_criteria)}")

        if self.categories:
            parts.append(f"Categories: {', '.join(self.categories)}")

        if self.keywords:
            parts.append(f"Keywords: {', '.join(self.keywords)}")

        return "\n".join(parts)


class ProfileMatch(BaseModel):
    """
    Intermediate result combining vector similarity and profile data.

    Used for passing candidates to LLM re-ranking.
    """

    user_id: UUID = Field(..., description="User identifier")
    vector_similarity: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Cosine similarity score from pgvector (0-1)",
    )
    profile: UserProfile = Field(..., description="Full user profile data")


class BatchMatchRequest(BaseModel):
    """
    Request for batch LLM match evaluation.

    Groups multiple profiles with a single grant for efficient
    batched API calls.
    """

    grant: GrantData = Field(..., description="Grant to match against")
    profiles: list[ProfileMatch] = Field(
        ...,
        description="List of user profiles with their vector similarity scores",
        min_length=1,
        max_length=5,  # Optimal batch size for LLM calls
    )


class BatchMatchResponse(BaseModel):
    """
    Response from batch LLM match evaluation.

    Contains match results for all profiles in the batch.
    """

    grant_id: UUID = Field(..., description="Grant identifier")
    results: list[tuple[UUID, MatchResult]] = Field(
        ...,
        description="List of (user_id, match_result) tuples",
    )
    processing_time_ms: float = Field(
        ...,
        description="Time taken to process batch in milliseconds",
    )


class FinalMatch(BaseModel):
    """
    Final computed match ready for storage and publishing.

    Combines vector similarity and LLM scores with weighted average.
    """

    match_id: UUID = Field(..., description="Unique match identifier")
    grant_id: UUID = Field(..., description="Grant identifier")
    user_id: UUID = Field(..., description="User identifier")
    vector_similarity: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Cosine similarity score (0-1)",
    )
    llm_match_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="LLM match score (0-100)",
    )
    final_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Weighted final score: 40% vector + 60% LLM",
    )
    reasoning: str = Field(..., description="Match reasoning from LLM")
    key_strengths: list[str] = Field(
        default_factory=list,
        description="Key match strengths",
    )
    concerns: list[str] = Field(
        default_factory=list,
        description="Match concerns",
    )
    predicted_success: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Predicted application success rate",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the match was computed",
    )

    @classmethod
    def compute_final_score(
        cls,
        vector_similarity: float,
        llm_match_score: float,
    ) -> float:
        """
        Compute weighted final score.

        Formula: 40% vector similarity + 60% LLM match score

        Args:
            vector_similarity: Cosine similarity (0-1)
            llm_match_score: LLM match score (0-100)

        Returns:
            Weighted final score (0-100)
        """
        # Convert vector similarity to 0-100 scale
        vector_score = vector_similarity * 100

        # Weighted average: 40% vector + 60% LLM
        return (0.4 * vector_score) + (0.6 * llm_match_score)
