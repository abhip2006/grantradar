"""
Discovery agent test fixtures.
Provides mock data and utilities for testing discovery agents.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock


@pytest.fixture
def mock_redis_client():
    """
    Mock Redis client for discovery agent tests.

    Provides mocked versions of Redis operations used by DiscoveryAgent base class.
    """
    redis = MagicMock()

    # Duplicate detection - default to not duplicate
    redis.sismember = MagicMock(return_value=False)
    redis.sadd = MagicMock(return_value=1)
    redis.expire = MagicMock(return_value=True)

    # Last check time - default to None (first run)
    redis.get = MagicMock(return_value=None)
    redis.set = MagicMock(return_value=True)

    # Stream publishing
    redis.xadd = MagicMock(return_value="1234567890-0")

    return redis


@pytest.fixture
def mock_http_client():
    """
    Mock async HTTP client for API tests.
    """
    client = AsyncMock()

    # Default successful response
    response = AsyncMock()
    response.status_code = 200
    response.raise_for_status = MagicMock()
    response.json = MagicMock(return_value={})

    client.get = AsyncMock(return_value=response)
    client.post = AsyncMock(return_value=response)
    client.aclose = AsyncMock()

    return client


@pytest.fixture
def sample_nsf_award():
    """Sample NSF Award Search API response data."""
    return {
        "id": "2529183",
        "title": "Machine Learning for Climate Science Research",
        "abstractText": "This project develops novel machine learning methods for climate modeling and prediction, focusing on neural network approaches to improve forecast accuracy.",
        "agency": "NSF",
        "fundsObligatedAmt": "797762",
        "date": "01/06/2025",
        "startDate": "06/01/2025",
        "expDate": "05/31/2028",
        "piFirstName": "Jane",
        "piLastName": "Smith",
        "piMiddeInitial": "A",
        "piEmail": "jsmith@stanford.edu",
        "awardeeName": "Stanford University",
        "awardeeCity": "Stanford",
        "awardeeStateCode": "CA",
        "awardeeZipCode": "94305",
        "fundProgramName": "Computer and Information Science",
        "primaryProgram": "AI Research",
        "cfdaNumber": "47.070",
        "awardInstrument": "Standard Grant",
    }


@pytest.fixture
def sample_nsf_api_response(sample_nsf_award):
    """Sample NSF Award Search API full response."""
    return {
        "response": {
            "award": [sample_nsf_award],
            "metadata": {
                "totalCount": 1,
            },
        }
    }


@pytest.fixture
def sample_nih_reporter_project():
    """Sample NIH Reporter API project data."""
    return {
        "project_num": "1R01CA123456-01",
        "project_title": "Novel Cancer Treatment Using Targeted Therapy",
        "abstract_text": "This research investigates new targeted therapy approaches for treating advanced stage cancer, focusing on genomic markers and personalized medicine strategies.",
        "phr_text": "This research will help develop new cancer treatments that are more effective and have fewer side effects.",
        "award_amount": 750000,
        "award_notice_date": "2025-01-15",
        "project_start_date": "2025-02-01",
        "project_end_date": "2028-01-31",
        "budget_start": "2025-02-01",
        "budget_end": "2026-01-31",
        "fiscal_year": 2025,
        "is_active": True,
        "activity_code": "R01",
        "award_type": "1",
        "direct_cost_amt": 500000,
        "indirect_cost_amt": 250000,
        "agency_ic_admin": {"abbreviation": "NCI", "name": "National Cancer Institute"},
        "agency_ic_fundings": [{"abbreviation": "NCI", "name": "National Cancer Institute"}],
        "principal_investigators": [
            {
                "first_name": "John",
                "last_name": "Doe",
                "middle_name": "B",
                "email": "jdoe@harvard.edu",
                "profile_id": 12345678,
            }
        ],
        "organization": {
            "org_name": "Harvard Medical School",
            "org_city": "Boston",
            "org_state": "MA",
            "org_country": "United States",
            "org_zipcode": "02115",
        },
        "opportunity_number": "PAR-24-001",
        "terms": "cancer, oncology, targeted therapy, genomics",
    }


@pytest.fixture
def sample_nih_reporter_api_response(sample_nih_reporter_project):
    """Sample NIH Reporter API full response."""
    return {
        "meta": {
            "total": 1,
            "offset": 0,
            "limit": 500,
        },
        "results": [sample_nih_reporter_project],
    }


@pytest.fixture
def sample_grants_gov_opportunity():
    """Sample Grants.gov opportunity data."""
    return {
        "opportunity_id": "HHS-2025-ACF-OCS-EE-0001",
        "opportunityTitle": "Community Economic Development Grant Program",
        "synopsis": "The Office of Community Services (OCS) is soliciting applications for community economic development projects that address the economic needs of individuals with low income.",
        "description": "This program provides funding for community-based organizations to implement strategies that create employment and business opportunities for low-income individuals.",
        "agencyCode": "HHS",
        "agencyName": "Department of Health and Human Services",
        "awardFloor": 50000,
        "awardCeiling": 800000,
        "estimatedTotalFunding": 15000000,
        "postedDate": "01/02/2025",
        "closeDate": "03/15/2025",
        "eligibleApplicants": [
            "Nonprofits with 501(c)(3) status",
            "State governments",
            "Local governments",
            "Native American tribal organizations",
        ],
        "cfda_numbers": ["93.570"],
        "categoryOfFunding": "Community Development",
        "costSharing": False,
        "opportunityNumber": "HHS-2025-ACF-OCS-EE-0001",
    }


@pytest.fixture
def sample_nih_foa():
    """Sample NIH Funding Opportunity Announcement (for scraper tests)."""
    return {
        "foa_number": "PAR-25-001",
        "title": "Research Project Grant (Parent R01 Clinical Trial Not Allowed)",
        "deadline": "2025-06-05",
        "url": "https://grants.nih.gov/grants/guide/pa-files/PAR-25-001.html",
        "description": "The NIH Research Project Grant (R01) supports a discrete, specified, circumscribed project in areas representing the investigator's specific interests and competencies.",
        "eligibility": "Eligible organizations include higher education institutions, nonprofits, for-profit organizations, governments, and other.",
    }


@pytest.fixture
def sample_nih_scraper_html():
    """Sample HTML content for NIH scraper tests."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>NIH Funding Opportunities</title></head>
    <body>
        <div id="funding-opportunities">
            <table>
                <tr>
                    <th>FOA Number</th>
                    <th>Title</th>
                    <th>Deadline</th>
                </tr>
                <tr>
                    <td><a href="/grants/guide/pa-files/PAR-25-001.html">PAR-25-001</a></td>
                    <td>Research Project Grant</td>
                    <td>June 5, 2025</td>
                </tr>
                <tr>
                    <td><a href="/grants/guide/rfa-files/RFA-CA-25-001.html">RFA-CA-25-001</a></td>
                    <td>Cancer Research Initiative</td>
                    <td>April 15, 2025</td>
                </tr>
            </table>
        </div>
        <script>var timestamp = "2025-01-07T10:30:00";</script>
    </body>
    </html>
    """


@pytest.fixture
def mock_nsf_agent(mock_redis_client, mock_http_client):
    """
    Create a mocked NSF Discovery Agent for testing.
    """
    from agents.discovery.nsf_api import NSFDiscoveryAgent

    agent = NSFDiscoveryAgent()
    agent._redis_client = mock_redis_client
    agent.http_client = mock_http_client

    return agent


@pytest.fixture
def mock_nih_reporter_agent(mock_redis_client, mock_http_client):
    """
    Create a mocked NIH Reporter Discovery Agent for testing.
    """
    from agents.discovery.nih_reporter import NIHReporterDiscoveryAgent

    agent = NIHReporterDiscoveryAgent()
    agent._redis_client = mock_redis_client
    agent.http_client = mock_http_client

    return agent


# Test helpers
def create_mock_response(data: dict, status_code: int = 200):
    """Create a mock HTTP response with given data."""
    response = AsyncMock()
    response.status_code = status_code
    response.raise_for_status = MagicMock()
    response.json = MagicMock(return_value=data)
    return response
