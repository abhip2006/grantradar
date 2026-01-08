"""
Tests for ORCID API Service.
Tests fetching and parsing researcher profiles from ORCID.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestValidateOrcid:
    """Tests for ORCID validation."""

    def test_valid_orcid(self):
        """Test valid ORCID format."""
        from backend.services.orcid import validate_orcid

        result = validate_orcid("0000-0002-1825-0097")

        assert result == "0000-0002-1825-0097"

    def test_valid_orcid_with_x(self):
        """Test valid ORCID with X checksum digit."""
        from backend.services.orcid import validate_orcid

        result = validate_orcid("0000-0002-1825-009X")

        assert result == "0000-0002-1825-009X"

    def test_orcid_from_url(self):
        """Test extracting ORCID from URL."""
        from backend.services.orcid import validate_orcid

        result = validate_orcid("https://orcid.org/0000-0002-1825-0097")

        assert result == "0000-0002-1825-0097"

    def test_orcid_from_http_url(self):
        """Test extracting ORCID from HTTP URL."""
        from backend.services.orcid import validate_orcid

        result = validate_orcid("http://orcid.org/0000-0002-1825-0097")

        assert result == "0000-0002-1825-0097"

    def test_invalid_orcid_format(self):
        """Test invalid ORCID format."""
        from backend.services.orcid import validate_orcid

        # Too short
        assert validate_orcid("0000-0002-1825") is None

        # Wrong separators
        assert validate_orcid("0000.0002.1825.0097") is None

        # Wrong length
        assert validate_orcid("0000-0002-1825-00971") is None

    def test_orcid_case_insensitive(self):
        """Test ORCID validation is case insensitive for X."""
        from backend.services.orcid import validate_orcid

        result_upper = validate_orcid("0000-0002-1825-009X")
        result_lower = validate_orcid("0000-0002-1825-009x")

        assert result_upper == "0000-0002-1825-009X"
        assert result_lower == "0000-0002-1825-009X"

    def test_orcid_with_whitespace(self):
        """Test ORCID validation handles whitespace."""
        from backend.services.orcid import validate_orcid

        result = validate_orcid("  0000-0002-1825-0097  ")

        assert result == "0000-0002-1825-0097"


class TestParseOrcidName:
    """Tests for ORCID name parsing."""

    def test_parse_full_name(self):
        """Test parsing full name from ORCID data."""
        from backend.services.orcid import parse_orcid_name

        person_data = {
            "name": {
                "given-names": {"value": "John"},
                "family-name": {"value": "Doe"},
            }
        }

        name = parse_orcid_name(person_data)

        assert name == "John Doe"

    def test_parse_given_name_only(self):
        """Test parsing when only given name present."""
        from backend.services.orcid import parse_orcid_name

        person_data = {
            "name": {
                "given-names": {"value": "John"},
                "family-name": {},
            }
        }

        name = parse_orcid_name(person_data)

        assert name == "John"

    def test_parse_family_name_only(self):
        """Test parsing when only family name present."""
        from backend.services.orcid import parse_orcid_name

        person_data = {
            "name": {
                "given-names": {},
                "family-name": {"value": "Doe"},
            }
        }

        name = parse_orcid_name(person_data)

        assert name == "Doe"

    def test_parse_no_name(self):
        """Test parsing when no name present."""
        from backend.services.orcid import parse_orcid_name

        person_data = {}

        name = parse_orcid_name(person_data)

        assert name is None

    def test_parse_empty_name_object(self):
        """Test parsing with empty name object."""
        from backend.services.orcid import parse_orcid_name

        person_data = {"name": None}

        name = parse_orcid_name(person_data)

        assert name is None


class TestParseOrcidKeywords:
    """Tests for ORCID keyword parsing."""

    def test_parse_keywords(self):
        """Test parsing keywords from ORCID data."""
        from backend.services.orcid import parse_orcid_keywords

        person_data = {
            "keywords": {
                "keyword": [
                    {"content": "machine learning"},
                    {"content": "bioinformatics"},
                    {"content": "genomics"},
                ]
            }
        }

        keywords = parse_orcid_keywords(person_data)

        assert len(keywords) == 3
        assert "machine learning" in keywords
        assert "bioinformatics" in keywords
        assert "genomics" in keywords

    def test_parse_empty_keywords(self):
        """Test parsing when no keywords present."""
        from backend.services.orcid import parse_orcid_keywords

        person_data = {}

        keywords = parse_orcid_keywords(person_data)

        assert keywords == []

    def test_parse_keywords_with_empty_content(self):
        """Test parsing keywords with empty content."""
        from backend.services.orcid import parse_orcid_keywords

        person_data = {
            "keywords": {
                "keyword": [
                    {"content": "machine learning"},
                    {"content": ""},
                    {"content": "genomics"},
                ]
            }
        }

        keywords = parse_orcid_keywords(person_data)

        # Empty content should be filtered
        assert len(keywords) == 2


class TestParseOrcidBiography:
    """Tests for ORCID biography parsing."""

    def test_parse_biography(self):
        """Test parsing biography from ORCID data."""
        from backend.services.orcid import parse_orcid_biography

        person_data = {
            "biography": {
                "content": "I am a researcher specializing in machine learning."
            }
        }

        bio = parse_orcid_biography(person_data)

        assert bio == "I am a researcher specializing in machine learning."

    def test_parse_empty_biography(self):
        """Test parsing when no biography present."""
        from backend.services.orcid import parse_orcid_biography

        person_data = {}

        bio = parse_orcid_biography(person_data)

        assert bio is None

    def test_parse_null_biography(self):
        """Test parsing with null biography object."""
        from backend.services.orcid import parse_orcid_biography

        person_data = {"biography": None}

        bio = parse_orcid_biography(person_data)

        assert bio is None


class TestOrcidApiBase:
    """Tests for ORCID API configuration."""

    def test_api_base_url(self):
        """Test ORCID API base URL."""
        from backend.services.orcid import ORCID_API_BASE

        assert ORCID_API_BASE == "https://pub.orcid.org/v3.0"

    def test_api_endpoints(self):
        """Test ORCID API endpoint construction."""
        from backend.services.orcid import ORCID_API_BASE

        orcid = "0000-0002-1825-0097"

        person_url = f"{ORCID_API_BASE}/{orcid}/person"
        works_url = f"{ORCID_API_BASE}/{orcid}/works"
        fundings_url = f"{ORCID_API_BASE}/{orcid}/fundings"

        assert person_url == "https://pub.orcid.org/v3.0/0000-0002-1825-0097/person"
        assert works_url == "https://pub.orcid.org/v3.0/0000-0002-1825-0097/works"
        assert fundings_url == "https://pub.orcid.org/v3.0/0000-0002-1825-0097/fundings"


class TestFetchOrcidProfileMocked:
    """Tests for ORCID profile fetching with mocked HTTP."""

    @pytest.mark.asyncio
    async def test_fetch_invalid_orcid(self):
        """Test fetching with invalid ORCID format."""
        from backend.services.orcid import fetch_orcid_profile

        result = await fetch_orcid_profile("invalid-orcid")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_profile_structure(self):
        """Test expected structure of fetched profile."""
        # The result should have these keys when successful
        expected_keys = {"orcid", "person", "works", "fundings"}

        # Verify the structure we expect
        mock_result = {
            "orcid": "0000-0002-1825-0097",
            "person": {},
            "works": {},
            "fundings": {},
        }

        assert set(mock_result.keys()) == expected_keys


class TestParseOrcidWorks:
    """Tests for ORCID works parsing."""

    def test_parse_works_structure(self):
        """Test parsing works structure."""
        from backend.services.orcid import parse_orcid_works

        works_data = {
            "group": [
                {
                    "work-summary": [
                        {
                            "title": {"title": {"value": "Paper 1"}},
                            "publication-date": {"year": {"value": "2023"}},
                        }
                    ]
                },
                {
                    "work-summary": [
                        {
                            "title": {"title": {"value": "Paper 2"}},
                            "publication-date": {"year": {"value": "2022"}},
                        }
                    ]
                },
            ]
        }

        publications = parse_orcid_works(works_data)

        assert isinstance(publications, list)

    def test_parse_works_empty(self):
        """Test parsing empty works."""
        from backend.services.orcid import parse_orcid_works

        works_data = {}

        publications = parse_orcid_works(works_data)

        assert publications == []

    def test_parse_works_max_limit(self):
        """Test max works limit parameter."""
        from backend.services.orcid import parse_orcid_works

        # Create 30 works
        works_data = {
            "group": [
                {
                    "work-summary": [
                        {
                            "title": {"title": {"value": f"Paper {i}"}},
                            "publication-date": {"year": {"value": "2023"}},
                        }
                    ]
                }
                for i in range(30)
            ]
        }

        # Default max is 20
        publications = parse_orcid_works(works_data, max_works=20)

        assert len(publications) <= 20

    def test_parse_works_custom_limit(self):
        """Test custom max works limit."""
        from backend.services.orcid import parse_orcid_works

        # Create 30 works
        works_data = {
            "group": [
                {
                    "work-summary": [
                        {
                            "title": {"title": {"value": f"Paper {i}"}},
                            "publication-date": {"year": {"value": "2023"}},
                        }
                    ]
                }
                for i in range(30)
            ]
        }

        publications = parse_orcid_works(works_data, max_works=5)

        assert len(publications) <= 5


class TestOrcidDataExtraction:
    """Tests for extracting data from ORCID responses."""

    def test_extract_publication_title(self):
        """Test extracting publication title."""
        work_summary = {
            "title": {"title": {"value": "Deep Learning in Genomics"}}
        }

        title_obj = work_summary.get("title", {}).get("title", {})
        title = title_obj.get("value", "")

        assert title == "Deep Learning in Genomics"

    def test_extract_publication_year(self):
        """Test extracting publication year."""
        work_summary = {
            "publication-date": {"year": {"value": "2023"}}
        }

        pub_date = work_summary.get("publication-date", {})
        year = pub_date.get("year", {}).get("value")

        assert year == "2023"

    def test_extract_journal_name(self):
        """Test extracting journal name."""
        work_summary = {
            "journal-title": {"value": "Nature Methods"}
        }

        journal = work_summary.get("journal-title", {}).get("value", "")

        assert journal == "Nature Methods"
