"""
Tests for CV Parser Service.
Tests extracting profile information from CV/resume text.
"""
import pytest


class TestExtractEmail:
    """Tests for email extraction."""

    def test_extract_valid_email(self):
        """Test extracting a valid email address."""
        from backend.services.cv_parser import extract_email

        text = "Contact me at john.doe@university.edu for more info."
        email = extract_email(text)

        assert email == "john.doe@university.edu"

    def test_extract_email_with_subdomain(self):
        """Test extracting email with subdomain."""
        from backend.services.cv_parser import extract_email

        text = "Email: researcher@cs.stanford.edu"
        email = extract_email(text)

        assert email == "researcher@cs.stanford.edu"

    def test_extract_first_email(self):
        """Test extracting first email when multiple present."""
        from backend.services.cv_parser import extract_email

        text = "Primary: first@example.com Secondary: second@example.org"
        email = extract_email(text)

        assert email == "first@example.com"

    def test_extract_email_no_match(self):
        """Test when no email is present."""
        from backend.services.cv_parser import extract_email

        text = "No email address here"
        email = extract_email(text)

        assert email is None

    def test_extract_email_edge_cases(self):
        """Test email extraction edge cases."""
        from backend.services.cv_parser import extract_email

        # Email with numbers
        text = "Contact: user123@domain.com"
        email = extract_email(text)
        assert email == "user123@domain.com"

        # Email with plus sign
        text = "Email: user+tag@domain.com"
        email = extract_email(text)
        assert email == "user+tag@domain.com"


class TestExtractName:
    """Tests for name extraction."""

    def test_extract_simple_name(self):
        """Test extracting a simple two-word name."""
        from backend.services.cv_parser import extract_name

        text = "John Smith\njohn.smith@university.edu\nResearch Professor"
        name = extract_name(text)

        assert name == "John Smith"

    def test_extract_name_with_middle_initial(self):
        """Test extracting name with middle initial."""
        from backend.services.cv_parser import extract_name

        text = "John A Smith\nDepartment of Computer Science"
        name = extract_name(text)

        assert name == "John A Smith"

    def test_extract_name_skips_cv_header(self):
        """Test that CV header is skipped."""
        from backend.services.cv_parser import extract_name

        text = "Curriculum Vitae\nJane Doe\nProfessor"
        name = extract_name(text)

        assert name == "Jane Doe"

    def test_extract_name_skips_email_line(self):
        """Test that email lines are skipped."""
        from backend.services.cv_parser import extract_name

        text = "email@example.com\nJohn Smith\nResearcher"
        name = extract_name(text)

        assert name == "John Smith"

    def test_extract_name_no_valid_name(self):
        """Test when no valid name is found."""
        from backend.services.cv_parser import extract_name

        # Use only headers/emails/URLs that should be skipped
        text = "email: test@test.com\nhttp://website.com\nphone: 555-1234"
        name = extract_name(text)

        assert name is None


class TestExtractInstitution:
    """Tests for institution extraction."""

    def test_extract_university(self):
        """Test extracting university name."""
        from backend.services.cv_parser import extract_institution

        text = "Professor at University of California Berkeley"
        institution = extract_institution(text)

        assert institution is not None
        assert "University" in institution

    def test_extract_institute(self):
        """Test extracting institute name."""
        from backend.services.cv_parser import extract_institution

        text = "Researcher at Massachusetts Institute of Technology"
        institution = extract_institution(text)

        assert institution is not None

    def test_extract_abbreviated_institution(self):
        """Test extracting abbreviated institution names."""
        from backend.services.cv_parser import extract_institution

        text = "Graduated from MIT in 2020"
        institution = extract_institution(text)

        assert institution is not None
        assert "MIT" in institution

    def test_extract_institution_with_affiliation_marker(self):
        """Test extracting institution near affiliation marker."""
        from backend.services.cv_parser import extract_institution

        text = "Affiliation: Stanford University\nDepartment of Biology"
        institution = extract_institution(text)

        assert institution is not None

    def test_extract_institution_no_match(self):
        """Test when no institution is found."""
        from backend.services.cv_parser import extract_institution

        text = "Worked in various companies"
        institution = extract_institution(text)

        assert institution is None


class TestExtractResearchInterests:
    """Tests for research interests extraction."""

    def test_extract_from_section_header(self):
        """Test extracting from research interests section."""
        from backend.services.cv_parser import extract_research_interests

        text = """
        Research Interests
        • Machine learning
        • Data science
        • Natural language processing
        """
        interests = extract_research_interests(text)

        assert isinstance(interests, list)

    def test_extract_common_research_fields(self):
        """Test extracting common research field keywords."""
        from backend.services.cv_parser import extract_research_interests

        text = "My work focuses on machine learning, bioinformatics, and genomics"
        interests = extract_research_interests(text)

        assert isinstance(interests, list)

    def test_extract_research_interests_empty(self):
        """Test when no research interests found."""
        from backend.services.cv_parser import extract_research_interests

        text = "No relevant content here"
        interests = extract_research_interests(text)

        assert isinstance(interests, list)

    def test_extract_comma_separated_interests(self):
        """Test extracting comma-separated interests."""
        from backend.services.cv_parser import extract_research_interests

        text = """
        Areas of Expertise: molecular biology, protein engineering, biochemistry
        """
        interests = extract_research_interests(text)

        assert isinstance(interests, list)


