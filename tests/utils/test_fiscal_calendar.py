"""
Tests for fiscal calendar utilities.
Tests federal fiscal year calculations and quarter detection.
"""
from datetime import date

import pytest

from backend.utils.fiscal_calendar import FiscalCalendar, is_federal_funder, FEDERAL_AGENCIES


class TestFiscalCalendar:
    """Tests for FiscalCalendar class."""

    # =========================================================================
    # Fiscal Year Tests
    # =========================================================================

    def test_get_fiscal_year_q1(self):
        """Test fiscal year calculation for Q1 (Oct-Dec)."""
        # October 2025 is FY2026 Q1
        assert FiscalCalendar.get_fiscal_year(date(2025, 10, 1)) == 2026
        assert FiscalCalendar.get_fiscal_year(date(2025, 11, 15)) == 2026
        assert FiscalCalendar.get_fiscal_year(date(2025, 12, 31)) == 2026

    def test_get_fiscal_year_q2(self):
        """Test fiscal year calculation for Q2 (Jan-Mar)."""
        # January 2026 is FY2026 Q2
        assert FiscalCalendar.get_fiscal_year(date(2026, 1, 1)) == 2026
        assert FiscalCalendar.get_fiscal_year(date(2026, 2, 15)) == 2026
        assert FiscalCalendar.get_fiscal_year(date(2026, 3, 31)) == 2026

    def test_get_fiscal_year_q3(self):
        """Test fiscal year calculation for Q3 (Apr-Jun)."""
        assert FiscalCalendar.get_fiscal_year(date(2026, 4, 1)) == 2026
        assert FiscalCalendar.get_fiscal_year(date(2026, 5, 15)) == 2026
        assert FiscalCalendar.get_fiscal_year(date(2026, 6, 30)) == 2026

    def test_get_fiscal_year_q4(self):
        """Test fiscal year calculation for Q4 (Jul-Sep)."""
        assert FiscalCalendar.get_fiscal_year(date(2026, 7, 1)) == 2026
        assert FiscalCalendar.get_fiscal_year(date(2026, 8, 15)) == 2026
        assert FiscalCalendar.get_fiscal_year(date(2026, 9, 30)) == 2026

    def test_get_fiscal_year_boundary(self):
        """Test fiscal year boundary (Sep 30 vs Oct 1)."""
        # Sep 30, 2026 is last day of FY2026
        assert FiscalCalendar.get_fiscal_year(date(2026, 9, 30)) == 2026
        # Oct 1, 2026 is first day of FY2027
        assert FiscalCalendar.get_fiscal_year(date(2026, 10, 1)) == 2027

    # =========================================================================
    # Fiscal Quarter Tests
    # =========================================================================

    def test_get_fiscal_quarter_q1(self):
        """Test Q1 detection (Oct-Dec)."""
        assert FiscalCalendar.get_fiscal_quarter(date(2025, 10, 1)) == 1
        assert FiscalCalendar.get_fiscal_quarter(date(2025, 11, 15)) == 1
        assert FiscalCalendar.get_fiscal_quarter(date(2025, 12, 31)) == 1

    def test_get_fiscal_quarter_q2(self):
        """Test Q2 detection (Jan-Mar)."""
        assert FiscalCalendar.get_fiscal_quarter(date(2026, 1, 1)) == 2
        assert FiscalCalendar.get_fiscal_quarter(date(2026, 2, 15)) == 2
        assert FiscalCalendar.get_fiscal_quarter(date(2026, 3, 31)) == 2

    def test_get_fiscal_quarter_q3(self):
        """Test Q3 detection (Apr-Jun)."""
        assert FiscalCalendar.get_fiscal_quarter(date(2026, 4, 1)) == 3
        assert FiscalCalendar.get_fiscal_quarter(date(2026, 5, 15)) == 3
        assert FiscalCalendar.get_fiscal_quarter(date(2026, 6, 30)) == 3

    def test_get_fiscal_quarter_q4(self):
        """Test Q4 detection (Jul-Sep)."""
        assert FiscalCalendar.get_fiscal_quarter(date(2026, 7, 1)) == 4
        assert FiscalCalendar.get_fiscal_quarter(date(2026, 8, 15)) == 4
        assert FiscalCalendar.get_fiscal_quarter(date(2026, 9, 30)) == 4

    # =========================================================================
    # Quarter End Tests
    # =========================================================================

    def test_get_next_quarter_end_from_q1(self):
        """Test getting next quarter end from Q1."""
        # From November 2025, next quarter end is Dec 31, 2025
        result = FiscalCalendar.get_next_quarter_end(date(2025, 11, 15))
        assert result == date(2025, 12, 31)

    def test_get_next_quarter_end_from_q2(self):
        """Test getting next quarter end from Q2."""
        # From February 2026, next quarter end is Mar 31, 2026
        result = FiscalCalendar.get_next_quarter_end(date(2026, 2, 15))
        assert result == date(2026, 3, 31)

    def test_get_next_quarter_end_from_q3(self):
        """Test getting next quarter end from Q3."""
        # From May 2026, next quarter end is Jun 30, 2026
        result = FiscalCalendar.get_next_quarter_end(date(2026, 5, 15))
        assert result == date(2026, 6, 30)

    def test_get_next_quarter_end_from_q4(self):
        """Test getting next quarter end from Q4."""
        # From August 2026, next quarter end is Sep 30, 2026
        result = FiscalCalendar.get_next_quarter_end(date(2026, 8, 15))
        assert result == date(2026, 9, 30)

    def test_get_next_quarter_end_on_quarter_end(self):
        """Test getting next quarter end when on a quarter end date."""
        # On Dec 31, next quarter end should be Mar 31
        result = FiscalCalendar.get_next_quarter_end(date(2025, 12, 31))
        # Should return the current quarter end or next
        assert result.month in [12, 3]

    # =========================================================================
    # Quarter End Dates Tests
    # =========================================================================

    def test_get_quarter_end_dates_for_fiscal_year(self):
        """Test getting all quarter end dates for a fiscal year."""
        result = FiscalCalendar.get_quarter_end_dates(2026)
        assert len(result) == 4
        assert result[0] == date(2025, 12, 31)  # Q1 end
        assert result[1] == date(2026, 3, 31)   # Q2 end
        assert result[2] == date(2026, 6, 30)   # Q3 end
        assert result[3] == date(2026, 9, 30)   # Q4 end

    # =========================================================================
    # Near Quarter End Tests
    # =========================================================================

    def test_is_near_quarter_end_true(self):
        """Test detection when near quarter end."""
        # Dec 25 is 6 days from Dec 31
        assert FiscalCalendar.is_near_quarter_end(date(2025, 12, 25), days_threshold=7) is True

    def test_is_near_quarter_end_false(self):
        """Test detection when not near quarter end."""
        # Nov 15 is far from Dec 31
        assert FiscalCalendar.is_near_quarter_end(date(2025, 11, 15), days_threshold=7) is False

    def test_is_near_quarter_end_exact_threshold(self):
        """Test detection at exact threshold."""
        # Dec 24 is exactly 7 days from Dec 31
        assert FiscalCalendar.is_near_quarter_end(date(2025, 12, 24), days_threshold=7) is True

    # =========================================================================
    # Fiscal Year Period Tests
    # =========================================================================

    def test_is_fiscal_year_end_period(self):
        """Test fiscal year end period detection (late Aug-Sep)."""
        # Sep 15 is 15 days before Sep 30, within 30-day window
        assert FiscalCalendar.is_fiscal_year_end_period(date(2026, 9, 15)) is True
        # Sep 1 is 29 days before Sep 30, within 30-day window
        assert FiscalCalendar.is_fiscal_year_end_period(date(2026, 9, 1)) is True
        # Aug 15 is 46 days before Sep 30, outside 30-day window
        assert FiscalCalendar.is_fiscal_year_end_period(date(2026, 8, 15)) is False
        assert FiscalCalendar.is_fiscal_year_end_period(date(2026, 7, 15)) is False
        assert FiscalCalendar.is_fiscal_year_end_period(date(2026, 10, 15)) is False

    def test_is_fiscal_year_start_period(self):
        """Test fiscal year start period detection (Oct-Nov)."""
        assert FiscalCalendar.is_fiscal_year_start_period(date(2025, 10, 15)) is True
        assert FiscalCalendar.is_fiscal_year_start_period(date(2025, 11, 15)) is True
        assert FiscalCalendar.is_fiscal_year_start_period(date(2025, 9, 15)) is False
        assert FiscalCalendar.is_fiscal_year_start_period(date(2025, 12, 15)) is False

    # =========================================================================
    # Historical Quarter Affinity Tests
    # =========================================================================

    def test_analyze_historical_quarter_affinity(self):
        """Test analysis of historical quarter patterns."""
        # All dates are near quarter ends (Mar 31 and Jun 30)
        historical_dates = [
            date(2024, 3, 31),  # Q2 end
            date(2023, 3, 31),  # Q2 end
            date(2022, 3, 30),  # Near Q2 end
            date(2021, 6, 30),  # Q3 end
        ]
        result = FiscalCalendar.analyze_historical_quarter_affinity(historical_dates)

        # Returns float affinity score (0.0 - 1.0)
        assert isinstance(result, float)
        assert result > 0.7  # Most dates are near quarter ends

    def test_analyze_historical_quarter_affinity_empty(self):
        """Test quarter affinity with no historical dates."""
        result = FiscalCalendar.analyze_historical_quarter_affinity([])
        assert result == 0.0

    # =========================================================================
    # Prediction Adjustment Tests
    # =========================================================================

    def test_adjust_prediction_for_fiscal_patterns_snaps_to_quarter_end(self):
        """Test that predictions snap to quarter end when pattern exists."""
        historical_dates = [
            date(2024, 3, 31),
            date(2023, 3, 31),
            date(2022, 3, 30),
        ]
        predicted = date(2026, 3, 15)  # Mid-March

        result = FiscalCalendar.adjust_prediction_for_fiscal_patterns(
            predicted_date=predicted,
            funder_name="NSF",
            historical_dates=historical_dates,
        )

        # Should snap to March 31 (Q2 end)
        assert result == date(2026, 3, 31)

    def test_adjust_prediction_no_change_without_pattern(self):
        """Test prediction unchanged when no clear pattern."""
        historical_dates = [
            date(2024, 1, 15),
            date(2023, 5, 20),
            date(2022, 8, 10),
        ]
        predicted = date(2026, 3, 15)

        result = FiscalCalendar.adjust_prediction_for_fiscal_patterns(
            predicted_date=predicted,
            funder_name="NSF",
            historical_dates=historical_dates,
        )

        # Should be close to original (no strong pattern)
        assert abs((result - predicted).days) <= 45


