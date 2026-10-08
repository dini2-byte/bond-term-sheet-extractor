"""
tests/test_fetch.py: Tests for Task A2 - pinned benchmark deals in fetch.py.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

import fetch


def test_deals_to_fetch_pinned_accessions():
    """Verify DEALS_TO_FETCH contains only the 4 pinned deals with accession numbers."""
    deals = fetch.DEALS_TO_FETCH
    assert len(deals) == 4, f"Expected 4 pinned deals, got {len(deals)}"

    tickers = [d["ticker"] for d in deals]
    assert tickers == ["AAPL", "MSFT", "ORCL", "GOOGL"]

    # Verify no AMZN or 424B2
    assert "AMZN" not in tickers
    for d in deals:
        assert d["form"] == "FWP"
        assert "accession" in d
        assert len(d["accession"]) > 0

    expected_accessions = {
        "AAPL": "0001140361-25-017410",
        "MSFT": "0001193125-17-024075",
        "ORCL": "0001193125-25-215807",
        "GOOGL": "0001193125-26-338750",
    }
    for d in deals:
        assert d["accession"] == expected_accessions[d["ticker"]]


def test_fetch_filings_by_accession(tmp_path):
    """Verify fetch_filings fetches using get_by_accession_number."""
    mock_filing = MagicMock()
    mock_filing.filing_date = "2026-01-01"
    mock_filing.text.return_value = "Mock filing content"

    called_accessions = []

    def fake_get_by_accession(acc):
        called_accessions.append(acc)
        return mock_filing

    with patch("fetch.get_by_accession_number", side_effect=fake_get_by_accession):
        manifest = fetch.fetch_filings(output_dir=tmp_path)

    assert len(manifest) == 4
    assert len(called_accessions) == 4
    for d in fetch.DEALS_TO_FETCH:
        assert d["accession"] in called_accessions
        saved_file = tmp_path / f"{d['label']}_2026-01-01.txt"
        assert saved_file.exists()
        assert saved_file.read_text(encoding="utf-8") == "Mock filing content"
