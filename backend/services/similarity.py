"""
Similarity Service for GrantRadar
Calculate grant similarity using algorithmic methods (no AI).
"""
import re
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Grant


# Common words to exclude from keyword matching
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "he",
    "in", "is", "it", "its", "of", "on", "or", "that", "the", "to", "was", "were",
    "will", "with", "grant", "funding", "research", "program", "project", "award",
    "application", "applicant", "applicants", "support", "opportunity", "opportunities"
}

# Minimum word length for keyword extraction
MIN_WORD_LENGTH = 3


@dataclass
class SimilarityResult:
    """Result of similarity calculation between two grants."""
    grant: Grant
    similarity_score: float
    similarity_reasons: list[str]


def extract_keywords(text: str) -> set[str]:
    """
    Extract significant keywords from text.

    Removes common words, short words, and normalizes to lowercase.
    """
    if not text:
        return set()

    # Normalize text
    text = text.lower()

    # Extract words (alphanumeric only)
    words = re.findall(r'\b[a-z]+\b', text)

    # Filter out stop words and short words
    keywords = {
        word for word in words
        if word not in STOP_WORDS and len(word) >= MIN_WORD_LENGTH
    }

    return keywords


def calculate_jaccard_similarity(set1: set, set2: set) -> float:
    """
    Calculate Jaccard similarity coefficient between two sets.

    Returns a value between 0.0 (no overlap) and 1.0 (identical).
    """
    if not set1 or not set2:
        return 0.0

    intersection = len(set1 & set2)
    union = len(set1 | set2)

    if union == 0:
        return 0.0

    return intersection / union


def calculate_funding_similarity(
    amount_min1: Optional[int],
    amount_max1: Optional[int],
    amount_min2: Optional[int],
    amount_max2: Optional[int],
) -> float:
    """
    Calculate funding range similarity.

    Uses overlap ratio of funding ranges. Returns 1.0 for identical ranges,
    0.0 for completely disjoint ranges.
    """
    # Get effective amounts (use min as max if max is None, vice versa)
    min1 = amount_min1 or amount_max1 or 0
    max1 = amount_max1 or amount_min1 or 0
    min2 = amount_min2 or amount_max2 or 0
    max2 = amount_max2 or amount_min2 or 0

    # If either grant has no funding info, return neutral score
    if max1 == 0 or max2 == 0:
        return 0.5

    # Ensure min <= max
    if min1 > max1:
        min1, max1 = max1, min1
    if min2 > max2:
        min2, max2 = max2, min2

    # Calculate overlap
    overlap_start = max(min1, min2)
    overlap_end = min(max1, max2)

    if overlap_start > overlap_end:
        # No overlap - calculate distance-based similarity
        distance = overlap_start - overlap_end
        max_range = max(max1, max2)
        if max_range == 0:
            return 0.0
        # Decay similarity based on distance
        return max(0.0, 1.0 - (distance / max_range))

    # Calculate overlap ratio
    overlap = overlap_end - overlap_start
    total_range = max(max1, max2) - min(min1, min2)

    if total_range == 0:
        return 1.0 if overlap == 0 else 0.0

    return overlap / total_range


def calculate_agency_similarity(agency1: Optional[str], agency2: Optional[str]) -> float:
    """
    Calculate agency similarity.

    Returns:
    - 1.0 for exact match (case-insensitive)
    - 0.5 for same agency type (e.g., both NIH institutes)
    - 0.0 for different agencies
    """
    if not agency1 or not agency2:
        return 0.0

    agency1_lower = agency1.lower().strip()
    agency2_lower = agency2.lower().strip()

    # Exact match
    if agency1_lower == agency2_lower:
        return 1.0

    # Check for same parent agency
    # NIH institutes
    nih_keywords = ["nih", "national institute", "national center for"]
    if any(kw in agency1_lower for kw in nih_keywords) and any(kw in agency2_lower for kw in nih_keywords):
        return 0.5

    # NSF directorates
    if "nsf" in agency1_lower and "nsf" in agency2_lower:
        return 0.5

    # DOE offices
    if "energy" in agency1_lower and "energy" in agency2_lower:
        return 0.5

    # Same department
    common_depts = ["health", "defense", "education", "agriculture", "commerce"]
    for dept in common_depts:
        if dept in agency1_lower and dept in agency2_lower:
            return 0.3

    return 0.0


