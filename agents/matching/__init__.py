"""
Matching Agent Module
Grant-to-user profile matching using vector similarity and LLM re-ranking.
"""
from .matcher import (
    GrantMatcher,
    process_grant_matches,
    run_matching_consumer,
)
from .models import (
    BatchMatchRequest,
    BatchMatchResponse,
    FinalMatch,
    GrantData,
    MatchResult,
    ProfileEmbedding,
    ProfileMatch,
    UserProfile,
)
from .profile_builder import ProfileBuilder

__all__ = [
    # Matcher
    "GrantMatcher",
    "process_grant_matches",
    "run_matching_consumer",
    # Profile Builder
    "ProfileBuilder",
    # Models
    "BatchMatchRequest",
    "BatchMatchResponse",
    "FinalMatch",
    "GrantData",
    "MatchResult",
    "ProfileEmbedding",
    "ProfileMatch",
    "UserProfile",
]
