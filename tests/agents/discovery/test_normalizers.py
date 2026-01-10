"""
Tests for grant data normalizers.
"""

from decimal import Decimal

from agents.discovery.normalizers import (
    GrantNormalizer,
    NSFNormalizer,
    NIHReporterNormalizer,
    GrantsGovNormalizer,
)


class TestGrantNormalizerAmountParsing:
    """Tests for amount parsing utility."""

    def test_parse_integer(self):
        """Test parsing integer amounts."""
        assert GrantNormalizer.parse_amount(500000) == 500000
        assert GrantNormalizer.parse_amount(0) == 0

    def test_parse_float(self):
        """Test parsing float amounts."""
        assert GrantNormalizer.parse_amount(500000.50) == 500000
        assert GrantNormalizer.parse_amount(123.99) == 123

    def test_parse_decimal(self):
        """Test parsing Decimal amounts."""
        assert GrantNormalizer.parse_amount(Decimal("500000")) == 500000
        assert GrantNormalizer.parse_amount(Decimal("123.45")) == 123

    def test_parse_string_with_commas(self):
        """Test parsing string amounts with commas."""
        assert GrantNormalizer.parse_amount("500,000") == 500000
        assert GrantNormalizer.parse_amount("1,234,567") == 1234567

    def test_parse_string_with_currency(self):
        """Test parsing string amounts with currency symbols."""
        assert GrantNormalizer.parse_amount("$500,000") == 500000
        assert GrantNormalizer.parse_amount("$1234567") == 1234567

    def test_parse_string_with_k_suffix(self):
        """Test parsing string amounts with K suffix."""
        assert GrantNormalizer.parse_amount("500K") == 500000
        assert GrantNormalizer.parse_amount("500k") == 500000
        assert GrantNormalizer.parse_amount("1.5K") == 1500

    def test_parse_string_with_m_suffix(self):
        """Test parsing string amounts with M suffix."""
        assert GrantNormalizer.parse_amount("1M") == 1000000
        assert GrantNormalizer.parse_amount("1.5M") == 1500000
        assert GrantNormalizer.parse_amount("2.5m") == 2500000

    def test_parse_none(self):
        """Test parsing None returns None."""
        assert GrantNormalizer.parse_amount(None) is None

    def test_parse_empty_string(self):
        """Test parsing empty string returns None."""
        assert GrantNormalizer.parse_amount("") is None
        assert GrantNormalizer.parse_amount("   ") is None

    def test_parse_invalid_string(self):
        """Test parsing invalid string returns None."""
        assert GrantNormalizer.parse_amount("not a number") is None
        assert GrantNormalizer.parse_amount("abc123") is None


class TestGrantNormalizerDateParsing:
    """Tests for date parsing utility."""

    def test_parse_iso_format(self):
        """Test parsing ISO date format."""
        assert GrantNormalizer.parse_date("2025-01-15") == "2025-01-15"
        assert GrantNormalizer.parse_date("2025-12-31") == "2025-12-31"

    def test_parse_iso_with_time(self):
        """Test parsing ISO datetime format."""
        assert GrantNormalizer.parse_date("2025-01-15T10:30:00") == "2025-01-15"
        assert GrantNormalizer.parse_date("2025-01-15T10:30:00Z") == "2025-01-15"

    def test_parse_us_format(self):
        """Test parsing US date format (MM/DD/YYYY)."""
        assert GrantNormalizer.parse_date("01/15/2025") == "2025-01-15"
        assert GrantNormalizer.parse_date("12/31/2025") == "2025-12-31"

    def test_parse_none(self):
        """Test parsing None returns None."""
        assert GrantNormalizer.parse_date(None) is None

    def test_parse_empty_string(self):
        """Test parsing empty string returns None."""
        assert GrantNormalizer.parse_date("") is None
        assert GrantNormalizer.parse_date("   ") is None

    def test_parse_invalid_format(self):
        """Test parsing invalid format returns None."""
        assert GrantNormalizer.parse_date("not a date") is None
        assert GrantNormalizer.parse_date("2025/13/45") is None


class TestGrantNormalizerAgencyNormalization:
    """Tests for agency name normalization."""

    def test_normalize_nsf(self):
        """Test NSF normalization."""
        assert GrantNormalizer.normalize_agency("NSF") == "National Science Foundation"
        assert GrantNormalizer.normalize_agency("nsf") == "National Science Foundation"

    def test_normalize_nih(self):
        """Test NIH normalization."""
        assert GrantNormalizer.normalize_agency("NIH") == "National Institutes of Health"
        assert GrantNormalizer.normalize_agency("nih") == "National Institutes of Health"

    def test_normalize_nih_with_institute(self):
        """Test NIH with institute abbreviation."""
        result = GrantNormalizer.normalize_agency("NIH", "NCI")
        assert "National Institutes of Health" in result
        assert "National Cancer Institute" in result

    def test_normalize_unknown_agency(self):
        """Test unknown agency returns as-is."""
        assert GrantNormalizer.normalize_agency("Some Agency") == "Some Agency"
        assert GrantNormalizer.normalize_agency("Custom Foundation") == "Custom Foundation"

    def test_normalize_none(self):
        """Test None agency returns default."""
        assert GrantNormalizer.normalize_agency(None) == "Unknown Agency"


