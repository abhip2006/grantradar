"""
NSF Award Search API Discovery Agent
Discovers new grant opportunities from the National Science Foundation.
"""
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
import asyncio

import httpx
import structlog
from celery import shared_task
from pydantic import BaseModel, Field, field_validator
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from backend.core.config import settings
from agents.discovery.base import DiscoveryAgent


# ============================================================================
# Pydantic Models
# ============================================================================


class NSFAwardStatus(str, Enum):
    """NSF Award status values."""
    ACTIVE = "Active"
    EXPIRED = "Expired"


class NSFAward(BaseModel):
    """
    Model for NSF Award API response data.

    Maps the JSON response from the NSF Award Search API.
    """
    id: str = Field(..., description="Award ID/Number")
    title: str = Field(..., description="Award title")
    agency: str = Field(default="NSF", description="Funding agency")

    # Award details
    abstractText: Optional[str] = Field(default=None, alias="abstractText", description="Award abstract")
    awardeeCity: Optional[str] = Field(default=None, description="Awardee institution city")
    awardeeCountryCode: Optional[str] = Field(default=None, description="Awardee country code")
    awardeeName: Optional[str] = Field(default=None, description="Awardee institution name")
    awardeeStateCode: Optional[str] = Field(default=None, description="Awardee state code")
    awardeeZipCode: Optional[str] = Field(default=None, description="Awardee ZIP code")

    # Funding information
    fundsObligatedAmt: Optional[str] = Field(default=None, description="Amount of funds obligated")

    # Dates
    date: Optional[str] = Field(default=None, description="Award date")
    startDate: Optional[str] = Field(default=None, description="Award start date")
    expDate: Optional[str] = Field(default=None, description="Award expiration date")

    # Principal Investigator
    piFirstName: Optional[str] = Field(default=None, description="PI first name")
    piLastName: Optional[str] = Field(default=None, description="PI last name")
    piMiddeInitial: Optional[str] = Field(default=None, description="PI middle initial")
    piEmail: Optional[str] = Field(default=None, description="PI email address")

    # Program information
    cfdaNumber: Optional[str] = Field(default=None, description="CFDA Number")
    fundProgramName: Optional[str] = Field(default=None, description="Fund program name")
    primaryProgram: Optional[str] = Field(default=None, description="Primary program")

    # Status
    awardInstrument: Optional[str] = Field(default=None, description="Award instrument type")

    class Config:
        populate_by_name = True

    @field_validator("primaryProgram", "fundProgramName", "cfdaNumber", mode="before")
    @classmethod
    def parse_list_to_string(cls, v: Any) -> Optional[str]:
        """Handle fields that may come as lists from the API."""
        if v is None:
            return None
        if isinstance(v, list):
            return "; ".join(str(x) for x in v) if v else None
        return str(v)

    @field_validator("fundsObligatedAmt", mode="before")
    @classmethod
    def parse_funds(cls, v: Any) -> Optional[str]:
        """Handle various formats of funds amount."""
        if v is None:
            return None
        return str(v)

    def get_amount(self) -> Optional[Decimal]:
        """Parse funds amount to Decimal."""
        if self.fundsObligatedAmt:
            try:
                # Remove any commas and dollar signs
                cleaned = self.fundsObligatedAmt.replace(",", "").replace("$", "")
                return Decimal(cleaned)
            except Exception:
                return None
        return None

    def get_pi_name(self) -> Optional[str]:
        """Get full PI name."""
        parts = []
        if self.piFirstName:
            parts.append(self.piFirstName)
        if self.piMiddeInitial:
            parts.append(self.piMiddeInitial)
        if self.piLastName:
            parts.append(self.piLastName)
        return " ".join(parts) if parts else None


