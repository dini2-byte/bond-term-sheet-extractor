"""
tests/test_structure.py: Unit and integration tests for DCM comps structuring and data normalization.
"""

import json
from pathlib import Path
import pytest
import pandas as pd

from structure import (
    clean_coupon,
    clean_principal,
    clean_issue_price,
    clean_yield,
    clean_spread,
    structure_filing_extractions,
)


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


class TestStructuring:
    def test_mock_filing_structuring(self, tmp_path):
        mock_data = {
            "extractions": [
                {
                    "extraction_class": "issuer",
                    "extraction_text": "ACME CORP",
                    "char_interval": {"start_pos": 0, "end_pos": 9},
                    "attributes": {"tranche": "all"},
                },
                {
                    "extraction_class": "trade_date",
                    "extraction_text": "January 15, 2026",
                    "char_interval": {"start_pos": 10, "end_pos": 26},
                    "attributes": {"tranche": "deal"},
                },
                {
                    "extraction_class": "tranche_name",
                    "extraction_text": "3.500% Notes due 2031",
                    "char_interval": {"start_pos": 30, "end_pos": 51},
                    "attributes": {"tranche": "2031 Notes"},
                },
                {
                    "extraction_class": "coupon",
                    "extraction_text": "3.500%",
                    "char_interval": {"start_pos": 52, "end_pos": 58},
                    "attributes": {"tranche": "2031 Notes"},
                },
                {
                    "extraction_class": "principal_amount",
                    "extraction_text": "$750,000,000",
                    "char_interval": {"start_pos": 60, "end_pos": 72},
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
        jsonl_path = Path("output/AAPL_FWP_TermSheet_2025-05-06_extractions.jsonl")
        if not jsonl_path.exists():
            pytest.skip("AAPL FWP cached extraction not found on disk")

        df, audit = structure_filing_extractions(jsonl_path)
        assert len(df) == 4
        assert (df["Issuer"] == "APPLE INC.").all()
        assert (df["Trade Date"] == "May 5, 2025").all()
        assert set(df["Coupon (%)"].tolist()) == {4.0, 4.2, 4.5, 4.75}
        assert set(df["Spread (bps)"].tolist()) == {25, 30, 40, 50}
        assert len(audit) == 4
