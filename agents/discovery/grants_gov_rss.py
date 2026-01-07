"""
Grants.gov RSS Discovery Agent

Subscribes to Grants.gov RSS feed for new funding opportunities,
fetches full details via API, and publishes to Redis stream.
"""

import asyncio
import hashlib
import time
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

import feedparser
import httpx
import redis.asyncio as aioredis
import structlog
from celery import Celery
from pydantic import BaseModel, Field, field_validator
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from backend.core.config import settings

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger(__name__)

# ============================================================================
# Pydantic Models
# ============================================================================


class GrantsGovEntry(BaseModel):
    """Parsed RSS feed entry from Grants.gov."""

    opportunity_id: str = Field(..., description="Grants.gov opportunity ID")
    title: str = Field(..., description="Grant title")
    agency: str = Field(..., description="Funding agency name")
    close_date: Optional[datetime] = Field(None, description="Application deadline")
    link: str = Field(..., description="URL to the opportunity")
    posted_date: Optional[datetime] = Field(None, description="Date posted")
    description: Optional[str] = Field(None, description="Brief description")

    @field_validator("opportunity_id", mode="before")
    @classmethod
    def extract_opportunity_id(cls, v: str) -> str:
        """Clean opportunity ID if needed."""
        if v:
            return v.strip()
        return v


class GrantsGovDetails(BaseModel):
    """Full grant details from Grants.gov API."""

    opportunity_id: str = Field(..., alias="opportunityId")
    opportunity_number: Optional[str] = Field(None, alias="opportunityNumber")
    title: str = Field(..., alias="opportunityTitle")
    agency_code: Optional[str] = Field(None, alias="agencyCode")
    agency_name: Optional[str] = Field(None, alias="agencyName")
    opportunity_status: Optional[str] = Field(None, alias="oppStatus")
    posted_date: Optional[str] = Field(None, alias="postedDate")
    close_date: Optional[str] = Field(None, alias="closeDate")
    archive_date: Optional[str] = Field(None, alias="archiveDate")
    description: Optional[str] = Field(None, alias="description")
    cfda_numbers: Optional[list[str]] = Field(default_factory=list, alias="cfdaList")
    eligible_applicants: Optional[list[str]] = Field(
        default_factory=list, alias="eligibleApplicants"
    )
    funding_instrument_type: Optional[str] = Field(
        None, alias="fundingInstrumentType"
    )
    category_of_funding: Optional[str] = Field(None, alias="categoryOfFundingActivity")
    award_ceiling: Optional[float] = Field(None, alias="awardCeiling")
    award_floor: Optional[float] = Field(None, alias="awardFloor")
    estimated_total_funding: Optional[float] = Field(
        None, alias="estimatedTotalProgramFunding"
    )
    expected_number_of_awards: Optional[int] = Field(
        None, alias="expectedNumberOfAwards"
    )
    cost_sharing: Optional[bool] = Field(None, alias="costSharingOrMatchingRequirement")
    additional_info_url: Optional[str] = Field(None, alias="additionalInformationUrl")
    grantor_contact_email: Optional[str] = Field(None, alias="grantorContactEmail")
    grantor_contact_name: Optional[str] = Field(None, alias="grantorContactName")

    model_config = {"populate_by_name": True}