class NSFSearchParams(BaseModel):
    """
    Query parameters for NSF Award Search API.

    See: https://www.research.gov/common/webapi/awardapisearch-v1.htm
    """
    # Date filters (MM/DD/YYYY format)
    dateStart: Optional[str] = Field(default=None, description="Start date for award date range")
    dateEnd: Optional[str] = Field(default=None, description="End date for award date range")

    # Text search
    keyword: Optional[str] = Field(default=None, description="Keyword search")

    # Institution filters
    awardeeName: Optional[str] = Field(default=None, description="Awardee institution name")
    awardeeStateCode: Optional[str] = Field(default=None, description="State code (e.g., 'CA')")

    # PI filters
    piLastName: Optional[str] = Field(default=None, description="PI last name")

    # Program filters
    cfdaNumber: Optional[str] = Field(default=None, description="CFDA number")
    fundProgramName: Optional[str] = Field(default=None, description="Fund program name")

    # Pagination
    offset: int = Field(default=1, ge=1, description="Result offset (1-indexed)")
    rpp: int = Field(default=25, ge=1, le=25, description="Results per page (max 25)")

    # Output format
    printFields: Optional[str] = Field(
        default=None,
        description="Comma-separated list of fields to return"
    )

    def to_query_params(self) -> dict[str, str]:
        """Convert to API query parameters, excluding None values."""
        params = {}
        for key, value in self.model_dump(exclude_none=True).items():
            params[key] = str(value)
        return params


class DiscoveredGrant(BaseModel):
    """
    Normalized grant data structure for publishing.

    This is the standard format used across all discovery agents.
    """
    external_id: str = Field(..., description="External ID from source")
    source: str = Field(..., description="Data source identifier")
    title: str = Field(..., description="Grant title")
    description: Optional[str] = Field(default=None, description="Grant description/abstract")

    # Funding details
    amount: Optional[Decimal] = Field(default=None, description="Award amount")
    amount_min: Optional[Decimal] = Field(default=None, description="Minimum award amount")
    amount_max: Optional[Decimal] = Field(default=None, description="Maximum award amount")

    # Dates
    start_date: Optional[str] = Field(default=None, description="Start date (ISO format)")
    end_date: Optional[str] = Field(default=None, description="End date/deadline (ISO format)")
    posted_date: Optional[str] = Field(default=None, description="Date posted (ISO format)")

    # Organization
    funding_agency: str = Field(default="NSF", description="Funding agency")
    program_name: Optional[str] = Field(default=None, description="Program name")
    cfda_number: Optional[str] = Field(default=None, description="CFDA number")

    # Awardee/Institution info
    institution_name: Optional[str] = Field(default=None, description="Awardee institution")
    institution_city: Optional[str] = Field(default=None, description="Institution city")
    institution_state: Optional[str] = Field(default=None, description="Institution state")

    # PI Information
    pi_name: Optional[str] = Field(default=None, description="Principal Investigator name")
    pi_email: Optional[str] = Field(default=None, description="PI email")

    # Metadata
    source_url: Optional[str] = Field(default=None, description="URL to original listing")
    raw_data: Optional[dict[str, Any]] = Field(default=None, description="Original API response")

    class Config:
        json_encoders = {
            Decimal: str
        }


# ============================================================================
# NSF Discovery Agent
# ============================================================================


