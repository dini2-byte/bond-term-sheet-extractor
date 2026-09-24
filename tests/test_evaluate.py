"""
tests/test_evaluate.py: Unit tests for quantitative evaluation framework, normalization, and tolerance matching.
"""

import pandas as pd
import pytest

from evaluate import (
    compute_summary_metrics,
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


class TestComputeSummaryMetrics:
    def test_compute_summary_metrics(self):
        eval_df = pd.DataFrame([
            {"Correct": True, "Grounded": True, "Extracted": "4.0%", "In Source": True},
            {"Correct": True, "Grounded": True, "Extracted": "1000", "In Source": True},
            {"Correct": True, "Grounded": False, "Extracted": "99.8", "In Source": False},
            {"Correct": False, "Grounded": False, "Extracted": None, "In Source": None},
        ])
        metrics = compute_summary_metrics(eval_df)
        assert metrics["total"] == 4
        assert metrics["correct"] == 3
        assert metrics["accuracy_pct"] == 75.0
        assert metrics["grounded"] == 2
        assert metrics["grounding_pct"] == 50.0
        assert metrics["extracted"] == 3
        assert metrics["not_in_source"] == 1
        assert metrics["not_in_source_pct"] == pytest.approx(33.333333333333336)

    def test_compute_summary_metrics_no_extractions(self):
        eval_df = pd.DataFrame([
            {"Correct": False, "Grounded": False, "Extracted": None, "In Source": None},
            {"Correct": False, "Grounded": False, "Extracted": None, "In Source": None},
        ])
        metrics = compute_summary_metrics(eval_df)
        assert metrics["total"] == 2
        assert metrics["extracted"] == 0
        assert metrics["not_in_source"] == 0
        assert metrics["not_in_source_pct"] == 0.0