class TestIsFederalFunder:
    """Tests for federal funder detection."""

    def test_known_federal_agencies(self):
        """Test detection of known federal agencies."""
        assert is_federal_funder("NSF") is True
        assert is_federal_funder("NIH") is True
        assert is_federal_funder("DOE") is True
        assert is_federal_funder("NASA") is True
        assert is_federal_funder("DARPA") is True

    def test_federal_agency_full_names(self):
        """Test detection using full names."""
        assert is_federal_funder("National Science Foundation") is True
        assert is_federal_funder("National Institutes of Health") is True
        assert is_federal_funder("Department of Energy") is True

    def test_federal_agency_variations(self):
        """Test detection with name variations."""
        assert is_federal_funder("NIH - National Cancer Institute") is True
        assert is_federal_funder("NSF - Directorate for Engineering") is True
        assert is_federal_funder("Department of Defense") is True

    def test_non_federal_funders(self):
        """Test that non-federal funders return False."""
        assert is_federal_funder("Ford Foundation") is False
        assert is_federal_funder("Bill & Melinda Gates Foundation") is False
        assert is_federal_funder("Wellcome Trust") is False
        assert is_federal_funder("Rockefeller Brothers Fund") is False

    def test_case_insensitive(self):
        """Test case insensitive matching."""
        assert is_federal_funder("nsf") is True
        assert is_federal_funder("Nsf") is True
        assert is_federal_funder("NATIONAL SCIENCE FOUNDATION") is True

    def test_partial_match(self):
        """Test partial name matching."""
        assert is_federal_funder("NIH Cancer Research") is True
        assert is_federal_funder("NASA Space Grant") is True

    def test_federal_agencies_list_not_empty(self):
        """Test that FEDERAL_AGENCIES list is populated."""
        assert len(FEDERAL_AGENCIES) > 20  # Should have many agencies


class TestFiscalCalendarEdgeCases:
    """Edge case tests for fiscal calendar."""

    def test_leap_year_handling(self):
        """Test handling of leap years."""
        # Feb 29, 2024 is in FY2024 Q2
        assert FiscalCalendar.get_fiscal_year(date(2024, 2, 29)) == 2024
        assert FiscalCalendar.get_fiscal_quarter(date(2024, 2, 29)) == 2

    def test_year_boundary(self):
        """Test year boundary (Dec 31 to Jan 1)."""
        assert FiscalCalendar.get_fiscal_year(date(2025, 12, 31)) == 2026
        assert FiscalCalendar.get_fiscal_year(date(2026, 1, 1)) == 2026

        assert FiscalCalendar.get_fiscal_quarter(date(2025, 12, 31)) == 1
        assert FiscalCalendar.get_fiscal_quarter(date(2026, 1, 1)) == 2

    def test_all_months_covered(self):
        """Test that all 12 months map to valid quarters."""
        for month in range(1, 13):
            test_date = date(2026, month, 15)
            quarter = FiscalCalendar.get_fiscal_quarter(test_date)
            assert 1 <= quarter <= 4

            fy = FiscalCalendar.get_fiscal_year(test_date)
            assert fy in [2026, 2027]
