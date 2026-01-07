"""
GrantRadar API Routers
FastAPI router modules for the grant intelligence platform.
"""
from backend.api import auth, grants, matches, preferences, profile, stats

__all__ = [
    "auth",
    "grants",
    "matches",
    "preferences",
    "profile",
    "stats",
]
