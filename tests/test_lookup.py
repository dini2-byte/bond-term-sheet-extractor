from datetime import date
from pathlib import Path
import pytest

from lookup import (
    TICKER_PATTERN,
    RunBudget,
    find_term_sheets,
    get_edgar_identity,
    is_bond_term_sheet,
    normalize_ticker,
)


class TestNormalizeTicker:
    def test_accepts_clean_and_whitespace(self):
        assert normalize_ticker(" ko ") == "KO"
        assert normalize_ticker("aapl") == "AAPL"
        assert normalize_ticker("BRK.B") == "BRK.B"
        assert normalize_ticker("T-PC") == "T-PC"

    @pytest.mark.parametrize("invalid", ["", "   ", "KO;rm", "TOOLONGTICKER1", "1KO", "$AAPL", "KO/PR"])
    def test_rejects_invalid_tickers(self, invalid: str):
        with pytest.raises(ValueError, match="Enter a stock ticker, for example KO."):
            normalize_ticker(invalid)


class TestIsBondTermSheet:
    def test_valid_pricing_term_sheet(self):
        text = (
            "PRICING TERM SHEET\n"
            "Issuer: Test Corp\n"
            "5.000% Notes due 2030\n"
            "CUSIP: 123456AA1 / US123456AA10"
        )
        assert is_bond_term_sheet(text) is True

    def test_valid_final_term_sheet(self):
        text = (
            "Final Term Sheet\n"
            "Issuer: Test Corp\n"
            "$750,000,000 4.250% Notes due 2035\n"
            "CUSIP: 68389XDH5"
        )
        assert is_bond_term_sheet(text) is True

    def test_structured_note_rejected(self):
        text = (
            "Pricing Supplement No. 1234\n"
            "Auto-callable Contingent Coupon Notes due 2027\n"
            "CUSIP: 123456AA1"
        )
        assert is_bond_term_sheet(text) is False

    def test_missing_cusip_rejected(self):
        text = (
            "Pricing Term Sheet\n"
            "5.000% Notes due 2030\n"
            "No identifier present"
        )
        assert is_bond_term_sheet(text) is False

    def test_missing_notes_due_rejected(self):
        text = (
            "Pricing Term Sheet\n"
            "Maturity: August 2030\n"
            "CUSIP: 123456AA1"
        )
        assert is_bond_term_sheet(text) is False

    def test_term_sheet_after_4000_chars_rejected(self):
        text = ("x" * 4050) + "\nPricing Term Sheet\n5.000% Notes due 2030\nCUSIP: 123456AA1"
        assert is_bond_term_sheet(text) is False


class FakeFiling:
    def __init__(self, accession: str, filing_date: str, text: str):
        self.accession_no = accession
        self.accession = accession
        self.filing_date = filing_date
        self._text = text

    def text(self) -> str:
        return self._text


class FakeCompany:
    def __init__(self, ticker: str):
        if ticker == "UNKNOWN":
            raise LookupError("Not found")
        self.ticker = ticker

    def get_filings(self, form: str = "FWP"):
        return [
            # Filing 1: valid 2-bond term sheet
            FakeFiling(
                accession="0001-26-000001",
                filing_date="2026-08-10",
                text=(
                    "Pricing Term Sheet\n"
                    "Issuer: Fake Corp\n"
                    "4.000% Notes due 2030\n"
                    "CUSIP: 123456AA1\n"
                    "5.000% Notes due 2035\n"
                    "CUSIP: 123456AB9"
                ),
            ),
            # Filing 2: structured note (filtered out)
            FakeFiling(
                accession="0001-26-000002",
                filing_date="2026-08-05",
                text="Pricing Supplement\nNotes due 2028\nCUSIP: 123456AC7",
            ),
            # Filing 3: too long (> max_chars, filtered out)
            FakeFiling(
                accession="0001-26-000003",
                filing_date="2026-08-01",
                text="Pricing Term Sheet\nNotes due 2032\nCUSIP: 123456AD5\n" + ("a" * 70_000),
            ),
            # Filing 4: valid 1-bond term sheet, older date
            FakeFiling(
                accession="0001-26-000004",
                filing_date="2026-07-15",
                text="Final Term Sheet\n3.500% Notes due 2029\nCUSIP: 123456AE3",
            ),
        ]


class TestFindTermSheets:
    def test_filters_max_chars_newest_first_and_bond_count(self):
        results = find_term_sheets("FAKE", scan=10, max_chars=60_000, company_cls=FakeCompany)
        assert len(results) == 2

        # Newest first
        assert results[0]["accession"] == "0001-26-000001"
        assert results[0]["filing_date"] == "2026-08-10"
        assert results[0]["bond_count"] == 2
        assert results[0]["chars"] == len(results[0]["text"])

        assert results[1]["accession"] == "0001-26-000004"
        assert results[1]["filing_date"] == "2026-07-15"
        assert results[1]["bond_count"] == 1

    def test_unknown_ticker_raises_lookup_error(self):
        with pytest.raises(LookupError, match=r"No SEC filer found for UNKNOWN\."):
            find_term_sheets("UNKNOWN", company_cls=FakeCompany)


class TestGetEdgarIdentity:
    def test_returns_secrets_first(self, monkeypatch):
        monkeypatch.setenv("EDGAR_IDENTITY", "Env User env@example.com")
        secrets = {"EDGAR_IDENTITY": "Secret User secret@example.com"}
        assert get_edgar_identity(secrets) == "Secret User secret@example.com"

    def test_returns_env_when_no_secrets(self, monkeypatch):
        monkeypatch.setenv("EDGAR_IDENTITY", "Env User env@example.com")
        assert get_edgar_identity({}) == "Env User env@example.com"
        assert get_edgar_identity(None) == "Env User env@example.com"

    def test_returns_none_when_neither_set(self, monkeypatch):
        monkeypatch.delenv("EDGAR_IDENTITY", raising=False)
        assert get_edgar_identity({}) is None
        assert get_edgar_identity(None) is None

    def test_never_returns_placeholder(self, monkeypatch):
        placeholder = "Baruch Student bstudent@baruch.cuny.edu"
        monkeypatch.setenv("EDGAR_IDENTITY", placeholder)
        assert get_edgar_identity({"EDGAR_IDENTITY": placeholder}) is None
        assert get_edgar_identity({}) is None


class TestRunBudget:
    def test_remaining_and_caps(self):
        b = RunBudget(daily_limit=2, session_limit=2)
        assert b.remaining() == 2

        ok, msg = b.can_run(session_runs=0)
        assert ok is True
        assert msg is None

        # Session cap check
        ok, msg = b.can_run(session_runs=2)
        assert ok is False
        assert msg == "You've used your 2 runs for this visit."

        # Record daily runs
        b.record_run()
        assert b.remaining() == 1
        b.record_run()
        assert b.remaining() == 0

        # Daily cap check
        ok, msg = b.can_run(session_runs=0)
        assert ok is False
        assert msg == "Today's 2 free runs are used up. Try again tomorrow."

    def test_daily_reset_with_injected_today(self):
        current = date(2026, 10, 9)

        def mock_today():
            return current

        b = RunBudget(daily_limit=2, session_limit=2, today=mock_today)
        b.record_run()
        b.record_run()
        assert b.remaining() == 0
        assert b.can_run(0)[0] is False

        # Advance calendar day
        current = date(2026, 10, 10)
        assert b.remaining() == 2
        assert b.can_run(0)[0] is True