class NSFDiscoveryAgent(DiscoveryAgent):
    """
    Discovery agent for the NSF Award Search API.

    Fetches recent awards from NSF and publishes them to the grants stream.
    """

    # NSF API configuration
    API_URL = settings.nsf_api_url
    RESULTS_PER_PAGE = 25
    MAX_PAGES = 100  # Safety limit

    # Default fields to request from API
    DEFAULT_FIELDS = (
        "id,title,abstractText,agency,"
        "awardeeCity,awardeeCountryCode,awardeeName,awardeeStateCode,awardeeZipCode,"
        "fundsObligatedAmt,date,startDate,expDate,"
        "piFirstName,piLastName,piMiddeInitial,piEmail,"
        "cfdaNumber,fundProgramName,primaryProgram,awardInstrument"
    )

    def __init__(self):
        super().__init__(source_name="nsf")
        self.http_client: Optional[httpx.AsyncClient] = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                headers={
                    "Accept": "application/json",
                    "User-Agent": "GrantRadar/1.0 (grant-discovery-agent)"
                }
            )
        return self.http_client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        before_sleep=lambda retry_state: structlog.get_logger().warning(
            "nsf_api_retry",
            attempt=retry_state.attempt_number,
            wait=retry_state.next_action.sleep
        )
    )
    async def _fetch_page(self, params: NSFSearchParams) -> dict[str, Any]:
        """
        Fetch a single page of results from the NSF API.

        Args:
            params: Search parameters

        Returns:
            API response as dictionary

        Raises:
            httpx.HTTPError: On network/HTTP errors after retries
        """
        client = await self._get_http_client()
        query_params = params.to_query_params()

        self.logger.debug(
            "nsf_api_request",
            offset=params.offset,
            params=query_params
        )

        response = await client.get(self.API_URL, params=query_params)
        response.raise_for_status()

        data = response.json()
        return data

    def _parse_nsf_date(self, date_str: Optional[str]) -> Optional[str]:
        """
        Parse NSF date format (MM/DD/YYYY) to ISO format.

        Args:
            date_str: Date string in MM/DD/YYYY format

        Returns:
            ISO format date string or None
        """
        if not date_str:
            return None
        try:
            # NSF uses MM/DD/YYYY format
            dt = datetime.strptime(date_str, "%m/%d/%Y")
            return dt.date().isoformat()
        except ValueError:
            self.logger.warning("invalid_date_format", date_str=date_str)
            return None

    def _format_date_for_api(self, dt: datetime) -> str:
        """Format datetime for NSF API (MM/DD/YYYY)."""
        return dt.strftime("%m/%d/%Y")

    def _normalize_award(self, award: NSFAward) -> DiscoveredGrant:
        """
        Convert NSF Award to normalized DiscoveredGrant.

        Args:
            award: NSF Award model

        Returns:
            Normalized DiscoveredGrant
        """
        return DiscoveredGrant(
            external_id=award.id,
            source="nsf",
            title=award.title,
            description=award.abstractText,
            amount=award.get_amount(),
            start_date=self._parse_nsf_date(award.startDate),
            end_date=self._parse_nsf_date(award.expDate),
            posted_date=self._parse_nsf_date(award.date),
            funding_agency="NSF",
            program_name=award.fundProgramName or award.primaryProgram,
            cfda_number=award.cfdaNumber,
            institution_name=award.awardeeName,
            institution_city=award.awardeeCity,
            institution_state=award.awardeeStateCode,
            pi_name=award.get_pi_name(),
            pi_email=award.piEmail,
            source_url=f"https://www.nsf.gov/awardsearch/showAward?AWD_ID={award.id}",
            raw_data=award.model_dump()
        )

    async def _fetch_all_pages(
        self,
        base_params: NSFSearchParams
    ) -> list[NSFAward]:
        """
        Fetch all pages of results from the NSF API.

        Args:
            base_params: Base search parameters

        Returns:
            List of all awards across all pages
        """
        all_awards: list[NSFAward] = []
        current_offset = 1
        page_count = 0

        while page_count < self.MAX_PAGES:
            params = base_params.model_copy(update={"offset": current_offset})

            try:
                response_data = await self._fetch_page(params)
            except httpx.HTTPError as e:
                self.logger.error(
                    "nsf_api_fetch_failed",
                    offset=current_offset,
                    error=str(e)
                )
                break

            # Parse response structure
            # NSF API returns: {"response": {"award": [...], "totalRecords": N}}
            response_wrapper = response_data.get("response", {})
            awards_data = response_wrapper.get("award", [])

            if not awards_data:
                self.logger.info(
                    "nsf_api_no_more_results",
                    offset=current_offset,
                    total_fetched=len(all_awards)
                )
                break

            # Parse awards
            for award_data in awards_data:
                try:
                    award = NSFAward.model_validate(award_data)
                    all_awards.append(award)
                except Exception as e:
                    self.logger.warning(
                        "nsf_award_parse_failed",
                        award_id=award_data.get("id"),
                        error=str(e)
                    )

            self.logger.info(
                "nsf_api_page_fetched",
                offset=current_offset,
                awards_in_page=len(awards_data),
                total_fetched=len(all_awards)
            )

            # Check if we've fetched all results
            if len(awards_data) < self.RESULTS_PER_PAGE:
                break

            current_offset += self.RESULTS_PER_PAGE
            page_count += 1

            # Rate limiting - be nice to the API
            await asyncio.sleep(0.5)

        return all_awards

    async def discover(self) -> list[dict[str, Any]]:
        """
        Discover new grants from NSF.

        Returns:
            List of normalized grant data dictionaries
        """
        # Determine date range
        last_check = self.get_last_check_time()

        if last_check:
            # Query from last check time
            start_date = last_check
        else:
            # First run - get last 7 days
            start_date = datetime.now(timezone.utc) - timedelta(days=7)

        end_date = datetime.now(timezone.utc)

        self.logger.info(
            "nsf_discovery_start",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )

        # Build search parameters
        params = NSFSearchParams(
            dateStart=self._format_date_for_api(start_date),
            dateEnd=self._format_date_for_api(end_date),
            printFields=self.DEFAULT_FIELDS,
            rpp=self.RESULTS_PER_PAGE,
            offset=1
        )

        # Fetch all awards
        awards = await self._fetch_all_pages(params)

        self.logger.info(
            "nsf_awards_fetched",
            total_awards=len(awards)
        )

        # Filter duplicates and normalize
        new_grants: list[dict[str, Any]] = []

        for award in awards:
            # Check for duplicates
            if self.is_duplicate(award.id, award.title):
                self.logger.debug(
                    "nsf_award_duplicate",
                    award_id=award.id
                )
                continue

            # Normalize and add
            grant = self._normalize_award(award)
            new_grants.append(grant.model_dump(mode="json"))

            # Mark as seen
            self.mark_as_seen(award.id, award.title)

        self.logger.info(
            "nsf_discovery_complete",
            total_fetched=len(awards),
            new_grants=len(new_grants)
        )

        return new_grants

    async def run(self) -> int:
        """
        Execute the discovery process.

        Returns:
            Number of new grants discovered
        """
        try:
            # Discover new grants
            grants = await self.discover()

            if grants:
                # Publish to Redis stream
                self.publish_grants_batch(grants)

            # Update last check time
            self.set_last_check_time()

            return len(grants)

        except Exception as e:
            self.logger.error(
                "nsf_discovery_failed",
                error=str(e),
                exc_info=True
            )
            raise
        finally:
            await self.close_async()

    async def close_async(self) -> None:
        """Clean up async resources."""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
        self.close()


