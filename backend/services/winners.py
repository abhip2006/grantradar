"""
Winners Service for querying funded grant projects from NIH and NSF.
Provides access to 2.6M+ funded projects with caching and aggregations.
"""

import logging
from collections import defaultdict
from typing import Any, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from backend.core.config import settings
from backend.services.cache import cache_key, get_cached, set_cached
from backend.schemas.winners import (
    FundedProject,
    FundedProjectOrg,
    FundedProjectPI,
    InstituteAggregation,
    InstitutionsResponse,
    InstitutionStats,
    MechanismAggregation,
    ProgramOfficer,
    ProgramOfficerProject,
    ProgramOfficersResponse,
    SearchAggregations,
    WinnersSearchRequest,
    WinnersSearchResponse,
    YearAggregation,
)

logger = logging.getLogger(__name__)

# NIH Institute name mappings
NIH_INSTITUTES = {
    "NCI": "National Cancer Institute",
    "NHLBI": "National Heart, Lung, and Blood Institute",
    "NIDDK": "National Institute of Diabetes and Digestive and Kidney Diseases",
    "NINDS": "National Institute of Neurological Disorders and Stroke",
    "NIAID": "National Institute of Allergy and Infectious Diseases",
    "NIA": "National Institute on Aging",
    "NICHD": "Eunice Kennedy Shriver National Institute of Child Health and Human Development",
    "NIMH": "National Institute of Mental Health",
    "NIGMS": "National Institute of General Medical Sciences",
    "NEI": "National Eye Institute",
    "NIEHS": "National Institute of Environmental Health Sciences",
    "NIDCD": "National Institute on Deafness and Other Communication Disorders",
    "NIDCR": "National Institute of Dental and Craniofacial Research",
    "NIAMS": "National Institute of Arthritis and Musculoskeletal and Skin Diseases",
    "NIAAA": "National Institute on Alcohol Abuse and Alcoholism",
    "NIDA": "National Institute on Drug Abuse",
    "NIBIB": "National Institute of Biomedical Imaging and Bioengineering",
    "NLM": "National Library of Medicine",
    "NCATS": "National Center for Advancing Translational Sciences",
    "NHGRI": "National Human Genome Research Institute",
    "NINR": "National Institute of Nursing Research",
    "NIMHD": "National Institute on Minority Health and Health Disparities",
    "FIC": "Fogarty International Center",
    "NCCIH": "National Center for Complementary and Integrative Health",
    "OD": "Office of the Director",
    "CIT": "Center for Information Technology",
    "CSR": "Center for Scientific Review",
    "CC": "Clinical Center",
}


