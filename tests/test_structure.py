"""
tests/test_structure.py: Unit and integration tests for DCM comps structuring and data normalization.
"""

import json
from pathlib import Path
import pytest
import pandas as pd

from structure import (
    assess_grounding,
    clean_coupon,
    clean_cusip,
    clean_principal,
    clean_issue_price,
    clean_yield,
    clean_spread,
    grounding_summary,
    normalize_date,
    normalize_ratings,
    structure_filing_extractions,
)


class TestCleanCusip:
    def test_clean_cusip_examples(self):
        assert clean_cusip("594918 BV5 / US594918BV54") == "594918BV5"
        assert clean_cusip("68389XDH5 / US68389XDH52") == "68389XDH5"
        assert clean_cusip("02079K CL9 / US02079KCL98") == "02079KCL9"
        assert clean_cusip("037833EY2") == "037833EY2"

    def test_clean_cusip_lowercase(self):
        assert clean_cusip("68389xdh5 / us68389xdh52") == "68389XDH5"

    def test_clean_cusip_no_cusip_returns_none(self):
        assert clean_cusip("Not found") is None
        assert clean_cusip("None") is None
        assert clean_cusip("") is None
        assert clean_cusip(None) is None
        assert clean_cusip("US594918BV54") is None

    def test_comps_table_cusip_cell_and_audit_record(self):
        fixture_path = Path("data/fixtures/MSFT_FWP_TermSheet_2017-01-31_extractions.jsonl")
        assert fixture_path.exists()
        df, audit = structure_filing_extractions(fixture_path)
        assert df["CUSIP"].iloc[0] == "594918BV5"
        assert audit[0]["fields"]["cusip"]["raw"] == "594918 BV5 / US594918BV54"




class TestNormalizeDate:
    def test_normalize_date_required_cases(self):
        assert normalize_date("On or after April 12, 2028") == "April 12, 2028"
        assert normalize_date("May 12, 2025 (T+5)") == "May 12, 2025"
        assert normalize_date("Sept. 14, 2026") == "September 14, 2026"
        assert normalize_date("May 2028") is None
        assert normalize_date("2028") is None
        assert normalize_date(None) is None
        assert normalize_date("") is None

    def test_normalize_date_h3_cases(self):
        assert normalize_date("Sep. 9, 2025") == "September 9, 2025"
        assert normalize_date("Sept. 9, 2025") == "September 9, 2025"
        assert normalize_date("Aug. 26, 2030") == "August 26, 2030"
        assert normalize_date("Feb 31, 2025") is None



class TestNormalizeRatings:
    def test_normalize_ratings_required_cases(self):
        assert normalize_ratings("Aaa (stable) by Moody’s Investors Service, Inc.\nAA+ (stable) by Standard & Poor’s Ratings Services") == "Aaa / AA+"
        assert normalize_ratings("Moody’s, Aaa (negative outlook); S&P, AAA (stable outlook)") == "Aaa / AAA"
        assert normalize_ratings("Moody’s: Aa2 (Stable); S&P: AA+ (Stable)") == "Aa2 / AA+"
        assert normalize_ratings("A1 by Moody’s Investor Service, Inc.\nAA by Standard & Poor’s Ratings Services\nAA- by Fitch Ratings Inc.") == "A1 / AA / AA-"
        assert normalize_ratings("Aaa / AA+") == "Aaa / AA+"
        assert normalize_ratings("Not rated") is None
        assert normalize_ratings(None) is None
        assert normalize_ratings("") is None

    def test_normalize_ratings_h2_cases(self):
        assert normalize_ratings("N/A") is None
        assert normalize_ratings("NA") is None
        assert normalize_ratings("NR") is None
        assert normalize_ratings("A rating of Aa1 / AA+") == "Aa1 / AA+"
        assert normalize_ratings("Baa1 / A / A-") == "Baa1 / A / A-"
        assert normalize_ratings("A (stable) by S&P") == "A"