# ============================================================================
# Celery Tasks
# ============================================================================


@shared_task(
    name="agents.discovery.nsf_api.discover_nsf_grants",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 3},
    acks_late=True,
    time_limit=600,  # 10 minute time limit
    soft_time_limit=540,  # 9 minute soft limit
)
def discover_nsf_grants(self) -> dict[str, Any]:
    """
    Celery task to discover new NSF grants.

    Scheduled to run every 15 minutes.

    Returns:
        Dict with discovery results
    """
    logger = structlog.get_logger().bind(
        task_id=self.request.id,
        task_name="discover_nsf_grants"
    )

    logger.info("nsf_discovery_task_start")

    agent = NSFDiscoveryAgent()

    try:
        # Run the async discovery in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            count = loop.run_until_complete(agent.run())
        finally:
            loop.close()

        logger.info(
            "nsf_discovery_task_complete",
            grants_discovered=count
        )

        return {
            "status": "success",
            "grants_discovered": count,
            "source": "nsf"
        }

    except Exception as e:
        logger.error(
            "nsf_discovery_task_failed",
            error=str(e),
            exc_info=True
        )
        raise


# ============================================================================
# Celery Beat Schedule Entry
# ============================================================================

# Add this to your Celery beat schedule configuration:
#
# from celery.schedules import crontab
#
# beat_schedule = {
#     'discover-nsf-grants-every-15-minutes': {
#         'task': 'agents.discovery.nsf_api.discover_nsf_grants',
#         'schedule': crontab(minute='*/15'),
#     },
# }