class TestGrantNormalizerTextCleaning:
    """Tests for text cleaning utility."""

    def test_clean_whitespace(self):
        """Test whitespace normalization."""
        assert GrantNormalizer.clean_text("  hello   world  ") == "hello world"
        assert GrantNormalizer.clean_text("multiple\n\nlines") == "multiple lines"

    def test_clean_with_max_length(self):
        """Test truncation to max length."""
        text = "This is a very long text that should be truncated"
        result = GrantNormalizer.clean_text(text, max_length=20)
        assert len(result) == 20
        assert result.endswith("...")

    def test_clean_none(self):
        """Test None returns None."""
        assert GrantNormalizer.clean_text(None) is None

    def test_clean_empty_string(self):
        """Test empty string returns None."""
        assert GrantNormalizer.clean_text("") is None
        assert GrantNormalizer.clean_text("   ") is None


class TestGrantNormalizerCategoryExtraction:
    """Tests for category extraction utility."""

    def test_extract_biomedical(self):
        """Test biomedical category extraction."""
        categories = GrantNormalizer.extract_categories(description="This health research addresses medical treatment")
        assert "biomedical" in categories

    def test_extract_cancer(self):
        """Test cancer category extraction."""
        categories = GrantNormalizer.extract_categories(description="Novel approaches to tumor oncology research")
        assert "cancer" in categories

    def test_extract_ai_ml(self):
        """Test AI/ML category extraction."""
        categories = GrantNormalizer.extract_categories(
            program_name="Machine Learning", description="Deep learning and neural network methods"
        )
        assert "ai_ml" in categories

    def test_extract_multiple_categories(self):
        """Test extracting multiple categories."""
        categories = GrantNormalizer.extract_categories(description="Machine learning for cancer genomics research")
        assert len(categories) >= 2

    def test_extract_from_keywords(self):
        """Test extraction from keywords."""
        categories = GrantNormalizer.extract_categories(keywords="climate, sustainability, environment")
        assert "climate" in categories

    def test_extract_empty(self):
        """Test empty inputs return empty list."""
        assert GrantNormalizer.extract_categories() == []
        assert GrantNormalizer.extract_categories(description="") == []


class TestNSFNormalizer:
    """Tests for NSF-specific normalization."""

    def test_normalize_complete_award(self, sample_nsf_award):
        """Test normalizing a complete NSF award."""
        result = NSFNormalizer.normalize(sample_nsf_award)

        assert result["external_id"] == "2529183"
        assert result["source"] == "nsf"
        assert result["title"] == "Machine Learning for Climate Science Research"
        assert result["amount_min"] == 797762
        assert result["agency"] == "National Science Foundation"
        assert "nsf.gov/awardsearch" in result["url"]
        assert result["raw_data"] == sample_nsf_award

    def test_normalize_minimal_award(self):
        """Test normalizing award with minimal fields."""
        minimal = {
            "id": "1234567",
            "title": "Test Grant",
        }
        result = NSFNormalizer.normalize(minimal)

        assert result["external_id"] == "1234567"
        assert result["source"] == "nsf"
        assert result["title"] == "Test Grant"
        assert result["amount_min"] is None

    def test_normalize_date_parsing(self, sample_nsf_award):
        """Test date parsing in NSF normalization."""
        result = NSFNormalizer.normalize(sample_nsf_award)

        # NSF uses MM/DD/YYYY format
        assert result["deadline"] == "2028-05-31"  # expDate
        assert result["posted_at"] == "2025-01-06"  # date


class TestNIHReporterNormalizer:
    """Tests for NIH Reporter-specific normalization."""

    def test_normalize_complete_project(self, sample_nih_reporter_project):
        """Test normalizing a complete NIH Reporter project."""
        result = NIHReporterNormalizer.normalize(sample_nih_reporter_project)

        assert result["external_id"] == "1R01CA123456-01"
        assert result["source"] == "nih_reporter"
        assert "Cancer Treatment" in result["title"]
        assert result["amount_min"] == 750000
        assert "National Cancer Institute" in result["agency"]
        assert "reporter.nih.gov" in result["url"]

    def test_normalize_extracts_pi(self, sample_nih_reporter_project):
        """Test PI information is extracted."""
        result = NIHReporterNormalizer.normalize(sample_nih_reporter_project)
        # PI name should be in raw_data, extracted by agent
        assert result["raw_data"]["principal_investigators"][0]["first_name"] == "John"

    def test_normalize_eligibility_from_org(self, sample_nih_reporter_project):
        """Test eligibility includes organization info."""
        result = NIHReporterNormalizer.normalize(sample_nih_reporter_project)

        assert result["eligibility"] is not None
        assert result["eligibility"]["institution"] == "Harvard Medical School"
        assert result["eligibility"]["institution_state"] == "MA"


class TestGrantsGovNormalizer:
    """Tests for Grants.gov-specific normalization."""

    def test_normalize_complete_opportunity(self, sample_grants_gov_opportunity):
        """Test normalizing a complete Grants.gov opportunity."""
        result = GrantsGovNormalizer.normalize(sample_grants_gov_opportunity)

        assert result["external_id"] == "HHS-2025-ACF-OCS-EE-0001"
        assert result["source"] == "grants_gov"
        assert "Economic Development" in result["title"]
        assert result["amount_min"] == 50000
        assert result["amount_max"] == 800000
        assert "grants.gov" in result["url"]

    def test_normalize_extracts_eligibility(self, sample_grants_gov_opportunity):
        """Test eligibility applicants are extracted."""
        result = GrantsGovNormalizer.normalize(sample_grants_gov_opportunity)

        assert result["eligibility"] is not None
        assert "applicant_types" in result["eligibility"]
        assert len(result["eligibility"]["applicant_types"]) > 0

    def test_normalize_date_parsing(self, sample_grants_gov_opportunity):
        """Test date parsing for Grants.gov."""
        result = GrantsGovNormalizer.normalize(sample_grants_gov_opportunity)

        assert result["deadline"] == "2025-03-15"  # closeDate
        assert result["posted_at"] == "2025-01-02"  # postedDate
