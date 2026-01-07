"""
Grants.gov XML Extract Discovery Agent

Downloads and parses daily XML database extracts from Grants.gov
since the RSS feed has been deprecated.

XML Extract URL Pattern:
https://prod-grants-gov-chatbot.s3.amazonaws.com/extracts/GrantsDBExtract{YYYYMMDD}v2.zip
"""

import asyncio
import io
import time
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Optional
from pathlib import Path

import httpx
import redis.asyncio as aioredis
import structlog
from celery import Celery
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from backend.core.config import settings

# Configure structured logging
logger = structlog.get_logger(__name__)

# ============================================================================
# Constants
# ============================================================================

XML_EXTRACT_BASE_URL = "https://prod-grants-gov-chatbot.s3.amazonaws.com/extracts"
REDIS_STREAM = "grants:discovered"
REDIS_PROCESSED_SET = "grants_gov:processed_ids"
REDIS_LAST_EXTRACT_KEY = "grants_gov:last_extract_date"


# ============================================================================
# Pydantic Models
# ============================================================================


class GrantsGovOpportunity(BaseModel):
    """Parsed grant opportunity from XML extract."""

    opportunity_id: str = Field(..., description="Grants.gov opportunity ID")
    opportunity_number: Optional[str] = Field(None, description="Opportunity number")
    title: str = Field(..., description="Grant title")
    agency_code: Optional[str] = Field(None, description="Agency code")
    agency_name: Optional[str] = Field(None, description="Agency name")
    opportunity_status: Optional[str] = Field(None, description="Status")
    posted_date: Optional[datetime] = Field(None, description="Date posted")
    close_date: Optional[datetime] = Field(None, description="Application deadline")
    description: Optional[str] = Field(None, description="Synopsis/description")
    cfda_numbers: list[str] = Field(default_factory=list, description="CFDA numbers")
    eligible_applicants: list[str] = Field(default_factory=list, description="Eligible applicant types")
    funding_instrument_type: Optional[str] = Field(None, description="Funding type")
    category: Optional[str] = Field(None, description="Category of funding")
    award_ceiling: Optional[float] = Field(None, description="Max award")
    award_floor: Optional[float] = Field(None, description="Min award")
    estimated_funding: Optional[float] = Field(None, description="Total funding")
    cost_sharing: Optional[bool] = Field(None, description="Cost sharing required")
    url: Optional[str] = Field(None, description="Direct URL")


class DiscoveredGrant(BaseModel):
    """Normalized grant data for publishing to Redis stream."""

    external_id: str = Field(..., description="Source system ID")
    source: str = Field(default="grants_gov", description="Source identifier")
    title: str = Field(..., description="Grant title")
    agency: str = Field(..., description="Funding agency")
    deadline: Optional[datetime] = Field(None, description="Application deadline")
    url: str = Field(..., description="Direct URL to opportunity")
    description: Optional[str] = Field(None, description="Grant description")
    posted_date: Optional[datetime] = Field(None, description="Date posted")
    award_ceiling: Optional[float] = Field(None, description="Maximum award")
    award_floor: Optional[float] = Field(None, description="Minimum award")
    estimated_funding: Optional[float] = Field(None, description="Total funding")
    eligible_applicants: list[str] = Field(default_factory=list)
    cfda_numbers: list[str] = Field(default_factory=list)
    funding_type: Optional[str] = Field(None)
    category: Optional[str] = Field(None)
    cost_sharing_required: Optional[bool] = Field(None)
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_stream_dict(self) -> dict:
        """Convert to dictionary suitable for Redis stream."""
        import json
        data = self.model_dump(mode="json", exclude_none=True)
        if "eligible_applicants" in data:
            data["eligible_applicants"] = json.dumps(data["eligible_applicants"])
        if "cfda_numbers" in data:
            data["cfda_numbers"] = json.dumps(data["cfda_numbers"])
        # Convert booleans to strings (Redis doesn't accept bool type)
        if "cost_sharing_required" in data:
            data["cost_sharing_required"] = str(data["cost_sharing_required"]).lower()
        return data


# ============================================================================
# Grants.gov XML Extract Discovery Agent
# ============================================================================


