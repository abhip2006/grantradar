"""
Tests for Similarity Service.
Tests algorithmic similarity calculations for grants.
"""


class TestExtractKeywords:
    """Tests for keyword extraction."""

    def test_extract_keywords_simple(self):
        """Test extracting keywords from simple text."""
        from backend.services.similarity import extract_keywords

        text = "Machine learning research in biology applications"
        keywords = extract_keywords(text)

        assert "machine" in keywords
        assert "learning" in keywords
        assert "biology" in keywords
        assert "applications" in keywords

    def test_extract_keywords_removes_stop_words(self):
        """Test that stop words are removed."""
        from backend.services.similarity import extract_keywords, STOP_WORDS

        text = "The research and applications of machine learning"
        keywords = extract_keywords(text)

        # Stop words should not be in keywords
        for keyword in keywords:
            assert keyword not in STOP_WORDS

    def test_extract_keywords_removes_short_words(self):
        """Test that short words are removed."""
        from backend.services.similarity import extract_keywords, MIN_WORD_LENGTH

        text = "AI ML is an area of CS"
        keywords = extract_keywords(text)

        # Short words should not be in keywords
        for keyword in keywords:
            assert len(keyword) >= MIN_WORD_LENGTH

    def test_extract_keywords_empty_text(self):
        """Test extracting keywords from empty text."""
        from backend.services.similarity import extract_keywords

        keywords = extract_keywords("")
        assert keywords == set()

    def test_extract_keywords_none_text(self):
        """Test extracting keywords from None."""
        from backend.services.similarity import extract_keywords

        keywords = extract_keywords(None)
        assert keywords == set()

    def test_extract_keywords_case_insensitive(self):
        """Test keyword extraction is case insensitive."""
        from backend.services.similarity import extract_keywords

        text1 = "Machine Learning"
        text2 = "machine learning"

        keywords1 = extract_keywords(text1)
        keywords2 = extract_keywords(text2)

        assert keywords1 == keywords2


class TestJaccardSimilarity:
    """Tests for Jaccard similarity calculation."""

    def test_identical_sets(self):
        """Test similarity of identical sets."""
        from backend.services.similarity import calculate_jaccard_similarity

        set1 = {"machine", "learning", "biology"}
        set2 = {"machine", "learning", "biology"}

        similarity = calculate_jaccard_similarity(set1, set2)

        assert similarity == 1.0

    def test_disjoint_sets(self):
        """Test similarity of completely different sets."""
        from backend.services.similarity import calculate_jaccard_similarity

        set1 = {"machine", "learning", "biology"}
        set2 = {"chemistry", "physics", "math"}

        similarity = calculate_jaccard_similarity(set1, set2)

        assert similarity == 0.0

    def test_partial_overlap(self):
        """Test similarity with partial overlap."""
        from backend.services.similarity import calculate_jaccard_similarity

        set1 = {"machine", "learning", "biology"}
        set2 = {"machine", "learning", "physics"}

        similarity = calculate_jaccard_similarity(set1, set2)

        # Intersection: {machine, learning} = 2
        # Union: {machine, learning, biology, physics} = 4
        # Jaccard = 2/4 = 0.5
        assert similarity == 0.5

    def test_empty_sets(self):
        """Test similarity with empty sets."""
        from backend.services.similarity import calculate_jaccard_similarity

        assert calculate_jaccard_similarity(set(), set()) == 0.0
        assert calculate_jaccard_similarity({"a"}, set()) == 0.0
        assert calculate_jaccard_similarity(set(), {"b"}) == 0.0


