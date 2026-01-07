"""
GrantRadar API Routers
FastAPI router modules for the grant intelligence platform.
"""
from backend.api import auth, compare, grants, matches, preferences, profile, stats

__all__ = [
    "auth",
    "compare",
    "grants",
    "matches",
    "preferences",
    "profile",
    "stats",
]