class GrantsGovXMLAgent:
    """
    Agent for discovering grant opportunities from Grants.gov daily XML extracts.

    Features:
    - Downloads daily XML database extract (~76MB compressed)
    - Parses all opportunities from XML
    - Tracks processed IDs to identify new grants
    - Publishes new grants to Redis stream
    - Runs daily (or more frequently to catch updates)
    """

    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None
        self._http_client: Optional[httpx.AsyncClient] = None
        self.logger = logger.bind(agent="grants_gov_xml")

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
                timeout=httpx.Timeout(300.0),  # 5 min timeout for large downloads
                headers={
                    "User-Agent": "GrantRadar/1.0 (https://grantradar.com)",
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

    def _get_extract_url(self, date: datetime) -> str:
        """Generate the URL for a specific date's XML extract."""
        date_str = date.strftime("%Y%m%d")
        return f"{XML_EXTRACT_BASE_URL}/GrantsDBExtract{date_str}v2.zip"

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=5, max=60),
    )
    async def download_extract(self, date: datetime) -> bytes:
        """
        Download the XML extract for a specific date.

        Args:
            date: The date to download the extract for

        Returns:
            Raw zip file bytes
        """
        url = self._get_extract_url(date)
        self.logger.info("downloading_xml_extract", url=url, date=date.isoformat())

        client = await self._get_http_client()

        try:
            response = await client.get(url)
            response.raise_for_status()
            self.logger.info(
                "xml_extract_downloaded",
                size_mb=round(len(response.content) / 1024 / 1024, 2),
            )
            return response.content
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                self.logger.warning("xml_extract_not_found", date=date.isoformat())
            raise

    def parse_xml_extract(self, zip_content: bytes) -> list[GrantsGovOpportunity]:
        """
        Parse the XML extract from the zip file.

        Args:
            zip_content: Raw zip file bytes

        Returns:
            List of parsed opportunities
        """
        self.logger.info("parsing_xml_extract")
        start_time = time.time()

        opportunities = []

        with zipfile.ZipFile(io.BytesIO(zip_content)) as zf:
            # Find the XML file in the archive
            xml_files = [f for f in zf.namelist() if f.endswith('.xml')]
            if not xml_files:
                self.logger.error("no_xml_file_in_archive")
                return []

            xml_filename = xml_files[0]
            self.logger.info("parsing_xml_file", filename=xml_filename)

            with zf.open(xml_filename) as xml_file:
                # Parse XML incrementally to handle large files
                # Handle namespace in Grants.gov XML
                ns = {'g': 'http://apply.grants.gov/system/OpportunityDetail-V1.0'}
                context = ET.iterparse(xml_file, events=('end',))

                for event, elem in context:
                    # Match with or without namespace
                    tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                    if tag_name == 'OpportunitySynopsisDetail_1_0':
                        try:
                            opp = self._parse_opportunity_element(elem)
                            if opp:
                                opportunities.append(opp)
                        except Exception as e:
                            self.logger.warning(
                                "failed_to_parse_opportunity",
                                error=str(e),
                            )
                        # Clear element to save memory
                        elem.clear()

        elapsed = time.time() - start_time
        self.logger.info(
            "xml_parsing_complete",
            opportunities_parsed=len(opportunities),
            elapsed_seconds=round(elapsed, 2),
        )

        return opportunities

    def _parse_opportunity_element(self, elem: ET.Element) -> Optional[GrantsGovOpportunity]:
        """Parse a single opportunity XML element."""
        # Namespace for Grants.gov XML
        ns = {'g': 'http://apply.grants.gov/system/OpportunityDetail-V1.0'}

        def get_text(tag: str) -> Optional[str]:
            # Try with namespace first, then without
            child = elem.find(f'g:{tag}', ns)
            if child is None:
                child = elem.find(tag)
            # Also try with full namespace in tag
            if child is None:
                for c in elem:
                    if c.tag.endswith(f'}}{tag}') or c.tag == tag:
                        child = c
                        break
            return child.text.strip() if child is not None and child.text else None

        def get_float(tag: str) -> Optional[float]:
            text = get_text(tag)
            if text:
                try:
                    return float(text.replace(',', ''))
                except ValueError:
                    return None
            return None

        def get_date(tag: str) -> Optional[datetime]:
            text = get_text(tag)
            if text:
                for fmt in ('%m%d%Y', '%Y-%m-%d', '%m/%d/%Y'):
                    try:
                        return datetime.strptime(text, fmt)
                    except ValueError:
                        continue
            return None

        opportunity_id = get_text('OpportunityID')
        title = get_text('OpportunityTitle')

        if not opportunity_id or not title:
            return None

        # Parse CFDA numbers - they can be in CFDANumbers element or directly
        cfda_numbers = []
        cfda_text = get_text('CFDANumbers')
        if cfda_text:
            # CFDANumbers is often a semicolon or comma separated list
            for cfda in cfda_text.replace(';', ',').split(','):
                cfda = cfda.strip()
                if cfda:
                    cfda_numbers.append(cfda)

        # Parse eligible applicants - they are codes
        eligible = []
        for child in elem:
            tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            if tag_name == 'EligibleApplicants' and child.text:
                eligible.append(child.text.strip())

        return GrantsGovOpportunity(
            opportunity_id=opportunity_id,
            opportunity_number=get_text('OpportunityNumber'),
            title=title,
            agency_code=get_text('AgencyCode'),
            agency_name=get_text('AgencyName'),
            opportunity_status=get_text('OpportunityStatus'),
            posted_date=get_date('PostDate'),
            close_date=get_date('CloseDate'),
            description=get_text('Description') or get_text('Synopsis'),
            cfda_numbers=cfda_numbers,
            eligible_applicants=eligible,
            funding_instrument_type=get_text('FundingInstrumentType'),
            category=get_text('CategoryOfFundingActivity'),
            award_ceiling=get_float('AwardCeiling'),
            award_floor=get_float('AwardFloor'),
            estimated_funding=get_float('EstimatedTotalProgramFunding'),
            cost_sharing=get_text('CostSharingOrMatchingRequirement') == 'Yes',
            url=f"https://www.grants.gov/search-results-detail/{opportunity_id}",
        )

    def _normalize_opportunity(self, opp: GrantsGovOpportunity) -> DiscoveredGrant:
        """Convert opportunity to normalized grant format."""
        return DiscoveredGrant(
            external_id=opp.opportunity_id,
            source="grants_gov",
            title=opp.title,
            agency=opp.agency_name or opp.agency_code or "Unknown Agency",
            deadline=opp.close_date,
            url=opp.url or f"https://www.grants.gov/search-results-detail/{opp.opportunity_id}",
            description=opp.description,
            posted_date=opp.posted_date,
            award_ceiling=opp.award_ceiling,
            award_floor=opp.award_floor,
            estimated_funding=opp.estimated_funding,
            eligible_applicants=opp.eligible_applicants,
            cfda_numbers=opp.cfda_numbers,
            funding_type=opp.funding_instrument_type,
            category=opp.category,
            cost_sharing_required=opp.cost_sharing,
        )

    async def is_processed(self, opportunity_id: str) -> bool:
        """Check if an opportunity has already been processed."""
        redis = await self._get_redis()
        return await redis.sismember(REDIS_PROCESSED_SET, opportunity_id)

    async def mark_processed(self, opportunity_id: str) -> None:
        """Mark an opportunity as processed."""
        redis = await self._get_redis()
        await redis.sadd(REDIS_PROCESSED_SET, opportunity_id)

    async def publish_grant(self, grant: DiscoveredGrant) -> str:
        """Publish a discovered grant to the Redis stream."""
        import json as json_lib
        redis = await self._get_redis()
        # Wrap in "data" key as JSON string - format expected by validator
        stream_data = {"data": json_lib.dumps(grant.to_stream_dict())}
        message_id = await redis.xadd(REDIS_STREAM, stream_data)

        self.logger.debug(
            "grant_published",
            external_id=grant.external_id,
            message_id=message_id,
        )

        return message_id

    async def get_last_extract_date(self) -> Optional[datetime]:
        """Get the date of the last processed extract."""
        redis = await self._get_redis()
        date_str = await redis.get(REDIS_LAST_EXTRACT_KEY)
        if date_str:
            return datetime.fromisoformat(date_str)
        return None

    async def set_last_extract_date(self, date: datetime) -> None:
        """Record the date of the last processed extract."""
        redis = await self._get_redis()
        await redis.set(REDIS_LAST_EXTRACT_KEY, date.isoformat())

    async def discover_new_grants(self, target_date: Optional[datetime] = None) -> list[DiscoveredGrant]:
        """
        Main discovery method: download XML, parse, publish new grants.

        Args:
            target_date: Specific date to fetch (defaults to today)

        Returns:
            List of newly discovered grants
        """
        if target_date is None:
            target_date = datetime.now(timezone.utc)

        self.logger.info("starting_discovery_run", target_date=target_date.isoformat())
        start_time = time.time()

        try:
            # Download the XML extract
            try:
                zip_content = await self.download_extract(target_date)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    # Try yesterday if today's not available yet
                    target_date = target_date - timedelta(days=1)
                    self.logger.info("trying_previous_day", date=target_date.isoformat())
                    zip_content = await self.download_extract(target_date)
                else:
                    raise

            # Parse the XML
            opportunities = self.parse_xml_extract(zip_content)

            # Filter to only active/posted opportunities
            active_opps = [
                opp for opp in opportunities
                if opp.opportunity_status in (None, 'Posted', 'Forecasted', 'posted', 'forecasted')
            ]

            self.logger.info(
                "filtering_opportunities",
                total=len(opportunities),
                active=len(active_opps),
            )

            discovered_grants = []
            new_count = 0
            skipped_count = 0

            for opp in active_opps:
                # Skip if already processed
                if await self.is_processed(opp.opportunity_id):
                    skipped_count += 1
                    continue

                # Normalize and publish
                grant = self._normalize_opportunity(opp)
                await self.publish_grant(grant)
                await self.mark_processed(opp.opportunity_id)

                discovered_grants.append(grant)
                new_count += 1

                # Log progress every 100 grants
                if new_count % 100 == 0:
                    self.logger.info("discovery_progress", new_grants=new_count)

            # Record last extract date
            await self.set_last_extract_date(target_date)

            elapsed = time.time() - start_time
            self.logger.info(
                "discovery_run_complete",
                total_opportunities=len(opportunities),
                active_opportunities=len(active_opps),
                new_grants=new_count,
                skipped=skipped_count,
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

celery_app = Celery(
    "grants_gov_xml_discovery",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,  # 30 minute hard limit (large file processing)
    task_soft_time_limit=1500,  # 25 minute soft limit
    worker_prefetch_multiplier=1,
)

# Run every 6 hours to catch daily updates
celery_app.conf.beat_schedule = {
    "discover-grants-gov-xml": {
        "task": "agents.discovery.grants_gov_xml.discover_grants_gov_xml",
        "schedule": 21600.0,  # 6 hours in seconds
        "options": {"queue": "high"},
    },
}


@celery_app.task(
    bind=True,
    name="agents.discovery.grants_gov_xml.discover_grants_gov_xml",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=3600,
    retry_kwargs={"max_retries": 3},
    acks_late=True,
)
def discover_grants_gov_xml(self) -> dict:
    """
    Celery task to discover grants from Grants.gov XML extract.
    """
    task_logger = logger.bind(
        task_id=self.request.id,
        task_name=self.name,
    )
    task_logger.info("celery_task_started")

    async def run_discovery():
        agent = GrantsGovXMLAgent()
        try:
            grants = await agent.discover_new_grants()
            return {
                "status": "success",
                "grants_discovered": len(grants),
                "sample_ids": [g.external_id for g in grants[:10]],
            }
        finally:
            await agent.close()

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
# Manual Run / Testing
# ============================================================================


async def main():
    """Manual run for testing the agent."""
    agent = GrantsGovXMLAgent()
    try:
        grants = await agent.discover_new_grants()
        print(f"\nDiscovered {len(grants)} new grants")
        for grant in grants[:10]:
            print(f"  - {grant.external_id}: {grant.title[:60]}...")
    finally:
        await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