class TestCleaners:
    def test_clean_coupon(self):
        assert clean_coupon("4.000%") == 4.0
        assert clean_coupon("4.25 %") == 4.25
        assert clean_coupon("4.50") == 4.5
        assert clean_coupon(None) is None
        assert clean_coupon("") is None
        assert clean_coupon("N/A") is None

    def test_clean_principal(self):
        assert clean_principal("$1,500,000,000") == 1500.0
        assert clean_principal("$1,000,000,000") == 1000.0
        assert clean_principal("$500,000,000") == 500.0
        assert clean_principal("750,000,000") == 750.0
        assert clean_principal(None) is None
        assert clean_principal("") is None

    def test_clean_principal_words(self):
        assert clean_principal("$1,500,000,000") == 1500.0
        assert clean_principal("$1.5 billion") == 1500.0
        assert clean_principal("$750 million") == 750.0
        assert clean_principal("US$1,000,000,000") == 1000.0
        assert clean_principal("$500,000,000 aggregate principal amount") == 500.0
        assert clean_principal("$1,500 million") == 1500.0
        assert clean_principal("1,250.5 million") == 1250.5
        assert clean_principal("$2,000mm") == 2000.0
        assert clean_principal("£1,250,000,000") == 1250.0

    def test_clean_principal_h5_cases(self):
        assert clean_principal("$1.5B") == 1500.0
        assert clean_principal("$750MM") == 750.0
        assert clean_principal("$2bn") == 2000.0



    def test_clean_issue_price(self):
        assert clean_issue_price("99.804%") == 99.804
        assert clean_issue_price("99.804") == 99.804
        assert clean_issue_price("100.000") == 100.0
        assert clean_issue_price(None) is None
        assert clean_issue_price("") is None

    def test_clean_yield(self):
        assert clean_yield("4.070%") == 4.07
        assert clean_yield("4.527 %") == 4.527
        assert clean_yield("4.834") == 4.834
        assert clean_yield(None) is None

    def test_clean_spread(self):
        assert clean_spread("25 basis points") == 25
        assert clean_spread("+30 bps") == 30
        assert clean_spread("+40") == 40
        assert clean_spread("50 bps") == 50
        assert clean_spread(None) is None
        assert clean_spread("") is None


class TestAssessGrounding:
    def test_assess_grounding_exact(self):
        item = {
            "extraction_text": "4.000%",
            "char_interval": {"start_pos": 10, "end_pos": 16},
            "alignment_status": "match_exact",
        }
        doc_text = "01234567894.000%extra"
        res = assess_grounding(item, doc_text)
        assert res["grounded"] is True
        assert res["grounding_quality"] == "exact"
        assert res["span_text"] == "4.000%"
        assert res["alignment_status"] == "match_exact"

    def test_assess_grounding_fuzzy_not_grounded(self):
        item = {
            "extraction_text": "4.000%",
            "char_interval": {"start_pos": 10, "end_pos": 16},
            "alignment_status": "match_fuzzy",
        }
        doc_text = "01234567894.000%extra"
        res = assess_grounding(item, doc_text)
        assert res["grounded"] is False
        assert res["grounding_quality"] == "fuzzy"
        assert res["span_text"] == "4.000%"
        assert res["alignment_status"] == "match_fuzzy"

    def test_assess_grounding_span_mismatch(self):
        item = {
            "extraction_text": "4.000%",
            "char_interval": {"start_pos": 10, "end_pos": 16},
            "alignment_status": "match_exact",
        }
        doc_text = "01234567894.200%extra"
        res = assess_grounding(item, doc_text)
        assert res["grounded"] is False
        assert res["grounding_quality"] == "span_mismatch"
        assert res["span_text"] == "4.200%"
        assert res["found_in_source"] is False

    def test_assess_grounding_no_interval(self):
        item = {
            "extraction_text": "4.000%",
            "char_interval": None,
            "alignment_status": None,
        }
        res = assess_grounding(item, "some text")
        assert res["grounded"] is False
        assert res["grounding_quality"] == "none"
        assert res["span_text"] is None

    def test_assess_grounding_no_doc_text(self):
        item = {
            "extraction_text": "4.000%",
            "char_interval": {"start_pos": 0, "end_pos": 6},
            "alignment_status": "match_exact",
        }
        res = assess_grounding(item, "")
        assert res["grounded"] is False
        assert res["grounding_quality"] == "no_source_text"
        assert res["found_in_source"] is False

    def test_assess_grounding_found_in_source_true(self):
        item = {
            "extraction_text": "Aaa\n   AA+",
            "char_interval": {"start_pos": 0, "end_pos": 7},
            "alignment_status": "match_fuzzy",
        }
        doc_text = "Aaa AA+ ratings assigned"
        res = assess_grounding(item, doc_text)
        assert res["found_in_source"] is True

    def test_assess_grounding_found_in_source_false(self):
        item = {
            "extraction_text": "BBB-",
            "char_interval": {"start_pos": 0, "end_pos": 4},
            "alignment_status": "match_fuzzy",
        }
        doc_text = "Aaa AA+ ratings assigned"
        res = assess_grounding(item, doc_text)
        assert res["found_in_source"] is False

    def test_assess_grounding_found_in_source_no_doc(self):
        item = {
            "extraction_text": "Apple Inc.",
            "char_interval": {"start_pos": 0, "end_pos": 10},
            "alignment_status": "match_exact",
        }
        res = assess_grounding(item, "")
        assert res["found_in_source"] is False


