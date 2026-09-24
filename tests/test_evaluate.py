"""
tests/test_evaluate.py: Unit tests for quantitative evaluation framework, normalization, and tolerance matching.
"""

import pandas as pd
import pytest

from evaluate import (
    normalize_text,
    matches_value,
    evaluate_deal,
)


class TestEvaluateHelpers:
    def test_normalize_text(self):
        assert normalize_text("Apple Inc.") == "apple inc"
        assert normalize_text("May 5, 2025") == "may 5 2025"
        assert normalize_text(None) == ""
        assert normalize_text(123) == "123"

    def test_matches_value_numeric(self):
        # Floats within 0.01 tolerance
        assert matches_value(4.00, 4.0, "Coupon (%)") is True
        assert matches_value(4.004, 4.0, "Coupon (%)") is True
        assert matches_value(4.05, 4.0, "Coupon (%)") is False

        # None handling
        assert matches_value(None, None, "Coupon (%)") is True
        assert matches_value(4.0, None, "Coupon (%)") is False
        assert matches_value(None, 4.0, "Coupon (%)") is False

    def test_matches_value_text(self):
        # Case and punctuation insensitive text
        assert matches_value("Apple Inc.", "APPLE INC.", "Issuer") is True
        assert matches_value("May 5, 2025", "May 5, 2025", "Trade Date") is True

        # Ratings grade matching
        ratings_agency_text = "Aaa (stable) by Moody's / AA+ (stable) by S&P"
        assert matches_value(ratings_agency_text, "Aaa / AA+", "Ratings") is True
        assert matches_value("Baa1 / BBB+", "Aaa / AA+", "Ratings") is False


class TestEvaluateDeal:
    def test_evaluate_deal_matching(self):
        extracted_df = pd.DataFrame([
            {
                "Issuer": "APPLE INC.",
                "Ratings": "Aaa / AA+",
                "Trade Date": "May 5, 2025",
                "Settlement Date": "May 12, 2025",
                "Principal ($M)": 1500.0,
                "Coupon (%)": 4.0,
                "Issue Price": 99.804,
                "Yield (%)": 4.07,
                "Spread (bps)": 25,
                "Benchmark Treasury": "3.750% due April 15, 2028",
                "Maturity Date": "May 12, 2028",
                "Day Count": "30/360",
                "Par Call Date": "April 12, 2028",
                "CUSIP": "037833EY2",
            }
        ])
        audit_records = [
            {
                "fields": {
                    "issuer": {"grounded": True},
                    "ratings": {"grounded": True},
                    "trade_date": {"grounded": True},
                    "settlement_date": {"grounded": True},
                    "principal_amount": {"grounded": True},
                    "coupon": {"grounded": True},
                    "issue_price": {"grounded": True},
                    "yield_to_maturity": {"grounded": True},
                    "spread_bps": {"grounded": True},
                    "benchmark_treasury": {"grounded": True},
                    "maturity_date": {"grounded": True},
                    "day_count": {"grounded": True},
                    "par_call_date": {"grounded": True},
                    "cusip": {"grounded": True},
                }
            }
        ]
        ground_truth = [
            {
                "Tranche": "4.000% Notes due 2028",
                "Issuer": "Apple Inc.",
                "Ratings": "Aaa / AA+",
                "Trade Date": "May 5, 2025",
                "Settlement Date": "May 12, 2025",
                "Principal ($M)": 1500.0,
                "Coupon (%)": 4.0,
                "Issue Price": 99.804,
                "Yield (%)": 4.07,
                "Spread (bps)": 25,
                "Benchmark Treasury": "3.750% due April 15, 2028",
                "Maturity Date": "May 12, 2028",
                "Day Count": "30/360",
                "Par Call Date": "April 12, 2028",
                "CUSIP": "037833EY2",
            }
        ]

        res = evaluate_deal("TEST_DEAL", extracted_df, audit_records, ground_truth)
        assert len(res) == 14
        assert res["Correct"].all()
        assert res["Grounded"].all()

    def test_run_evaluation_e2e(self):
        from evaluate import run_evaluation
        # Ensure full benchmark evaluation pipeline executes and creates report
        run_evaluation()

