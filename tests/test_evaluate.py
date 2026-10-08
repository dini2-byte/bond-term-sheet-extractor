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
        # Floats rounded to 3 decimal places
        assert matches_value(4.00, 4.0, "Coupon (%)") is True
        assert matches_value(4.0004, 4.0, "Coupon (%)") is True
        assert matches_value(4.005, 4.0, "Coupon (%)") is False
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

    def test_matches_value_strict_required_cases(self):
        # Task C required test cases
        assert matches_value("APPLE INC.", "Apple Inc.", "Issuer") is True
        assert matches_value("Apple", "Apple Inc.", "Issuer") is False
        assert matches_value("May 12, 2025 (T+5)", "May 12, 2025", "Settlement Date") is True
        assert matches_value("May 13, 2025", "May 12, 2025", "Settlement Date") is False
        assert matches_value("Aaa (Moody's) / AA+ (S&P)", "Aaa / AA+", "Ratings") is True
        assert matches_value("Aaa / AA", "Aaa / AA+", "Ratings") is False
        assert matches_value("Aaa", "Aaa / AA+", "Ratings") is False
        assert matches_value(4.0, 4.00, "Coupon (%)") is True
        assert matches_value(4.005, 4.0, "Coupon (%)") is False
        assert matches_value(" 037833ey2 ", "037833EY2", "CUSIP") is True

        # Additional field tests
        assert matches_value(1500.04, 1500.0, "Principal ($M)") is True
        assert matches_value(1500.2, 1500.0, "Principal ($M)") is False
        assert matches_value(25, 25, "Spread (bps)") is True
        assert matches_value(25.4, 25, "Spread (bps)") is False
        assert matches_value(True, 25, "Spread (bps)") is False
        assert matches_value(25, False, "Spread (bps)") is False
        assert matches_value("invalid-date", "May 12, 2025", "Settlement Date") is False
        assert matches_value("May 2028", "May 7, 2028", "Settlement Date") is False
        assert matches_value("30/360", "30/360", "Day Count") is True
        assert matches_value("30", "30/360", "Day Count") is False
        assert matches_value("Not found", None, "Day Count") is True
        assert matches_value(None, "Not found", "Day Count") is True
        assert matches_value("Not found", "30/360", "Day Count") is False

    def test_principal_tolerance(self):
        # 1500.04 and 1500.06 have diff 0.02 <= 0.05
        assert matches_value(1500.04, 1500.06, "Principal ($M)") is True
        # 1500.0 and 1500.06 have diff 0.06 > 0.05
        assert matches_value(1500.0, 1500.06, "Principal ($M)") is False
        assert matches_value(True, 1500.0, "Principal ($M)") is False


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

    def test_tranches_reverse_order_pairing(self):
        t1_gt = {
            "Tranche": "4.000% Notes due 2028", "Issuer": "Apple Inc.", "Ratings": "Aaa / AA+",
            "Trade Date": "May 5, 2025", "Settlement Date": "May 12, 2025", "Principal ($M)": 1500.0,
            "Coupon (%)": 4.0, "Issue Price": 99.804, "Yield (%)": 4.07, "Spread (bps)": 25,
            "Benchmark Treasury": "3.750% due April 15, 2028", "Maturity Date": "May 12, 2028",
            "Day Count": "30/360", "Par Call Date": "April 12, 2028", "CUSIP": "037833EY2"
        }
        t2_gt = {
            "Tranche": "4.200% Notes due 2030", "Issuer": "Apple Inc.", "Ratings": "Aaa / AA+",
            "Trade Date": "May 5, 2025", "Settlement Date": "May 12, 2025", "Principal ($M)": 1000.0,
            "Coupon (%)": 4.2, "Issue Price": 99.830, "Yield (%)": 4.238, "Spread (bps)": 30,
            "Benchmark Treasury": "3.875% due April 30, 2030", "Maturity Date": "May 12, 2030",
            "Day Count": "30/360", "Par Call Date": "April 12, 2030", "CUSIP": "037833EZ9"
        }
        ground_truth = [t1_gt, t2_gt]

        # Extracted in reverse order (t2 then t1)
        extracted_df = pd.DataFrame([t2_gt.copy(), t1_gt.copy()])
        audit_records = [
            {"fields": {k.lower().replace(" ", "_").replace("($m)", "amount").replace("(%)", "").replace("(bps)", "_bps"): {"grounded": True, "found_in_source": True} for k in t2_gt}},
            {"fields": {k.lower().replace(" ", "_").replace("($m)", "amount").replace("(%)", "").replace("(bps)", "_bps"): {"grounded": True, "found_in_source": True} for k in t1_gt}}
        ]

        res = evaluate_deal("TEST_DEAL", extracted_df, audit_records, ground_truth)
        assert len(res) == 28
        # Ensure all fields matched correctly despite reversed order
        assert res["Correct"].all()

    def test_tranche_wrong_cusip_fallback_to_maturity_date(self):
        ground_truth = [{
            "Tranche": "4.000% Notes due 2028", "Issuer": "Apple Inc.", "Ratings": "Aaa / AA+",
            "Trade Date": "May 5, 2025", "Settlement Date": "May 12, 2025", "Principal ($M)": 1500.0,
            "Coupon (%)": 4.0, "Issue Price": 99.804, "Yield (%)": 4.07, "Spread (bps)": 25,
            "Benchmark Treasury": "3.750% due April 15, 2028", "Maturity Date": "May 12, 2028",
            "Day Count": "30/360", "Par Call Date": "April 12, 2028", "CUSIP": "037833EY2"
        }]
        # Extracted has mismatched CUSIP but identical Maturity Date
        extracted_df = pd.DataFrame([{
            "Issuer": "Apple Inc.", "Ratings": "Aaa / AA+", "Trade Date": "May 5, 2025",
            "Settlement Date": "May 12, 2025", "Principal ($M)": 1500.0, "Coupon (%)": 4.0,
            "Issue Price": 99.804, "Yield (%)": 4.07, "Spread (bps)": 25,
            "Benchmark Treasury": "3.750% due April 15, 2028", "Maturity Date": "May 12, 2028",
            "Day Count": "30/360", "Par Call Date": "April 12, 2028", "CUSIP": "WRONGCUSIP"
        }])
        audit_records = [{"fields": {}}]

        res = evaluate_deal("TEST_DEAL", extracted_df, audit_records, ground_truth)
        assert len(res) == 14
        # Paired by maturity date: coupon is correct, but CUSIP is incorrect
        coupon_res = res[res["Field"] == "Coupon (%)"].iloc[0]
        assert bool(coupon_res["Correct"]) is True
        cusip_res = res[res["Field"] == "CUSIP"].iloc[0]
        assert bool(cusip_res["Correct"]) is False

    def test_tranche_no_match_scores_all_fields_incorrect(self):
        ground_truth = [{
            "Tranche": "4.000% Notes due 2028", "Issuer": "Apple Inc.", "Ratings": "Aaa / AA+",
            "Trade Date": "May 5, 2025", "Settlement Date": "May 12, 2025", "Principal ($M)": 1500.0,
            "Coupon (%)": 4.0, "Issue Price": 99.804, "Yield (%)": 4.07, "Spread (bps)": 25,
            "Benchmark Treasury": "3.750% due April 15, 2028", "Maturity Date": "May 12, 2028",
            "Day Count": "30/360", "Par Call Date": "April 12, 2028", "CUSIP": "037833EY2"
        }]
        # Extracted has completely different CUSIP and Maturity Date
        extracted_df = pd.DataFrame([{
            "Issuer": "Other Inc.", "Ratings": "Baa1 / BBB+", "Trade Date": "June 1, 2025",
            "Settlement Date": "June 5, 2025", "Principal ($M)": 500.0, "Coupon (%)": 5.5,
            "Issue Price": 99.0, "Yield (%)": 5.6, "Spread (bps)": 100,
            "Benchmark Treasury": "Treasury", "Maturity Date": "June 1, 2040",
            "Day Count": "30/360", "Par Call Date": "May 1, 2040", "CUSIP": "999999ZZ9"
        }])
        audit_records = [{"fields": {}}]

        res = evaluate_deal("TEST_DEAL", extracted_df, audit_records, ground_truth)
        assert len(res) == 14
        assert not res["Correct"].any()
        assert res["Extracted"].isna().all()
        assert not res["Grounded"].any()
        assert res["In Source"].isna().all()

    def test_extra_extracted_tranche_unmatched_not_scored(self):
        ground_truth = [{
            "Tranche": "4.000% Notes due 2028", "Issuer": "Apple Inc.", "Ratings": "Aaa / AA+",
            "Trade Date": "May 5, 2025", "Settlement Date": "May 12, 2025", "Principal ($M)": 1500.0,
            "Coupon (%)": 4.0, "Issue Price": 99.804, "Yield (%)": 4.07, "Spread (bps)": 25,
            "Benchmark Treasury": "3.750% due April 15, 2028", "Maturity Date": "May 12, 2028",
            "Day Count": "30/360", "Par Call Date": "April 12, 2028", "CUSIP": "037833EY2"
        }]
        # 1 matching tranche and 1 extra extracted tranche
        extracted_df = pd.DataFrame([
            {
                "Issuer": "Apple Inc.", "Ratings": "Aaa / AA+", "Trade Date": "May 5, 2025",
                "Settlement Date": "May 12, 2025", "Principal ($M)": 1500.0, "Coupon (%)": 4.0,
                "Issue Price": 99.804, "Yield (%)": 4.07, "Spread (bps)": 25,
                "Benchmark Treasury": "3.750% due April 15, 2028", "Maturity Date": "May 12, 2028",
                "Day Count": "30/360", "Par Call Date": "April 12, 2028", "CUSIP": "037833EY2"
            },
            {
                "Issuer": "Extra Tranche", "Ratings": "Aaa", "Trade Date": "May 5, 2025",
                "Settlement Date": "May 12, 2025", "Principal ($M)": 200.0, "Coupon (%)": 3.0,
                "Issue Price": 100.0, "Yield (%)": 3.0, "Spread (bps)": 10,
                "Benchmark Treasury": "T", "Maturity Date": "May 12, 2050",
                "Day Count": "30/360", "Par Call Date": "April 12, 2050", "CUSIP": "EXTRA1234"
            }
        ])
        audit_records = [{"fields": {}}, {"fields": {}}]

        res = evaluate_deal("TEST_DEAL", extracted_df, audit_records, ground_truth)
        assert len(res) == 14
        assert res.attrs.get("unmatched_extracted_tranches") == 1

    def test_two_pass_tranche_pairing(self):
        ground_truth = [
            {"Tranche": "T1", "CUSIP": "CUSIP_X", "Maturity Date": "January 1, 2030", "Coupon (%)": 4.0},
            {"Tranche": "T2", "CUSIP": "CUSIP_B", "Maturity Date": "January 1, 2030", "Coupon (%)": 5.0},
        ]
        extracted_df = pd.DataFrame([
            {"Tranche": "E1", "CUSIP": "CUSIP_B", "Maturity Date": "January 1, 2030", "Coupon (%)": 5.0},
            {"Tranche": "E2", "CUSIP": "CUSIP_A", "Maturity Date": "January 1, 2030", "Coupon (%)": 4.0},
        ])
        audit_records = [{"fields": {}}, {"fields": {}}]

        res = evaluate_deal("TEST_DEAL", extracted_df, audit_records, ground_truth)
        # The key tranche with CUSIP B (T2) pairs with extracted B (E1)
        t2_cusip = res[(res["Tranche"] == "T2") & (res["Field"] == "CUSIP")].iloc[0]
        assert t2_cusip["Extracted"] == "CUSIP_B"
        assert bool(t2_cusip["Correct"]) is True

    def test_nan_missing_value_evaluation(self):
        ground_truth = [{
            "Tranche": "T1",
            "CUSIP": "CUSIP_B",
            "Par Call Date": None,
        }]
        extracted_df = pd.DataFrame([{
            "Tranche": "T1",
            "CUSIP": "CUSIP_B",
            "Par Call Date": float("nan"),
        }])
        audit_records = [{"fields": {
            "par_call_date": {"grounded": True, "found_in_source": True}
        }}]

        res = evaluate_deal("TEST_DEAL", extracted_df, audit_records, ground_truth)
        par_call_row = res[res["Field"] == "Par Call Date"].iloc[0]
        assert bool(par_call_row["Correct"]) is True
        assert bool(par_call_row["Grounded"]) is False
    def test_h1_not_found_is_missing_value(self, tmp_path):
        import json
        from structure import structure_filing_extractions
        # Extracted tranche with no day_count extraction
        mock_data = {
            "text": "Apple Inc. May 5, 2025 037833EY2",
            "extractions": [
                {
                    "extraction_class": "issuer",
                    "extraction_text": "Apple Inc.",
                    "char_interval": {"start_pos": 0, "end_pos": 10},
                    "alignment_status": "match_exact",
                    "attributes": {"tranche": "all"},
                },
                {
                    "extraction_class": "cusip",
                    "extraction_text": "037833EY2",
                    "char_interval": {"start_pos": 23, "end_pos": 32},
                    "alignment_status": "match_exact",
                    "attributes": {"tranche": "Tranche 1"},
                },
            ]
        }
        jsonl_path = tmp_path / "mock_no_day_count.jsonl"
        jsonl_path.write_text(json.dumps(mock_data) + "\n", encoding="utf-8")

        df, audit = structure_filing_extractions(jsonl_path)
        # H1: structure.py fills comps-table with None for missing fields, not "Not found"
        assert df["Day Count"].iloc[0] is None

        ground_truth = [{
            "CUSIP": "037833EY2",
            "Day Count": None,
        }]

        res = evaluate_deal("TEST_DEAL", df, audit, ground_truth)
        day_count_row = res[res["Field"] == "Day Count"].iloc[0]
        # Required test assertions
        assert bool(day_count_row["Correct"]) is True
        assert bool(day_count_row["Grounded"]) is False
        assert pd.isna(day_count_row["Extracted"])

        metrics = compute_summary_metrics(res)
        assert metrics["extracted"] == 2

    def test_h4_field_with_value_but_no_audit_entry(self):
        # A field with a value but no audit entry counts as extracted, not grounded and not in source.
        extracted_df = pd.DataFrame([{
            "Issuer": "Apple Inc.",
            "CUSIP": "037833EY2",
            "Day Count": "30/360",
        }])
        # Audit records has entry for CUSIP, but NO entry for Day Count or Issuer
        audit_records = [{"fields": {
            "cusip": {"grounded": True, "found_in_source": True},
        }}]
        ground_truth = [{
            "Issuer": "Apple Inc.",
            "CUSIP": "037833EY2",
            "Day Count": "30/360",
        }]

        res = evaluate_deal("TEST_DEAL", extracted_df, audit_records, ground_truth)
        day_count_row = res[res["Field"] == "Day Count"].iloc[0]
        assert day_count_row["Extracted"] == "30/360"
        assert bool(day_count_row["Grounded"]) is False
        assert day_count_row["In Source"] is False

        metrics = compute_summary_metrics(res)
        # Extracted fields: Issuer (no audit), CUSIP (has audit), Day Count (no audit) = 3 extracted fields
        assert metrics["extracted"] == 3
        # Grounded: only CUSIP = 1
        assert metrics["grounded"] == 1
        # Not-in-source: Issuer and Day Count have no audit, so not in source = 2
        assert metrics["not_in_source"] == 2

    def test_run_evaluation_missing_fixture_raises(self, tmp_path, monkeypatch):
        import json
        from evaluate import run_evaluation
        fake_key_path = tmp_path / "answer_key.json"
        fake_key_path.write_text(json.dumps({"MISSING_DEAL": []}), encoding="utf-8")
        monkeypatch.setattr("evaluate.ANSWER_KEY_PATH", fake_key_path)
        with pytest.raises(FileNotFoundError) as excinfo:
            run_evaluation()
        err_msg = str(excinfo.value)
        assert "MISSING_DEAL" in err_msg
        assert "MISSING_DEAL_extractions.jsonl" in err_msg

    def test_run_evaluation_empty_deals(self, tmp_path, monkeypatch):
        import json
        from evaluate import run_evaluation
        fake_key_path = tmp_path / "answer_key.json"
        fake_key_path.write_text(json.dumps({"AAPL_FWP_TermSheet_2025-05-06": []}), encoding="utf-8")
        monkeypatch.setattr("evaluate.ANSWER_KEY_PATH", fake_key_path)
        monkeypatch.setattr("evaluate.OUTPUT_DIR", tmp_path / "output")
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
        assert metrics["grounding_pct"] == pytest.approx(66.66666666666667)
        assert metrics["extracted"] == 3
        assert metrics["not_in_source"] == 1
        assert metrics["not_in_source_pct"] == pytest.approx(33.333333333333336)

    def test_headline_formatting(self, capsys):
        from evaluate import run_evaluation
        run_evaluation()
        captured = capsys.readouterr().out
        lines = [line.strip() for line in captured.strip().split("\n")]
        assert lines[0].startswith("Field accuracy:")
        assert "Grounded:" in lines[1]
        assert "extracted fields)" in lines[1]
        assert "Not-in-source:" in lines[2]
        assert "extracted fields)" in lines[2]
        assert lines[3].startswith("Unmatched extracted tranches:")

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

    def test_missing_field_placeholder_not_counted_as_hallucination(self):
        # structure.py fills absent text fields with "Not found"; that is a miss, not a hallucination
        extracted_df = pd.DataFrame([{"Issuer": "Apple Inc.", "Par Call Date": "Not found", "CUSIP": "037833EY2"}])
        audit_records = [{"fields": {
            "issuer": {"grounded": True, "found_in_source": True},
            "cusip": {"grounded": True, "found_in_source": True},
        }}]
        ground_truth = [{"Issuer": "Apple Inc.", "Par Call Date": None, "CUSIP": "037833EY2"}]

        res = evaluate_deal("TEST_DEAL", extracted_df, audit_records, ground_truth)
        par_call = res[res["Field"] == "Par Call Date"].iloc[0]
        assert par_call["In Source"] is None

        metrics = compute_summary_metrics(res)
        assert metrics["not_in_source"] == 0
        assert metrics["extracted"] == 2

    def test_fixtures_dir_configuration(self):
        from evaluate import FIXTURES_DIR
        from pathlib import Path
        assert FIXTURES_DIR == Path("data/fixtures")
        fixture_file = FIXTURES_DIR / "AAPL_FWP_TermSheet_2025-05-06_extractions.jsonl"
        assert fixture_file.exists(), f"Fixture file not found: {fixture_file}"