class WinnersService:
    """
    Service for querying funded grant projects from NIH Reporter and NSF APIs.

    Provides search, aggregation, and analytics on historical funding data.
    """

    # API Configuration
    NIH_API_URL = settings.nih_reporter_api_url
    NSF_API_URL = settings.nsf_api_url
    RESULTS_PER_PAGE = 100  # NIH max is 500, but we paginate smaller for responsiveness

    def __init__(self):
        self.http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0),
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "User-Agent": "GrantRadar/1.0 (winners-intelligence)",
                },
            )
        return self.http_client

    async def close(self):
        """Close HTTP client."""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    )
    async def _query_nih_reporter(
        self,
        criteria: dict,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        Query the NIH Reporter API.

        Args:
            criteria: Search criteria dictionary
            limit: Number of results per page
            offset: Starting offset

        Returns:
            API response as dictionary
        """
        client = await self._get_client()

        payload = {
            "criteria": criteria,
            "limit": limit,
            "offset": offset,
            "sort_field": "award_notice_date",
            "sort_order": "desc",
        }

        logger.debug(f"NIH Reporter query: offset={offset}, limit={limit}")

        response = await client.post(
            self.NIH_API_URL,
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def _parse_nih_project(self, data: dict) -> FundedProject:
        """Parse NIH Reporter project data into FundedProject model."""
        # Extract PI info
        pis = data.get("principal_investigators", [])
        primary_pi = None
        if pis:
            pi_data = pis[0]
            name_parts = []
            if pi_data.get("first_name"):
                name_parts.append(pi_data["first_name"])
            if pi_data.get("middle_name"):
                name_parts.append(pi_data["middle_name"])
            if pi_data.get("last_name"):
                name_parts.append(pi_data["last_name"])

            primary_pi = FundedProjectPI(
                name=" ".join(name_parts) if name_parts else None,
                email=pi_data.get("email"),
                profile_id=pi_data.get("profile_id"),
            )

        # Extract organization info
        org_data = data.get("organization", {}) or {}
        org = (
            FundedProjectOrg(
                name=org_data.get("org_name"),
                city=org_data.get("org_city"),
                state=org_data.get("org_state"),
                country=org_data.get("org_country"),
            )
            if org_data
            else None
        )

        # Extract institute info
        agency_info = data.get("agency_ic_admin", {}) or {}
        institute_abbr = agency_info.get("abbreviation")
        institute_name = NIH_INSTITUTES.get(institute_abbr, agency_info.get("name"))

        # Parse project number for mechanism
        project_num = data.get("project_num", "")

        return FundedProject(
            project_num=project_num,
            title=data.get("project_title", "Untitled"),
            abstract=data.get("abstract_text"),
            award_amount=data.get("award_amount"),
            activity_code=data.get("activity_code"),
            mechanism=data.get("activity_code"),
            agency="NIH",
            institute=institute_abbr,
            institute_name=institute_name,
            fiscal_year=data.get("fiscal_year"),
            start_date=data.get("project_start_date"),
            end_date=data.get("project_end_date"),
            award_date=data.get("award_notice_date"),
            principal_investigator=primary_pi,
            organization=org,
            program_officer=data.get("program_officer_name"),
            terms=data.get("terms"),
            source_url=f"https://reporter.nih.gov/project-details/{project_num}",
        )

    async def search_projects(
        self,
        request: WinnersSearchRequest,
    ) -> WinnersSearchResponse:
        """
        Search funded projects from NIH Reporter.

        Args:
            request: Search parameters

        Returns:
            Search results with aggregations
        """
        # Build cache key
        cache_key_str = f"winners:search:{cache_key(request.model_dump())}"
        cached_result = get_cached(cache_key_str, ttl_minutes=15)
        if cached_result:
            return WinnersSearchResponse(**cached_result)

        # Build NIH criteria
        criteria: dict[str, Any] = {}

        # Keyword search
        if request.query:
            criteria["advanced_text_search"] = {
                "operator": "and",
                "search_field": "all",
                "search_text": request.query,
            }

        # Activity codes filter
        if request.activity_codes:
            criteria["activity_codes"] = request.activity_codes

        # Fiscal years filter
        if request.fiscal_years:
            criteria["fiscal_years"] = request.fiscal_years
        else:
            # Default to last 5 years
            from datetime import datetime

            current_year = datetime.now().year
            criteria["fiscal_years"] = list(range(current_year - 4, current_year + 1))

        # Institute filter
        if request.institute:
            criteria["agencies"] = [request.institute]

        # Institution filter
        if request.institution:
            criteria["org_names"] = [{"any_name": request.institution}]

        # PI name filter
        if request.pi_name:
            criteria["pi_names"] = [{"any_name": request.pi_name}]

        # State filter
        if request.state:
            criteria["org_states"] = [request.state]

        # Amount filter (note: NIH API doesn't support this directly, we filter post-query)

        # Calculate offset
        offset = (request.page - 1) * request.limit

        try:
            # Query NIH Reporter
            response = await self._query_nih_reporter(
                criteria=criteria,
                limit=request.limit,
                offset=offset,
            )

            # Parse results
            results = response.get("results", [])
            meta = response.get("meta", {})
            total = meta.get("total", 0)

            # Parse projects
            projects = []
            for project_data in results:
                try:
                    project = self._parse_nih_project(project_data)

                    # Apply amount filters (post-query)
                    if request.min_amount and project.award_amount:
                        if project.award_amount < request.min_amount:
                            continue
                    if request.max_amount and project.award_amount:
                        if project.award_amount > request.max_amount:
                            continue

                    projects.append(project)
                except Exception as e:
                    logger.warning(f"Failed to parse project: {e}")
                    continue

            # Build aggregations from full dataset (we'd need separate queries for accurate aggs)
            # For now, aggregate from the current page
            year_counts: dict[int, dict] = defaultdict(lambda: {"count": 0, "funding": 0})
            mechanism_counts: dict[str, dict] = defaultdict(lambda: {"count": 0, "total": 0})
            institute_counts: dict[str, int] = defaultdict(int)

            for project in projects:
                if project.fiscal_year:
                    year_counts[project.fiscal_year]["count"] += 1
                    year_counts[project.fiscal_year]["funding"] += project.award_amount or 0

                if project.activity_code:
                    mechanism_counts[project.activity_code]["count"] += 1
                    mechanism_counts[project.activity_code]["total"] += project.award_amount or 0

                if project.institute:
                    institute_counts[project.institute] += 1

            # Build aggregation models
            by_year = [
                YearAggregation(year=y, count=d["count"], total_funding=d["funding"])
                for y, d in sorted(year_counts.items(), reverse=True)
            ]

            by_mechanism = [
                MechanismAggregation(
                    code=code, count=d["count"], avg_award=d["total"] // d["count"] if d["count"] > 0 else None
                )
                for code, d in sorted(mechanism_counts.items(), key=lambda x: -x[1]["count"])
            ]

            by_institute = [
                InstituteAggregation(abbreviation=inst, name=NIH_INSTITUTES.get(inst), count=count)
                for inst, count in sorted(institute_counts.items(), key=lambda x: -x[1])
            ]

            # Calculate pages
            pages = (total + request.limit - 1) // request.limit if total > 0 else 1

            result = WinnersSearchResponse(
                results=projects,
                total=total,
                page=request.page,
                pages=pages,
                aggregations=SearchAggregations(
                    by_year=by_year,
                    by_mechanism=by_mechanism,
                    by_institute=by_institute,
                ),
            )

            # Cache result
            set_cached(cache_key_str, result.model_dump())

            return result

        except httpx.HTTPError as e:
            logger.error(f"NIH Reporter API error: {e}")
            raise

    async def get_program_officers(
        self,
        institute: Optional[str] = None,
        research_area: Optional[str] = None,
        limit: int = 20,
    ) -> ProgramOfficersResponse:
        """
        Get program officers with their funding patterns.

        Note: NIH Reporter doesn't have a dedicated PO endpoint,
        so we aggregate PO data from funded projects.

        Args:
            institute: Filter by NIH institute
            research_area: Filter by research area (keyword search)
            limit: Maximum officers to return

        Returns:
            Program officers with funding patterns
        """
        cache_key_str = f"winners:pos:{institute}:{research_area}:{limit}"
        cached_result = get_cached(cache_key_str, ttl_minutes=60)
        if cached_result:
            return ProgramOfficersResponse(**cached_result)

        # Build search criteria
        criteria: dict[str, Any] = {}

        from datetime import datetime

        current_year = datetime.now().year
        criteria["fiscal_years"] = [current_year, current_year - 1, current_year - 2]

        if institute:
            criteria["agencies"] = [institute]

        if research_area:
            criteria["advanced_text_search"] = {
                "operator": "and",
                "search_field": "all",
                "search_text": research_area,
            }

        try:
            # Fetch projects to aggregate PO data
            response = await self._query_nih_reporter(
                criteria=criteria,
                limit=500,  # Fetch more to get better PO coverage
                offset=0,
            )

            results = response.get("results", [])

            # Aggregate by program officer
            po_data: dict[str, dict] = defaultdict(
                lambda: {
                    "name": "",
                    "institute": "",
                    "projects": [],
                    "total_funding": 0,
                    "mechanisms": defaultdict(int),
                }
            )

            for project_data in results:
                po_name = project_data.get("program_officer_name")
                if not po_name:
                    continue

                # Get institute
                agency_info = project_data.get("agency_ic_admin", {}) or {}
                inst = agency_info.get("abbreviation", "")

                po_data[po_name]["name"] = po_name
                po_data[po_name]["institute"] = inst

                # Add project
                project = {
                    "project_num": project_data.get("project_num", ""),
                    "title": project_data.get("project_title", ""),
                    "award_amount": project_data.get("award_amount"),
                    "fiscal_year": project_data.get("fiscal_year"),
                    "activity_code": project_data.get("activity_code"),
                }
                po_data[po_name]["projects"].append(project)

                # Aggregate funding
                if project_data.get("award_amount"):
                    po_data[po_name]["total_funding"] += project_data["award_amount"]

                # Track mechanisms
                if project_data.get("activity_code"):
                    po_data[po_name]["mechanisms"][project_data["activity_code"]] += 1

            # Build PO models
            officers = []
            for po_name, data in sorted(po_data.items(), key=lambda x: -len(x[1]["projects"]))[:limit]:
                # Get top mechanisms
                top_mechanisms = sorted(data["mechanisms"].items(), key=lambda x: -x[1])[:5]

                # Get recent projects
                recent = sorted(data["projects"], key=lambda x: x.get("fiscal_year") or 0, reverse=True)[:5]

                officers.append(
                    ProgramOfficer(
                        name=data["name"],
                        institute=data["institute"],
                        institute_name=NIH_INSTITUTES.get(data["institute"]),
                        total_projects=len(data["projects"]),
                        total_funding=data["total_funding"],
                        avg_award_size=data["total_funding"] // len(data["projects"]) if data["projects"] else None,
                        top_mechanisms=[m[0] for m in top_mechanisms],
                        research_themes=[],  # Would need NLP to extract
                        recent_projects=[ProgramOfficerProject(**p) for p in recent],
                    )
                )

            result = ProgramOfficersResponse(
                officers=officers,
                total=len(officers),
            )

            set_cached(cache_key_str, result.model_dump())
            return result

        except httpx.HTTPError as e:
            logger.error(f"NIH Reporter API error: {e}")
            raise

    async def get_institution_stats(
        self,
        research_area: Optional[str] = None,
        mechanism: Optional[str] = None,
        fiscal_years: Optional[list[int]] = None,
        limit: int = 50,
    ) -> InstitutionsResponse:
        """
        Get institution success statistics.

        Args:
            research_area: Filter by research area
            mechanism: Filter by activity code
            fiscal_years: Years to analyze
            limit: Maximum institutions to return

        Returns:
            Institution statistics ranked by funding
        """
        cache_key_str = f"winners:institutions:{research_area}:{mechanism}:{fiscal_years}:{limit}"
        cached_result = get_cached(cache_key_str, ttl_minutes=60)
        if cached_result:
            return InstitutionsResponse(**cached_result)

        # Build search criteria
        criteria: dict[str, Any] = {}

        if fiscal_years:
            criteria["fiscal_years"] = fiscal_years
        else:
            from datetime import datetime

            current_year = datetime.now().year
            criteria["fiscal_years"] = [current_year, current_year - 1, current_year - 2]

        if mechanism:
            criteria["activity_codes"] = [mechanism]

        if research_area:
            criteria["advanced_text_search"] = {
                "operator": "and",
                "search_field": "all",
                "search_text": research_area,
            }

        try:
            # Fetch projects
            response = await self._query_nih_reporter(
                criteria=criteria,
                limit=500,
                offset=0,
            )

            results = response.get("results", [])

            # Aggregate by institution
            inst_data: dict[str, dict] = defaultdict(
                lambda: {
                    "name": "",
                    "city": "",
                    "state": "",
                    "awards": 0,
                    "funding": 0,
                    "mechanisms": defaultdict(int),
                    "pis": set(),
                }
            )

            for project_data in results:
                org = project_data.get("organization", {}) or {}
                org_name = org.get("org_name")
                if not org_name:
                    continue

                inst_data[org_name]["name"] = org_name
                inst_data[org_name]["city"] = org.get("org_city", "")
                inst_data[org_name]["state"] = org.get("org_state", "")
                inst_data[org_name]["awards"] += 1

                if project_data.get("award_amount"):
                    inst_data[org_name]["funding"] += project_data["award_amount"]

                if project_data.get("activity_code"):
                    inst_data[org_name]["mechanisms"][project_data["activity_code"]] += 1

                # Track PIs
                pis = project_data.get("principal_investigators", [])
                for pi in pis[:1]:  # Just primary PI
                    pi_name = f"{pi.get('first_name', '')} {pi.get('last_name', '')}".strip()
                    if pi_name:
                        inst_data[org_name]["pis"].add(pi_name)

            # Build institution models
            institutions = []
            sorted_insts = sorted(inst_data.items(), key=lambda x: -x[1]["funding"])[:limit]

            for rank, (org_name, data) in enumerate(sorted_insts, 1):
                top_mechanisms = sorted(data["mechanisms"].items(), key=lambda x: -x[1])[:5]

                top_pis = list(data["pis"])[:5]

                institutions.append(
                    InstitutionStats(
                        name=data["name"],
                        city=data["city"],
                        state=data["state"],
                        total_awards=data["awards"],
                        total_funding=data["funding"],
                        avg_award_size=data["funding"] // data["awards"] if data["awards"] > 0 else None,
                        top_mechanisms=[m[0] for m in top_mechanisms],
                        top_pis=top_pis,
                        rank=rank,
                    )
                )

            result = InstitutionsResponse(
                institutions=institutions,
                total=len(inst_data),
            )

            set_cached(cache_key_str, result.model_dump())
            return result

        except httpx.HTTPError as e:
            logger.error(f"NIH Reporter API error: {e}")
            raise


# Singleton instance
_winners_service: Optional[WinnersService] = None


def get_winners_service() -> WinnersService:
    """Get or create the winners service singleton."""
    global _winners_service
    if _winners_service is None:
        _winners_service = WinnersService()
    return _winners_service


async def cleanup_winners_service():
    """Clean up the winners service."""
    global _winners_service
    if _winners_service:
        await _winners_service.close()
        _winners_service = None