class DiscoveredGrant(BaseModel):
    """Normalized grant data for publishing to Redis stream."""

    external_id: str = Field(..., description="Source system ID (opportunity_id)")
    source: str = Field(default="grants_gov", description="Source identifier")
    title: str = Field(..., description="Grant title")
    agency: str = Field(..., description="Funding agency")
    deadline: Optional[datetime] = Field(None, description="Application deadline")
    url: str = Field(..., description="Direct URL to opportunity")
    description: Optional[str] = Field(None, description="Grant description")
    posted_date: Optional[datetime] = Field(None, description="Date posted")
    award_ceiling: Optional[float] = Field(None, description="Maximum award amount")
    award_floor: Optional[float] = Field(None, description="Minimum award amount")
    estimated_funding: Optional[float] = Field(None, description="Total program funding")
    eligible_applicants: list[str] = Field(
        default_factory=list, description="Eligible applicant types"
    )
    cfda_numbers: list[str] = Field(
        default_factory=list, description="CFDA/Assistance Listing numbers"
    )
    funding_type: Optional[str] = Field(None, description="Funding instrument type")
    category: Optional[str] = Field(None, description="Category of funding activity")
    cost_sharing_required: Optional[bool] = Field(
        None, description="Cost sharing requirement"
    )
    discovered_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp of discovery"
    )
    raw_data: Optional[dict] = Field(None, description="Raw API response data")

    def to_stream_dict(self) -> dict:
        """Convert to dictionary suitable for Redis stream."""
        data = self.model_dump(mode="json", exclude_none=True)
        # Convert complex types to JSON strings for Redis
        if "eligible_applicants" in data:
            import json

            data["eligible_applicants"] = json.dumps(data["eligible_applicants"])
        if "cfda_numbers" in data:
            import json

            data["cfda_numbers"] = json.dumps(data["cfda_numbers"])
        if "raw_data" in data:
            import json

            data["raw_data"] = json.dumps(data["raw_data"])
        return data


# ============================================================================
# Rate Limiter
# ============================================================================