def calculate_similarity(
    source_grant: Grant,
    candidate_grant: Grant,
) -> SimilarityResult:
    """
    Calculate overall similarity between two grants.

    Weights:
    - Category overlap: 40%
    - Agency match: 25%
    - Funding range: 20%
    - Title keywords: 15%

    Returns a SimilarityResult with score (0-100) and reasons.
    """
    reasons = []

    # 1. Category/Focus area overlap (40% weight)
    source_categories = set(source_grant.categories or [])
    candidate_categories = set(candidate_grant.categories or [])
    category_score = calculate_jaccard_similarity(source_categories, candidate_categories)

    if category_score >= 0.5:
        common = source_categories & candidate_categories
        if common:
            reasons.append(f"Related Topics: {', '.join(list(common)[:3])}")
    elif category_score > 0:
        reasons.append("Similar Research Areas")

    # 2. Agency similarity (25% weight)
    agency_score = calculate_agency_similarity(source_grant.agency, candidate_grant.agency)

    if agency_score == 1.0:
        reasons.append("Same Agency")
    elif agency_score >= 0.5:
        reasons.append("Same Agency Family")
    elif agency_score > 0:
        reasons.append("Related Department")

    # 3. Funding range similarity (20% weight)
    funding_score = calculate_funding_similarity(
        source_grant.amount_min,
        source_grant.amount_max,
        candidate_grant.amount_min,
        candidate_grant.amount_max,
    )

    if funding_score >= 0.7:
        reasons.append("Similar Funding")

    # 4. Title keyword similarity (15% weight)
    source_keywords = extract_keywords(source_grant.title)
    candidate_keywords = extract_keywords(candidate_grant.title)
    keyword_score = calculate_jaccard_similarity(source_keywords, candidate_keywords)

    if keyword_score >= 0.3:
        common_keywords = source_keywords & candidate_keywords
        if common_keywords:
            reasons.append(f"Keywords: {', '.join(list(common_keywords)[:2])}")

    # Calculate weighted total score
    total_score = (
        category_score * 0.40 +
        agency_score * 0.25 +
        funding_score * 0.20 +
        keyword_score * 0.15
    )

    # Convert to 0-100 scale
    similarity_percentage = round(total_score * 100)

    # If no specific reasons found but score is decent, add generic reason
    if not reasons and similarity_percentage >= 30:
        reasons.append("General Similarity")

    return SimilarityResult(
        grant=candidate_grant,
        similarity_score=similarity_percentage,
        similarity_reasons=reasons,
    )


async def find_similar_grants(
    db: AsyncSession,
    grant_id: UUID,
    limit: int = 10,
    min_score: int = 20,
) -> list[SimilarityResult]:
    """
    Find grants similar to the given grant.

    Uses a two-phase approach:
    1. Pre-filter candidates using database queries (same agency, overlapping categories)
    2. Calculate detailed similarity scores for candidates

    Args:
        db: Database session
        grant_id: ID of the source grant
        limit: Maximum number of similar grants to return
        min_score: Minimum similarity score (0-100) to include

    Returns:
        List of SimilarityResult objects, sorted by similarity score descending
    """
    # Fetch the source grant
    result = await db.execute(
        select(Grant).where(Grant.id == grant_id)
    )
    source_grant = result.scalar_one_or_none()

    if not source_grant:
        return []

    # Build query to find candidate grants
    # Pre-filter to reduce computation
    filters = [Grant.id != grant_id]  # Exclude the source grant

    # Build OR conditions for pre-filtering
    or_conditions = []

    # Same agency
    if source_grant.agency:
        or_conditions.append(Grant.agency == source_grant.agency)

    # Overlapping categories
    if source_grant.categories:
        for category in source_grant.categories:
            or_conditions.append(Grant.categories.contains([category]))

    # Similar funding range (within 2x)
    if source_grant.amount_max:
        or_conditions.append(
            and_(
                Grant.amount_min >= source_grant.amount_max * 0.5,
                Grant.amount_min <= source_grant.amount_max * 2
            )
        )
    elif source_grant.amount_min:
        or_conditions.append(
            and_(
                Grant.amount_max >= source_grant.amount_min * 0.5,
                Grant.amount_max <= source_grant.amount_min * 2
            )
        )

    # Same source (nih, nsf, grants_gov)
    or_conditions.append(Grant.source == source_grant.source)

    # Apply OR conditions if any
    if or_conditions:
        filters.append(or_(*or_conditions))

    # Execute query to get candidates (limit to reasonable number for scoring)
    query = select(Grant).where(and_(*filters)).limit(100)
    result = await db.execute(query)
    candidates = result.scalars().all()

    # Calculate similarity scores for all candidates
    similarity_results = []
    for candidate in candidates:
        result = calculate_similarity(source_grant, candidate)
        if result.similarity_score >= min_score:
            similarity_results.append(result)

    # Sort by similarity score (descending) and return top N
    similarity_results.sort(key=lambda x: x.similarity_score, reverse=True)

    return similarity_results[:limit]