class TestFundingSimilarity:
    """Tests for funding range similarity."""

    def test_identical_ranges(self):
        """Test identical funding ranges."""
        from backend.services.similarity import calculate_funding_similarity

        similarity = calculate_funding_similarity(100000, 500000, 100000, 500000)

        assert similarity == 1.0

    def test_completely_disjoint_ranges(self):
        """Test completely disjoint funding ranges."""
        from backend.services.similarity import calculate_funding_similarity

        # $100K-$200K vs $500K-$600K
        similarity = calculate_funding_similarity(100000, 200000, 500000, 600000)

        # Should be a low value (0.5 or below due to distance-based decay)
        assert similarity <= 0.5

    def test_overlapping_ranges(self):
        """Test overlapping funding ranges."""
        from backend.services.similarity import calculate_funding_similarity

        # $100K-$300K vs $200K-$400K
        similarity = calculate_funding_similarity(100000, 300000, 200000, 400000)

        # Some overlap should give a medium similarity
        assert 0 < similarity < 1

    def test_one_contains_other(self):
        """Test when one range contains the other."""
        from backend.services.similarity import calculate_funding_similarity

        # $100K-$500K vs $200K-$300K
        similarity = calculate_funding_similarity(100000, 500000, 200000, 300000)

        assert similarity > 0

    def test_no_funding_info(self):
        """Test with no funding information."""
        from backend.services.similarity import calculate_funding_similarity

        # No funding info returns neutral score (0.5)
        similarity = calculate_funding_similarity(None, None, None, None)

        assert similarity == 0.5

    def test_partial_funding_info(self):
        """Test with partial funding information."""
        from backend.services.similarity import calculate_funding_similarity

        # One has funding, one doesn't
        similarity = calculate_funding_similarity(100000, 500000, None, None)

        assert similarity == 0.5

    def test_min_only(self):
        """Test with only min amount."""
        from backend.services.similarity import calculate_funding_similarity

        similarity = calculate_funding_similarity(100000, None, 100000, None)

        assert similarity > 0

    def test_max_only(self):
        """Test with only max amount."""
        from backend.services.similarity import calculate_funding_similarity

        similarity = calculate_funding_similarity(None, 500000, None, 500000)

        assert similarity > 0


class TestAgencySimilarity:
    """Tests for agency similarity."""

    def test_exact_match(self):
        """Test exact agency match."""
        from backend.services.similarity import calculate_agency_similarity

        similarity = calculate_agency_similarity("NSF", "NSF")

        assert similarity == 1.0

    def test_case_insensitive_match(self):
        """Test case insensitive agency match."""
        from backend.services.similarity import calculate_agency_similarity

        similarity = calculate_agency_similarity("nsf", "NSF")

        assert similarity == 1.0

    def test_different_agencies(self):
        """Test different agencies."""
        from backend.services.similarity import calculate_agency_similarity

        similarity = calculate_agency_similarity("NSF", "DOD")

        assert similarity < 1.0

    def test_no_agency(self):
        """Test with no agency."""
        from backend.services.similarity import calculate_agency_similarity

        assert calculate_agency_similarity(None, "NSF") == 0.0
        assert calculate_agency_similarity("NSF", None) == 0.0
        assert calculate_agency_similarity(None, None) == 0.0

    def test_whitespace_handling(self):
        """Test whitespace handling in agency names."""
        from backend.services.similarity import calculate_agency_similarity

        similarity = calculate_agency_similarity("  NSF  ", "NSF")

        assert similarity == 1.0


class TestStopWords:
    """Tests for stop words constant."""

    def test_stop_words_exist(self):
        """Test that stop words set exists."""
        from backend.services.similarity import STOP_WORDS

        assert len(STOP_WORDS) > 0
        assert isinstance(STOP_WORDS, set)

    def test_common_stop_words(self):
        """Test common stop words are included."""
        from backend.services.similarity import STOP_WORDS

        assert "the" in STOP_WORDS
        assert "and" in STOP_WORDS
        assert "of" in STOP_WORDS
        assert "grant" in STOP_WORDS
        assert "research" in STOP_WORDS


class TestSimilarityResult:
    """Tests for SimilarityResult dataclass."""

    def test_similarity_result_creation(self):
        """Test creating a SimilarityResult."""
        from backend.services.similarity import SimilarityResult
        from backend.models import Grant
        from unittest.mock import MagicMock

        mock_grant = MagicMock(spec=Grant)
        result = SimilarityResult(
            grant=mock_grant,
            similarity_score=0.85,
            similarity_reasons=["Agency match", "Keyword overlap"],
        )

        assert result.grant == mock_grant
        assert result.similarity_score == 0.85
        assert len(result.similarity_reasons) == 2

    def test_similarity_result_fields(self):
        """Test SimilarityResult has expected fields."""
        from backend.services.similarity import SimilarityResult
        import dataclasses

        fields = {f.name for f in dataclasses.fields(SimilarityResult)}

        assert "grant" in fields
        assert "similarity_score" in fields
        assert "similarity_reasons" in fields


class TestMinWordLength:
    """Tests for MIN_WORD_LENGTH constant."""

    def test_min_word_length_value(self):
        """Test minimum word length value."""
        from backend.services.similarity import MIN_WORD_LENGTH

        assert MIN_WORD_LENGTH == 3

    def test_min_word_length_filtering(self):
        """Test that words shorter than MIN_WORD_LENGTH are filtered."""
        from backend.services.similarity import extract_keywords

        # "AI" and "ML" should be filtered out
        text = "AI ML machine learning"
        keywords = extract_keywords(text)

        # Only longer words should remain
        assert "machine" in keywords
        assert "learning" in keywords