class TestGroundingSummary:
    def test_grounding_summary(self):
        audit_records = [
            {
                "tranche": "Tranche 1",
                "fields": {
                    "coupon": {"grounded": True},
                    "price": {"grounded": True},
                },
            },
            {
                "tranche": "Tranche 2",
                "fields": {
                    "coupon": {"grounded": False},
                },
            },
        ]
        res = grounding_summary(audit_records)
        assert res["grounded"] == 2
        assert res["total"] == 3
        assert res["pct"] == pytest.approx(66.66666666666667)

    def test_grounding_summary_empty(self):
        res = grounding_summary([])
        assert res == {"grounded": 0, "total": 0, "pct": 0.0}



class TestStructuring:
    def test_mock_filing_structuring(self, tmp_path):
        mock_text = "ACME CORP January 15, 2026    3.500% Notes due 2031 3.500%  $750,000,000"
        mock_data = {
            "text": mock_text,
            "extractions": [
                {
                    "extraction_class": "issuer",
                    "extraction_text": "ACME CORP",
                    "char_interval": {"start_pos": 0, "end_pos": 9},
                    "alignment_status": "match_exact",
                    "attributes": {"tranche": "all"},
                },
                {
                    "extraction_class": "trade_date",
                    "extraction_text": "January 15, 2026",
                    "char_interval": {"start_pos": 10, "end_pos": 26},
                    "alignment_status": "match_exact",
                    "attributes": {"tranche": "deal"},
                },
                {
                    "extraction_class": "tranche_name",
                    "extraction_text": "3.500% Notes due 2031",
                    "char_interval": {"start_pos": 30, "end_pos": 51},
                    "alignment_status": "match_exact",
                    "attributes": {"tranche": "2031 Notes"},
                },
                {
                    "extraction_class": "coupon",
                    "extraction_text": "3.500%",
                    "char_interval": {"start_pos": 52, "end_pos": 58},
                    "alignment_status": "match_exact",
                    "attributes": {"tranche": "2031 Notes"},
                },
                {
                    "extraction_class": "principal_amount",
                    "extraction_text": "$750,000,000",
                    "char_interval": {"start_pos": 60, "end_pos": 72},
                    "alignment_status": "match_exact",
                    "attributes": {"tranche": "2031 Notes"},
                },
            ]
        }
        jsonl_file = tmp_path / "mock_extractions.jsonl"
        with open(jsonl_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(mock_data) + "\n")

        df, audit = structure_filing_extractions(jsonl_file)
        assert len(df) == 1
        row = df.iloc[0]
        assert row["Tranche"] == "3.500% Notes due 2031"
        assert row["Issuer"] == "ACME CORP"
        assert row["Trade Date"] == "January 15, 2026"
        assert row["Coupon (%)"] == 3.5
        assert row["Principal ($M)"] == 750.0

        assert len(audit) == 1
        assert audit[0]["tranche"] == "2031 Notes"
        assert audit[0]["fields"]["issuer"]["grounded"] is True
        assert audit[0]["fields"]["coupon"]["grounded"] is True

    def test_cached_aapl_fwp_extractions(self):
        jsonl_path = Path("data/fixtures/AAPL_FWP_TermSheet_2025-05-06_extractions.jsonl")
        assert jsonl_path.exists(), f"AAPL FWP fixture not found on disk: {jsonl_path}"

        df, audit = structure_filing_extractions(jsonl_path)
        assert len(df) == 4
        assert (df["Issuer"] == "APPLE INC.").all()
        assert (df["Trade Date"] == "May 5, 2025").all()
        assert set(df["Coupon (%)"].tolist()) == {4.0, 4.2, 4.5, 4.75}
        assert set(df["Spread (bps)"].tolist()) == {25, 30, 40, 50}
        assert len(audit) == 4

        # 2028 tranche coupon is grounded with exact match
        t2028 = [a for a in audit if a["tranche"] == "2028 Notes"][0]
        coupon_meta = t2028["fields"]["coupon"]
        assert coupon_meta["grounded"] is True
        assert coupon_meta["grounding_quality"] == "exact"

        # Settlement date of every tranche is not grounded (fuzzy alignment)
        for a in audit:
            settlement_meta = a["fields"]["settlement_date"]
            assert settlement_meta["grounded"] is False