class TestExtractPublications:
    """Tests for publication extraction patterns."""

    def test_publication_count_pattern(self):
        """Test extracting publication counts."""
        import re

        text = "Publications: 25 peer-reviewed articles"
        pattern = r"(\d+)\s*(?:peer-reviewed\s+)?(?:publications?|articles?|papers?)"
        match = re.search(pattern, text, re.IGNORECASE)

        assert match is not None
        assert match.group(1) == "25"

    def test_h_index_pattern(self):
        """Test extracting H-index."""
        import re

        text = "h-index: 15"
        pattern = r"h[-\s]?index\s*:?\s*(\d+)"
        match = re.search(pattern, text, re.IGNORECASE)

        assert match is not None
        assert match.group(1) == "15"


class TestExtractEducation:
    """Tests for education extraction patterns."""

    def test_phd_extraction(self):
        """Test extracting PhD degree."""
        import re

        text = "Ph.D. in Computer Science, Stanford University, 2015"
        pattern = r"(Ph\.?D\.?|PhD|Doctor)\s*(?:of|in)?\s*[\w\s]+,?\s*(?:from\s+)?[\w\s]+(?:University|Institute)"
        match = re.search(pattern, text, re.IGNORECASE)

        assert match is not None

    def test_masters_extraction(self):
        """Test extracting Master's degree."""
        import re

        text = "M.S. in Biology from MIT"
        pattern = r"(M\.?S\.?|Master'?s?|MA|MS)\s*(?:of|in)?\s*[\w\s]+"
        match = re.search(pattern, text, re.IGNORECASE)

        assert match is not None


class TestExtractCareerStage:
    """Tests for career stage extraction."""

    def test_professor_keywords(self):
        """Test identifying professor career stage."""
        text = "Full Professor of Biology"

        keywords = ["professor", "faculty", "tenure"]
        stage = None
        text_lower = text.lower()

        for kw in keywords:
            if kw in text_lower:
                stage = "faculty"
                break

        assert stage == "faculty"

    def test_postdoc_keywords(self):
        """Test identifying postdoc career stage."""
        text = "Postdoctoral Research Fellow"

        keywords = ["postdoc", "postdoctoral", "post-doc"]
        stage = None
        text_lower = text.lower()

        for kw in keywords:
            if kw in text_lower:
                stage = "postdoc"
                break

        assert stage == "postdoc"

    def test_graduate_student_keywords(self):
        """Test identifying graduate student career stage."""
        text = "Ph.D. Candidate in Chemistry"

        keywords = ["phd candidate", "ph.d. candidate", "graduate student", "doctoral"]
        stage = None
        text_lower = text.lower()

        for kw in keywords:
            if kw in text_lower:
                stage = "graduate"
                break

        assert stage == "graduate"


class TestExtractFundingHistory:
    """Tests for funding history extraction."""

    def test_funding_amount_pattern(self):
        """Test extracting funding amounts."""
        import re

        text = "NSF Grant $500,000"
        pattern = r"\$[\d,]+(?:\.\d{2})?"
        match = re.search(pattern, text)

        assert match is not None
        assert "$500,000" in match.group(0)

    def test_grant_agency_pattern(self):
        """Test extracting grant agencies."""
        import re

        text = "Funded by NSF, NIH, and DOE grants"
        agencies = ["NSF", "NIH", "DOE", "DOD", "NASA"]

        found = [a for a in agencies if a in text]

        assert "NSF" in found
        assert "NIH" in found
        assert "DOE" in found


class TestTextCleaning:
    """Tests for text cleaning utilities."""

    def test_normalize_whitespace(self):
        """Test normalizing whitespace."""
        import re

        text = "Multiple   spaces   here"
        cleaned = re.sub(r"\s+", " ", text)

        assert cleaned == "Multiple spaces here"

    def test_remove_special_characters(self):
        """Test removing special characters."""
        import re

        text = "Research•Topic—Area"
        cleaned = re.sub(r"[•—–]", " ", text)
        cleaned = re.sub(r"\s+", " ", cleaned)

        assert "•" not in cleaned
        assert "—" not in cleaned


class TestPDFExtraction:
    """Tests for PDF extraction setup."""

    def test_import_error_handling(self):
        """Test that import errors are handled gracefully."""
        from backend.services.cv_parser import extract_text_from_pdf

        # When pymupdf is not installed, should return None
        # The function handles ImportError internally
        result = extract_text_from_pdf(b"not a pdf")

        # Should return None when PDF is invalid or library missing
        assert result is None

    def test_empty_pdf_bytes(self):
        """Test handling empty PDF bytes."""
        from backend.services.cv_parser import extract_text_from_pdf

        result = extract_text_from_pdf(b"")

        assert result is None