class RateLimiter:
    """Simple rate limiter for API calls (3 requests/second max)."""

    def __init__(self, max_requests: int = 3, time_window: float = 1.0):
        self.max_requests = max_requests
        self.time_window = time_window
        self.request_times: list[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until we can make a request within rate limits."""
        async with self._lock:
            now = time.monotonic()
            # Remove old timestamps outside the time window
            self.request_times = [
                t for t in self.request_times if now - t < self.time_window
            ]

            if len(self.request_times) >= self.max_requests:
                # Wait until the oldest request expires
                sleep_time = self.time_window - (now - self.request_times[0])
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    # Remove expired timestamps after sleeping
                    now = time.monotonic()
                    self.request_times = [
                        t for t in self.request_times if now - t < self.time_window
                    ]

            self.request_times.append(time.monotonic())


# ============================================================================
# Grants.gov RSS Discovery Agent
# ============================================================================


class GrantsGovRSSAgent:
    """
    Agent for discovering new grant opportunities from Grants.gov RSS feed.

    Features:
    - Polls RSS feed every 5 minutes
    - Fetches full details via Grants.gov API
    - Publishes to Redis stream
    - Tracks last processed ID to avoid duplicates
    - Rate limiting (3 req/sec)
    - Retry logic for network errors
    """

    RSS_FEED_URL = settings.grants_gov_rss_url
    API_BASE_URL = settings.grants_gov_api_url
    REDIS_STREAM = "grants:discovered"
    REDIS_LAST_ID_KEY = "grants_gov:last_processed_id"
    REDIS_PROCESSED_SET = "grants_gov:processed_ids"

    def __init__(self):
        self.rate_limiter = RateLimiter(max_requests=3, time_window=1.0)
        self._redis: Optional[aioredis.Redis] = None
        self._http_client: Optional[httpx.AsyncClient] = None
        self.logger = logger.bind(agent="grants_gov_rss")

    async def _get_redis(self) -> aioredis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                headers={
                    "User-Agent": "GrantRadar/1.0 (https://grantradar.com)",
                    "Accept": "application/json",
                },
            )
        return self._http_client

    async def close(self) -> None:
        """Close connections."""
        if self._redis:
            await self._redis.close()
            self._redis = None
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def fetch_rss_feed(self) -> list[GrantsGovEntry]:
        """
        Fetch and parse the Grants.gov RSS feed.

        Returns:
            List of parsed RSS entries
        """
        self.logger.info("fetching_rss_feed", url=self.RSS_FEED_URL)

        await self.rate_limiter.acquire()

        client = await self._get_http_client()

        try:
            response = await client.get(self.RSS_FEED_URL)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            self.logger.error(
                "rss_feed_http_error",
                status_code=e.response.status_code,
                url=self.RSS_FEED_URL,
            )
            raise

        # Parse the RSS feed
        feed = feedparser.parse(response.text)

        if feed.bozo and feed.bozo_exception:
            self.logger.warning(
                "rss_feed_parse_warning",
                exception=str(feed.bozo_exception),
            )

        entries = []
        for entry in feed.entries:
            try:
                parsed_entry = self._parse_rss_entry(entry)
                if parsed_entry:
                    entries.append(parsed_entry)
            except Exception as e:
                self.logger.warning(
                    "rss_entry_parse_error",
                    entry_id=getattr(entry, "id", "unknown"),
                    error=str(e),
                )

        self.logger.info("rss_feed_parsed", entry_count=len(entries))
        return entries

    def _parse_rss_entry(self, entry) -> Optional[GrantsGovEntry]:
        """Parse a single RSS feed entry."""
        # Extract opportunity ID from the entry
        # Grants.gov RSS typically includes the ID in the link or guid
        opportunity_id = None

        # Try to extract from link
        link = getattr(entry, "link", "")
        if "opportunityId=" in link:
            opportunity_id = link.split("opportunityId=")[-1].split("&")[0]
        elif hasattr(entry, "id"):
            # Sometimes the guid contains the ID
            guid = entry.id
            if guid.isdigit():
                opportunity_id = guid
            elif "opportunityId=" in guid:
                opportunity_id = guid.split("opportunityId=")[-1].split("&")[0]

        # Fallback: generate hash from title if no ID found
        if not opportunity_id:
            title = getattr(entry, "title", "")
            if title:
                opportunity_id = hashlib.md5(title.encode()).hexdigest()[:12]
            else:
                return None

        # Parse dates
        close_date = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                close_date = datetime(*entry.published_parsed[:6])
            except (ValueError, TypeError):
                pass

        posted_date = None
        if hasattr(entry, "updated_parsed") and entry.updated_parsed:
            try:
                posted_date = datetime(*entry.updated_parsed[:6])
            except (ValueError, TypeError):
                pass

        # Extract agency from title or description
        title = getattr(entry, "title", "Unknown Title")
        agency = "Unknown Agency"

        # Often the agency is in the summary/description
        description = getattr(entry, "summary", "") or getattr(
            entry, "description", ""
        )

        return GrantsGovEntry(
            opportunity_id=opportunity_id,
            title=title,
            agency=agency,
            close_date=close_date,
            link=link,
            posted_date=posted_date,
            description=description[:500] if description else None,
        )

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def fetch_grant_details(
        self, opportunity_id: str
    ) -> Optional[GrantsGovDetails]:
        """
        Fetch full grant details from Grants.gov API.

        Args:
            opportunity_id: The Grants.gov opportunity ID

        Returns:
            Full grant details or None if not found
        """
        self.logger.info("fetching_grant_details", opportunity_id=opportunity_id)

        await self.rate_limiter.acquire()

        client = await self._get_http_client()

        # Grants.gov API uses POST with search criteria
        search_payload = {
            "keyword": opportunity_id,
            "oppNum": opportunity_id,
            "rows": 1,
        }

        try:
            response = await client.post(
                self.API_BASE_URL,
                json=search_payload,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            self.logger.error(
                "api_http_error",
                status_code=e.response.status_code,
                opportunity_id=opportunity_id,
            )
            raise

        data = response.json()

        # Extract opportunity from response
        opportunities = data.get("oppHits", [])
        if not opportunities:
            self.logger.warning(
                "grant_not_found_in_api",
                opportunity_id=opportunity_id,
            )
            return None

        opp_data = opportunities[0]

        try:
            return GrantsGovDetails(
                opportunityId=str(opp_data.get("id", opportunity_id)),
                opportunityNumber=opp_data.get("number"),
                opportunityTitle=opp_data.get("title", "Unknown Title"),
                agencyCode=opp_data.get("agency"),
                agencyName=opp_data.get("agencyName"),
                oppStatus=opp_data.get("oppStatus"),
                postedDate=opp_data.get("openDate"),
                closeDate=opp_data.get("closeDate"),
                archiveDate=opp_data.get("archiveDate"),
                description=opp_data.get("synopsis"),
                cfdaList=opp_data.get("cfdaList", []),
                eligibleApplicants=opp_data.get("eligibleApplicants", []),
                fundingInstrumentType=opp_data.get("instrumentType"),
                categoryOfFundingActivity=opp_data.get("fundingActivityCategory"),
                awardCeiling=opp_data.get("awardCeiling"),
                awardFloor=opp_data.get("awardFloor"),
                estimatedTotalProgramFunding=opp_data.get("estimatedFunding"),
                expectedNumberOfAwards=opp_data.get("numberOfAwards"),
                costSharingOrMatchingRequirement=opp_data.get("costSharing"),
                additionalInformationUrl=opp_data.get("additionalInfoUrl"),
                grantorContactEmail=opp_data.get("grantorContactEmail"),
                grantorContactName=opp_data.get("grantorContactName"),
            )
        except Exception as e:
            self.logger.error(
                "grant_details_parse_error",
                opportunity_id=opportunity_id,
                error=str(e),
            )
            return None

    def _normalize_grant(
        self, entry: GrantsGovEntry, details: Optional[GrantsGovDetails]
    ) -> DiscoveredGrant:
        """
        Normalize RSS entry and API details into a DiscoveredGrant.

        Args:
            entry: Parsed RSS entry
            details: Full API details (may be None)

        Returns:
            Normalized DiscoveredGrant
        """
        # Parse deadline
        deadline = None
        if details and details.close_date:
            try:
                deadline = datetime.strptime(details.close_date, "%m/%d/%Y")
            except ValueError:
                try:
                    deadline = datetime.fromisoformat(details.close_date)
                except ValueError:
                    pass
        elif entry.close_date:
            deadline = entry.close_date

        # Parse posted date
        posted_date = None
        if details and details.posted_date:
            try:
                posted_date = datetime.strptime(details.posted_date, "%m/%d/%Y")
            except ValueError:
                try:
                    posted_date = datetime.fromisoformat(details.posted_date)
                except ValueError:
                    pass
        elif entry.posted_date:
            posted_date = entry.posted_date

        # Build opportunity URL
        url = entry.link or f"https://www.grants.gov/search-results-detail/{entry.opportunity_id}"

        # Determine agency
        agency = (
            details.agency_name
            if details and details.agency_name
            else (
                details.agency_code
                if details and details.agency_code
                else entry.agency
            )
        )

        return DiscoveredGrant(
            external_id=entry.opportunity_id,
            source="grants_gov",
            title=details.title if details else entry.title,
            agency=agency,
            deadline=deadline,
            url=url,
            description=(
                details.description if details else entry.description
            ),
            posted_date=posted_date,
            award_ceiling=details.award_ceiling if details else None,
            award_floor=details.award_floor if details else None,
            estimated_funding=details.estimated_total_funding if details else None,
            eligible_applicants=(
                details.eligible_applicants if details else []
            ),
            cfda_numbers=details.cfda_numbers if details else [],
            funding_type=(
                details.funding_instrument_type if details else None
            ),
            category=details.category_of_funding if details else None,
            cost_sharing_required=details.cost_sharing if details else None,
            raw_data=details.model_dump() if details else None,
        )

    async def is_processed(self, opportunity_id: str) -> bool:
        """Check if an opportunity has already been processed."""
        redis = await self._get_redis()
        return await redis.sismember(self.REDIS_PROCESSED_SET, opportunity_id)

    async def mark_processed(self, opportunity_id: str) -> None:
        """Mark an opportunity as processed."""
        redis = await self._get_redis()
        await redis.sadd(self.REDIS_PROCESSED_SET, opportunity_id)
        # Also update last processed ID
        await redis.set(self.REDIS_LAST_ID_KEY, opportunity_id)

    async def publish_grant(self, grant: DiscoveredGrant) -> str:
        """
        Publish a discovered grant to the Redis stream.

        Args:
            grant: The normalized grant data

        Returns:
            Stream message ID
        """
        import json as json_lib
        redis = await self._get_redis()
        # Wrap in "data" key as JSON string - format expected by validator
        stream_data = {"data": json_lib.dumps(grant.to_stream_dict())}

        message_id = await redis.xadd(self.REDIS_STREAM, stream_data)

        self.logger.info(
            "grant_published",
            external_id=grant.external_id,
            message_id=message_id,
            stream=self.REDIS_STREAM,
        )

        return message_id

    async def discover_new_grants(self) -> list[DiscoveredGrant]:
        """
        Main discovery method: fetch RSS, get details, publish new grants.

        Returns:
            List of newly discovered grants
        """
        self.logger.info("starting_discovery_run")
        start_time = time.time()

        try:
            # Fetch RSS feed
            entries = await self.fetch_rss_feed()

            discovered_grants = []

            for entry in entries:
                # Skip if already processed
                if await self.is_processed(entry.opportunity_id):
                    self.logger.debug(
                        "skipping_processed_entry",
                        opportunity_id=entry.opportunity_id,
                    )
                    continue

                # Fetch full details from API
                try:
                    details = await self.fetch_grant_details(entry.opportunity_id)
                except Exception as e:
                    self.logger.warning(
                        "failed_to_fetch_details",
                        opportunity_id=entry.opportunity_id,
                        error=str(e),
                    )
                    details = None

                # Normalize the grant
                grant = self._normalize_grant(entry, details)

                # Publish to Redis stream
                await self.publish_grant(grant)

                # Mark as processed
                await self.mark_processed(entry.opportunity_id)

                discovered_grants.append(grant)

            elapsed = time.time() - start_time
            self.logger.info(
                "discovery_run_complete",
                entries_found=len(entries),
                new_grants=len(discovered_grants),
                elapsed_seconds=round(elapsed, 2),
            )

            return discovered_grants

        except Exception as e:
            self.logger.error(
                "discovery_run_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise


# ============================================================================
# Celery Task Configuration
# ============================================================================

# Initialize Celery app
celery_app = Celery(
    "grants_gov_discovery",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minute hard limit
    task_soft_time_limit=240,  # 4 minute soft limit
    worker_prefetch_multiplier=1,  # One task at a time for this agent
)

# Celery Beat schedule - run every 5 minutes
celery_app.conf.beat_schedule = {
    "discover-grants-gov-rss": {
        "task": "agents.discovery.grants_gov_rss.discover_grants_gov",
        "schedule": 300.0,  # 5 minutes in seconds
        "options": {"queue": "discovery"},
    },
}


@celery_app.task(
    bind=True,
    name="agents.discovery.grants_gov_rss.discover_grants_gov",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 3},
    acks_late=True,
)
def discover_grants_gov(self) -> dict:
    """
    Celery task to discover new grants from Grants.gov RSS feed.

    This task:
    1. Fetches the Grants.gov RSS feed
    2. Extracts new opportunity IDs
    3. Fetches full details via API
    4. Publishes to Redis stream

    Returns:
        Dictionary with discovery results
    """
    task_logger = logger.bind(
        task_id=self.request.id,
        task_name=self.name,
    )
    task_logger.info("celery_task_started")

    async def run_discovery():
        agent = GrantsGovRSSAgent()
        try:
            grants = await agent.discover_new_grants()
            return {
                "status": "success",
                "grants_discovered": len(grants),
                "grant_ids": [g.external_id for g in grants],
            }
        finally:
            await agent.close()

    # Run the async discovery
    try:
        result = asyncio.run(run_discovery())
        task_logger.info(
            "celery_task_completed",
            grants_discovered=result["grants_discovered"],
        )
        return result
    except Exception as e:
        task_logger.error(
            "celery_task_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise


# ============================================================================
# Manual Run Support
# ============================================================================


async def main():
    """Manual run for testing the agent."""
    agent = GrantsGovRSSAgent()
    try:
        grants = await agent.discover_new_grants()
        print(f"Discovered {len(grants)} new grants")
        for grant in grants:
            print(f"  - {grant.external_id}: {grant.title}")
    finally:
        await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
