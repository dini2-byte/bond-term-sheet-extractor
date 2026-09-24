"""
tests/test_validate.py: Unit tests for financial sanity rules, source grounding enforcement, and date chronology.
"""

from datetime import datetime
import pandas as pd
import pytest

from validate import (
    parse_flexible_date,
    validate_tranche,
    validate_comps_table,
)


class TestDateParsing:
    def test_parse_flexible_date(self):
        dt = parse_flexible_date("May 5, 2025")
        assert dt == datetime(2025, 5, 5)

        dt_suffix = parse_flexible_date("May 12, 2025 (T+5)")
        assert dt == datetime(2025, 5, 5)
        assert dt_suffix == datetime(2025, 5, 12)

        assert parse_flexible_date("Not found") is None
        assert parse_flexible_date("None") is None
        assert parse_flexible_date(None) is None


class TestTrancheValidation:
    @pytest.fixture
    def valid_tranche_row(self):
        return {
            "Tranche": "4.000% Notes due 2028",
            "Coupon (%)": 4.0,
            "Issue Price": 99.804,
            "Spread (bps)": 25,
            "Trade Date": "May 5, 2025",
            "Settlement Date": "May 12, 2025 (T+5)",
            "Maturity Date": "May 12, 2028",
        }

    @pytest.fixture
    def valid_audit_fields(self):
        return {
            "coupon": {"grounded": True, "raw": "4.000%"},
            "issue_price": {"grounded": True, "raw": "99.804%"},
            "spread_bps": {"grounded": True, "raw": "25 basis points"},
            "maturity_date": {"grounded": True, "raw": "May 12, 2028"},
        }

    def test_valid_tranche_passes(self, valid_tranche_row, valid_audit_fields):
        flags = validate_tranche(valid_tranche_row, valid_audit_fields)
        assert flags == []

    def test_ungrounded_field_flags(self, valid_tranche_row, valid_audit_fields):
        valid_audit_fields["coupon"]["grounded"] = False
        flags = validate_tranche(valid_tranche_row, valid_audit_fields)
        assert any("UNGROUNDED: coupon" in f for f in flags)

    def test_weak_grounding_flag(self, valid_tranche_row, valid_audit_fields):
        valid_audit_fields["coupon"]["grounded"] = False
        valid_audit_fields["coupon"]["grounding_quality"] = "span_mismatch"
        valid_audit_fields["coupon"]["span_text"] = "4."
        flags = validate_tranche(valid_tranche_row, valid_audit_fields)
        assert any(f.startswith("WEAK_GROUNDING: coupon") for f in flags)

    def test_no_interval_ungrounded_flag(self, valid_tranche_row, valid_audit_fields):
        valid_audit_fields["coupon"]["grounded"] = False
        valid_audit_fields["coupon"]["grounding_quality"] = "none"
        flags = validate_tranche(valid_tranche_row, valid_audit_fields)
        assert any("UNGROUNDED: coupon" in f for f in flags)

    def test_fully_exact_tranche_passes(self, valid_tranche_row, valid_audit_fields):
        for f in valid_audit_fields.values():
            f["grounded"] = True
            f["grounding_quality"] = "exact"
        flags = validate_tranche(valid_tranche_row, valid_audit_fields)
        assert not any("GROUNDING" in f or "UNGROUNDED" in f for f in flags)


    def test_coupon_bounds_check(self, valid_tranche_row, valid_audit_fields):
        valid_tranche_row["Coupon (%)"] = 25.0
        flags = validate_tranche(valid_tranche_row, valid_audit_fields)
        assert any("SUSPICIOUS_COUPON" in f for f in flags)

        valid_tranche_row["Coupon (%)"] = None
        flags = validate_tranche(valid_tranche_row, valid_audit_fields)
        assert any("MISSING_COUPON" in f for f in flags)

    def test_issue_price_bounds_check(self, valid_tranche_row, valid_audit_fields):
        valid_tranche_row["Issue Price"] = 80.0  # deep discount outside 90-110
        flags = validate_tranche(valid_tranche_row, valid_audit_fields)
        assert any("PRICE_DEVIATION" in f for f in flags)

    def test_spread_bounds_check(self, valid_tranche_row, valid_audit_fields):
        valid_tranche_row["Spread (bps)"] = 1200  # excessive spread > 1000 bps
        flags = validate_tranche(valid_tranche_row, valid_audit_fields)
        assert any("SPREAD_ANOMALY" in f for f in flags)

    def test_chronology_checks(self, valid_tranche_row, valid_audit_fields):
        # Maturity before trade date
        valid_tranche_row["Maturity Date"] = "May 1, 2025"
        flags = validate_tranche(valid_tranche_row, valid_audit_fields)
        assert any("DATE_SEQUENCE_ERROR: Maturity" in f for f in flags)

        # Settlement before trade date
        valid_tranche_row["Maturity Date"] = "May 12, 2028"
        valid_tranche_row["Settlement Date"] = "May 1, 2025"
        flags = validate_tranche(valid_tranche_row, valid_audit_fields)
        assert any("DATE_SEQUENCE_ERROR: Settlement" in f for f in flags)


class TestCompsTableValidation:
    def test_validate_comps_table(self):
        df = pd.DataFrame([
            {
                "Tranche": "Valid Notes 2028",
                "Coupon (%)": 4.0,
                "Issue Price": 99.8,
                "Spread (bps)": 25,
                "Trade Date": "May 5, 2025",
                "Settlement Date": "May 12, 2025",
                "Maturity Date": "May 12, 2028",
            },
            {
                "Tranche": "Bad Notes 2030",
                "Coupon (%)": 25.0,  # Invalid coupon
                "Issue Price": 99.8,
                "Spread (bps)": 25,
                "Trade Date": "May 5, 2025",
                "Settlement Date": "May 12, 2025",
                "Maturity Date": "May 12, 2030",
            },
        ])
        audit_records = [
            {"fields": {"coupon": {"grounded": True}}},
            {"fields": {"coupon": {"grounded": True}}},
        ]

        result_df = validate_comps_table(df, audit_records)
        assert result_df.iloc[0]["Validation Status"] == "PASSED"
        assert result_df.iloc[1]["Validation Status"] == "FLAGGED"
        assert "SUSPICIOUS_COUPON" in result_df.iloc[1]["Validation Issues"]
