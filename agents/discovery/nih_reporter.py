"""
NIH Reporter API Discovery Agent
Discovers active funding opportunities from the NIH Reporter API.

This provides a reliable alternative to web scraping for NIH grant data.
API documentation: https://api.reporter.nih.gov/
"""
from datetime import datetime, timezone, timedelta
from decimal import Decimal
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


class NIHAgencyInfo(BaseModel):
    """NIH agency/institute information."""
    abbreviation: Optional[str] = None
    name: Optional[str] = None


class NIHOrganization(BaseModel):
    """Awardee organization information."""
    org_name: Optional[str] = None
    org_city: Optional[str] = None
    org_state: Optional[str] = None
    org_country: Optional[str] = None
    org_zipcode: Optional[str] = None


class NIHPrincipalInvestigator(BaseModel):
    """Principal investigator information."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    email: Optional[str] = None
    profile_id: Optional[int] = None

    def get_full_name(self) -> Optional[str]:
        """Get full PI name."""
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.middle_name:
            parts.append(self.middle_name)
        if self.last_name:
            parts.append(self.last_name)
        return " ".join(parts) if parts else None


class NIHReporterProject(BaseModel):
    """
    Model for NIH Reporter API project data.

    Maps the JSON response from the NIH Reporter Projects Search API.
    """
    # Core identifiers
    project_num: str = Field(..., description="Project number (unique ID)")
    project_title: str = Field(..., description="Project title")

    # Funding details
    award_amount: Optional[int] = Field(default=None, description="Award amount in dollars")
    award_notice_date: Optional[str] = Field(default=None, description="Award notice date")

    # Project timeline
    project_start_date: Optional[str] = Field(default=None, description="Project start date")
    project_end_date: Optional[str] = Field(default=None, description="Project end date")
    budget_start: Optional[str] = Field(default=None, description="Budget period start")
    budget_end: Optional[str] = Field(default=None, description="Budget period end")

    # Content
    abstract_text: Optional[str] = Field(default=None, alias="abstract_text", description="Project abstract")
    phr_text: Optional[str] = Field(default=None, description="Public health relevance")
    terms: Optional[str] = Field(default=None, description="Terms/keywords")

    # Agency info
    agency_ic_admin: Optional[NIHAgencyInfo] = Field(default=None, description="Administering IC")
    agency_ic_fundings: Optional[list[NIHAgencyInfo]] = Field(default=None, description="Funding ICs")

    # Organization and PI
    organization: Optional[NIHOrganization] = Field(default=None, description="Awardee organization")
    principal_investigators: Optional[list[NIHPrincipalInvestigator]] = Field(
        default=None,
        description="Principal investigators"
    )

    # Additional metadata
    fiscal_year: Optional[int] = Field(default=None, description="Fiscal year")
    is_active: Optional[bool] = Field(default=None, description="Whether project is active")
    activity_code: Optional[str] = Field(default=None, description="Activity code (R01, R21, etc.)")
    award_type: Optional[str] = Field(default=None, description="Award type")
    direct_cost_amt: Optional[int] = Field(default=None, description="Direct costs")
    indirect_cost_amt: Optional[int] = Field(default=None, description="Indirect costs")

    # FOA information
    opportunity_number: Optional[str] = Field(default=None, description="FOA number if linked")

    class Config:
        populate_by_name = True

    @field_validator("award_amount", "direct_cost_amt", "indirect_cost_amt", mode="before")
    @classmethod
    def parse_amount(cls, v: Any) -> Optional[int]:
        """Parse amount to integer."""
        if v is None:
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, float):
            return int(v)
        if isinstance(v, str):
            try:
                cleaned = v.replace(",", "").replace("$", "").strip()
                return int(float(cleaned)) if cleaned else None
            except ValueError:
                return None
        return None

    def get_agency_name(self) -> str:
        """Get full agency name."""
        if self.agency_ic_admin and self.agency_ic_admin.name:
            return self.agency_ic_admin.name
        if self.agency_ic_admin and self.agency_ic_admin.abbreviation:
            return f"NIH/{self.agency_ic_admin.abbreviation}"
        return "NIH"

    def get_agency_abbreviation(self) -> Optional[str]:
        """Get agency abbreviation."""
        if self.agency_ic_admin and self.agency_ic_admin.abbreviation:
            return self.agency_ic_admin.abbreviation
        return None

    def get_primary_pi(self) -> Optional[NIHPrincipalInvestigator]:
        """Get primary PI."""
        if self.principal_investigators:
            return self.principal_investigators[0]
        return None

    def get_project_url(self) -> str:
        """Generate NIH Reporter project URL."""
        return f"https://reporter.nih.gov/project-details/{self.project_num}"


class NIHSearchCriteria(BaseModel):
    """Search criteria for NIH Reporter API."""
    fiscal_years: Optional[list[int]] = None
    is_active: Optional[bool] = None
    newly_added_projects_only: Optional[bool] = None
    include_active_projects: Optional[bool] = None
    activity_codes: Optional[list[str]] = None
    agencies: Optional[list[str]] = None
    org_names: Optional[list[str]] = None
    org_states: Optional[list[str]] = None
    pi_names: Optional[list[dict]] = None
    advanced_text_search: Optional[dict] = None
    project_nums: Optional[list[str]] = None
    date_range: Optional[dict] = None


class NIHSearchRequest(BaseModel):
    """Request payload for NIH Reporter search."""
    criteria: NIHSearchCriteria = Field(default_factory=NIHSearchCriteria)
    limit: int = Field(default=500, ge=1, le=500)
    offset: int = Field(default=0, ge=0)
    sort_field: Optional[str] = Field(default="project_start_date")
    sort_order: Optional[str] = Field(default="desc")


class DiscoveredGrant(BaseModel):
    """
    Normalized grant data structure for publishing.

    This is the standard format used across all discovery agents.
    """
    external_id: str = Field(..., description="External ID from source (project_num)")
    source: str = Field(default="nih_reporter", description="Data source identifier")
    title: str = Field(..., description="Grant title")
    description: Optional[str] = Field(default=None, description="Grant description/abstract")

    # Funding details
    amount: Optional[int] = Field(default=None, description="Award amount")
    amount_min: Optional[int] = Field(default=None, description="Minimum award amount")
    amount_max: Optional[int] = Field(default=None, description="Maximum award amount")

    # Dates
    start_date: Optional[str] = Field(default=None, description="Start date (ISO format)")
    end_date: Optional[str] = Field(default=None, description="End date (ISO format)")
    posted_date: Optional[str] = Field(default=None, description="Award notice date (ISO format)")

    # Organization
    funding_agency: str = Field(default="NIH", description="Funding agency")
    agency_abbreviation: Optional[str] = Field(default=None, description="Agency abbreviation (NCI, NIMH, etc.)")
    program_name: Optional[str] = Field(default=None, description="Activity code/program")
    opportunity_number: Optional[str] = Field(default=None, description="FOA number if available")

    # Awardee/Institution info
    institution_name: Optional[str] = Field(default=None, description="Awardee institution")
    institution_city: Optional[str] = Field(default=None, description="Institution city")
    institution_state: Optional[str] = Field(default=None, description="Institution state")

    # PI Information
    pi_name: Optional[str] = Field(default=None, description="Principal Investigator name")
    pi_email: Optional[str] = Field(default=None, description="PI email")

    # Metadata
    source_url: Optional[str] = Field(default=None, description="URL to NIH Reporter")
    fiscal_year: Optional[int] = Field(default=None, description="Fiscal year")
    is_active: Optional[bool] = Field(default=None, description="Active project flag")
    raw_data: Optional[dict[str, Any]] = Field(default=None, description="Original API response")


# ============================================================================
# NIH Reporter Discovery Agent
# ============================================================================


class NIHReporterDiscoveryAgent(DiscoveryAgent):
    """
    Discovery agent for the NIH Reporter Projects API.

    Fetches active projects from NIH Reporter and publishes them to the grants stream.
    This provides more reliable data than web scraping.
    """

    # NIH Reporter API configuration
    API_URL = settings.nih_reporter_api_url
    RESULTS_PER_PAGE = 500  # Max allowed by API
    MAX_PAGES = 100  # Safety limit

    def __init__(self):
        super().__init__(source_name="nih_reporter")
        self.http_client: Optional[httpx.AsyncClient] = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0),  # Longer timeout for large responses
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "User-Agent": "GrantRadar/1.0 (grant-discovery-agent)"
                }
            )
        return self.http_client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        before_sleep=lambda retry_state: structlog.get_logger().warning(
            "nih_reporter_api_retry",
            attempt=retry_state.attempt_number,
            wait=retry_state.next_action.sleep
        )
    )
    async def _fetch_page(self, request: NIHSearchRequest) -> dict[str, Any]:
        """
        Fetch a single page of results from the NIH Reporter API.

        Args:
            request: Search request parameters

        Returns:
            API response as dictionary

        Raises:
            httpx.HTTPError: On network/HTTP errors after retries
        """
        client = await self._get_http_client()

        self.logger.debug(
            "nih_reporter_api_request",
            offset=request.offset,
            limit=request.limit,
        )

        response = await client.post(
            self.API_URL,
            json=request.model_dump(exclude_none=True),
        )
        response.raise_for_status()

        data = response.json()
        return data

    def _parse_nih_date(self, date_str: Optional[str]) -> Optional[str]:
        """
        Parse NIH date format to ISO format.

        NIH Reporter uses various formats including YYYY-MM-DD and MM/DD/YYYY.

        Args:
            date_str: Date string from API

        Returns:
            ISO format date string or None
        """
        if not date_str:
            return None

        # Common formats used by NIH Reporter
        formats = [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%m/%d/%Y",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.split("T")[0] if "T" in date_str else date_str, fmt.split("T")[0])
                return dt.date().isoformat()
            except ValueError:
                continue

        self.logger.warning("invalid_date_format", date_str=date_str)
        return None

    def _normalize_project(self, project: NIHReporterProject) -> DiscoveredGrant:
        """
        Convert NIH Reporter project to normalized DiscoveredGrant.

        Args:
            project: NIH Reporter project model

        Returns:
            Normalized DiscoveredGrant
        """
        # Get PI info
        primary_pi = project.get_primary_pi()
        pi_name = primary_pi.get_full_name() if primary_pi else None
        pi_email = primary_pi.email if primary_pi else None

        # Get organization info
        org = project.organization
        institution_name = org.org_name if org else None
        institution_city = org.org_city if org else None
        institution_state = org.org_state if org else None

        return DiscoveredGrant(
            external_id=project.project_num,
            source="nih_reporter",
            title=project.project_title,
            description=project.abstract_text or project.phr_text,
            amount=project.award_amount,
            amount_min=project.award_amount,  # NIH typically has single amount
            amount_max=project.award_amount,
            start_date=self._parse_nih_date(project.project_start_date),
            end_date=self._parse_nih_date(project.project_end_date),
            posted_date=self._parse_nih_date(project.award_notice_date),
            funding_agency=project.get_agency_name(),
            agency_abbreviation=project.get_agency_abbreviation(),
            program_name=project.activity_code,
            opportunity_number=project.opportunity_number,
            institution_name=institution_name,
            institution_city=institution_city,
            institution_state=institution_state,
            pi_name=pi_name,
            pi_email=pi_email,
            source_url=project.get_project_url(),
            fiscal_year=project.fiscal_year,
            is_active=project.is_active,
            raw_data=project.model_dump(mode="json"),
        )

    async def _fetch_all_pages(
        self,
        base_request: NIHSearchRequest
    ) -> list[NIHReporterProject]:
        """
        Fetch all pages of results from the NIH Reporter API.

        Args:
            base_request: Base search request

        Returns:
            List of all projects across all pages
        """
        all_projects: list[NIHReporterProject] = []
        current_offset = 0
        page_count = 0

        while page_count < self.MAX_PAGES:
            request = base_request.model_copy(update={"offset": current_offset})

            try:
                response_data = await self._fetch_page(request)
            except httpx.HTTPError as e:
                self.logger.error(
                    "nih_reporter_api_fetch_failed",
                    offset=current_offset,
                    error=str(e)
                )
                break

            # Parse response structure
            meta = response_data.get("meta", {})
            total = meta.get("total", 0)
            results = response_data.get("results", [])

            if not results:
                self.logger.info(
                    "nih_reporter_api_no_more_results",
                    offset=current_offset,
                    total_fetched=len(all_projects)
                )
                break

            # Parse projects
            for project_data in results:
                try:
                    project = NIHReporterProject.model_validate(project_data)
                    all_projects.append(project)
                except Exception as e:
                    self.logger.warning(
                        "nih_reporter_project_parse_failed",
                        project_num=project_data.get("project_num"),
                        error=str(e)
                    )

            self.logger.info(
                "nih_reporter_api_page_fetched",
                offset=current_offset,
                projects_in_page=len(results),
                total_fetched=len(all_projects),
                total_available=total
            )

            # Check if we've fetched all results
            if current_offset + len(results) >= total:
                break

            current_offset += self.RESULTS_PER_PAGE
            page_count += 1

            # Rate limiting - be nice to the API
            await asyncio.sleep(0.5)

        return all_projects

    def _get_current_fiscal_year(self) -> int:
        """Get current federal fiscal year (Oct 1 - Sep 30)."""
        now = datetime.now(timezone.utc)
        # FY starts in October
        if now.month >= 10:
            return now.year + 1
        return now.year

    async def discover(self) -> list[dict[str, Any]]:
        """
        Discover new grants from NIH Reporter.

        Returns:
            List of normalized grant data dictionaries
        """
        # Build search criteria for active projects
        current_fy = self._get_current_fiscal_year()

        criteria = NIHSearchCriteria(
            fiscal_years=[current_fy, current_fy - 1],  # Current and previous FY
            is_active=True,
        )

        # Check if we have a last check time
        last_check = self.get_last_check_time()
        if last_check:
            # Only get newly added projects since last check
            criteria.newly_added_projects_only = True
            # Add date range filter
            criteria.date_range = {
                "from_date": last_check.strftime("%Y-%m-%d"),
                "to_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            }

        request = NIHSearchRequest(
            criteria=criteria,
            limit=self.RESULTS_PER_PAGE,
            offset=0,
            sort_field="project_start_date",
            sort_order="desc",
        )

        self.logger.info(
            "nih_reporter_discovery_start",
            fiscal_years=criteria.fiscal_years,
            is_active=criteria.is_active,
            newly_added=criteria.newly_added_projects_only,
        )

        # Fetch all projects
        projects = await self._fetch_all_pages(request)

        self.logger.info(
            "nih_reporter_projects_fetched",
            total_projects=len(projects)
        )

        # Filter duplicates and normalize
        new_grants: list[dict[str, Any]] = []

        for project in projects:
            # Check for duplicates
            if self.is_duplicate(project.project_num, project.project_title):
                self.logger.debug(
                    "nih_reporter_project_duplicate",
                    project_num=project.project_num
                )
                continue

            # Normalize and add
            grant = self._normalize_project(project)
            new_grants.append(grant.model_dump(mode="json"))

            # Mark as seen
            self.mark_as_seen(project.project_num, project.project_title)

        self.logger.info(
            "nih_reporter_discovery_complete",
            total_fetched=len(projects),
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
                "nih_reporter_discovery_failed",
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
    name="agents.discovery.nih_reporter.discover_nih_reporter_grants",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 3},
    acks_late=True,
    time_limit=900,  # 15 minute time limit
    soft_time_limit=840,  # 14 minute soft limit
)
def discover_nih_reporter_grants(self) -> dict[str, Any]:
    """
    Celery task to discover new NIH Reporter grants.

    Scheduled to run every 15 minutes.

    Returns:
        Dict with discovery results
    """
    logger = structlog.get_logger().bind(
        task_id=self.request.id,
        task_name="discover_nih_reporter_grants"
    )

    logger.info("nih_reporter_discovery_task_start")

    agent = NIHReporterDiscoveryAgent()

    try:
        # Run the async discovery in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            count = loop.run_until_complete(agent.run())
        finally:
            loop.close()

        logger.info(
            "nih_reporter_discovery_task_complete",
            grants_discovered=count
        )

        return {
            "status": "success",
            "grants_discovered": count,
            "source": "nih_reporter"
        }

    except Exception as e:
        logger.error(
            "nih_reporter_discovery_task_failed",
            error=str(e),
            exc_info=True
        )
        raise
