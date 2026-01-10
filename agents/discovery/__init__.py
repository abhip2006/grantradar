"""
Discovery Agents Module
Agents responsible for discovering grant opportunities from various sources.

Each agent inherits from DiscoveryAgent and implements source-specific
logic for fetching, normalizing, and publishing grant data.
"""

# Base class
from agents.discovery.base import DiscoveryAgent

# NIH Scraper
from agents.discovery.nih_scraper import (
    NIHFundingOpportunity,
    ScraperState,
    DiscoveredGrant as NIHDiscoveredGrant,
    scrape_nih_funding,
    run_nih_scraper,
    celery_app as nih_celery_app,
)

# NSF API Agent
from agents.discovery.nsf_api import (
    NSFDiscoveryAgent,
    NSFAward,
    NSFSearchParams,
    DiscoveredGrant,
    discover_nsf_grants,
)

# Grants.gov RSS Agent
from agents.discovery.grants_gov_rss import (
    GrantsGovRSSAgent,
    GrantsGovEntry,
    GrantsGovDetails,
    DiscoveredGrant as GrantsGovDiscoveredGrant,
    RateLimiter,
    discover_grants_gov,
    celery_app as grants_gov_celery_app,
)

__all__ = [
    # Base class
    "DiscoveryAgent",
    # NIH Scraper
    "NIHFundingOpportunity",
    "ScraperState",
    "NIHDiscoveredGrant",
    "scrape_nih_funding",
    "run_nih_scraper",
    "nih_celery_app",
    # NSF API Agent
    "NSFDiscoveryAgent",
    "NSFAward",
    "NSFSearchParams",
    "DiscoveredGrant",
    "discover_nsf_grants",
    # Grants.gov RSS Agent
    "GrantsGovRSSAgent",
    "GrantsGovEntry",
    "GrantsGovDetails",
    "GrantsGovDiscoveredGrant",
    "RateLimiter",
    "discover_grants_gov",
    "grants_gov_celery_app",
]
