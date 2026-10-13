"""
tests/test_test_set.py: Pins the hand-keyed non-dollar test set to its filings.
See data/test_set/README.md for how the deals were picked.
"""

import json
import re
from pathlib import Path

import pytest

from lookup import count_bonds, deal_currencies

TEST_SET_DIR = Path(__file__).resolve().parent.parent / "data" / "test_set"
KEY = json.loads((TEST_SET_DIR / "answer_key.json").read_text(encoding="utf-8"))

FIELDS = [
    "Tranche", "Currency", "Size (M)", "Coupon (%)", "Issue Price", "Yield (%)", "Semi-annual yield (%)",
    "Spread to mid-swaps (bps)", "Benchmark kind", "Benchmark text", "Spread to benchmark (bps)",
    "Maturity Date", "Par Call Date", "Day Count", "Coupon frequency", "ISIN", "Common Code", "CUSIP",
]
VERBATIM_FIELDS = ["Tranche", "Benchmark text", "Maturity Date", "Par Call Date", "Day Count", "ISIN", "Common Code"]
BENCHMARK_KINDS = {"US Treasury", "German government", "UK government", "Government, not named", "None"}
CURRENCIES = {"EUR", "GBP", "JPY"}


def raw_text(stem: str) -> str:
    return (TEST_SET_DIR / "raw" / f"{stem}.txt").read_text(encoding="utf-8")


def squash(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def test_every_key_entry_has_a_filing_and_every_filing_has_a_key_entry():
    filings = {p.stem for p in (TEST_SET_DIR / "raw").glob("*.txt")}
    assert filings == set(KEY)


def test_set_has_enough_euro_and_sterling_deals():
    deals_with = lambda cur: sum(1 for d in KEY.values() if cur in d["currencies"])
    assert deals_with("EUR") >= 6
    assert deals_with("GBP") >= 2


@pytest.mark.parametrize("stem", sorted(KEY))
def test_key_entry_shape(stem):
    deal = KEY[stem]
    assert deal["bond_count"] == len(deal["bonds"])
    assert set(deal["currencies"]) <= CURRENCIES
    assert deal["currencies"] == sorted({b["Currency"] for b in deal["bonds"]})
    for bond in deal["bonds"]:
        assert list(bond) == FIELDS
        assert bond["Benchmark kind"] in BENCHMARK_KINDS
        assert bond["Coupon frequency"] in {"Annual", "Semiannual", "Quarterly"}
        assert (bond["Benchmark text"] is None) == (bond["Benchmark kind"] == "None")


@pytest.mark.parametrize("stem", sorted(KEY))
def test_text_values_appear_in_the_filing(stem):
    text = squash(raw_text(stem))
    no_spaces = re.sub(r"\s+", "", text)
    for bond in KEY[stem]["bonds"]:
        for field in VERBATIM_FIELDS:
            if bond[field] is not None:
                assert squash(bond[field]) in text, f"{bond['Tranche']}: {field}"
        assert bond["CUSIP"] in no_spaces, f"{bond['Tranche']}: CUSIP"


@pytest.mark.parametrize("stem", sorted(KEY))
def test_sizes_appear_in_the_filing(stem):
    text = raw_text(stem)
    symbol = {"EUR": "€", "GBP": "£", "JPY": "¥"}
    for bond in KEY[stem]["bonds"]:
        amount = f"{symbol[bond['Currency']]}{round(bond['Size (M)'] * 1_000_000):,}"
        assert amount in text, f"{bond['Tranche']}: {amount}"


@pytest.mark.parametrize("stem", sorted(KEY))
def test_count_bonds_matches_key(stem):
    assert count_bonds(raw_text(stem)) == KEY[stem]["bond_count"]


def test_count_bonds_benchmark_filings():
    raw_dir = Path(__file__).resolve().parent.parent / "data" / "raw_filings"
    assert count_bonds((raw_dir / "AAPL_FWP_TermSheet_2025-05-06.txt").read_text(encoding="utf-8")) == 4
    assert count_bonds((raw_dir / "MSFT_FWP_TermSheet_2017-01-31.txt").read_text(encoding="utf-8")) == 7
    assert count_bonds((raw_dir / "ORCL_FWP_TermSheet_2025-09-24.txt").read_text(encoding="utf-8")) == 6
    # GOOGL has 8 keyed fixed-rate notes and 2 floating-rate notes (10 total)
    assert count_bonds((raw_dir / "GOOGL_FWP_TermSheet_2026-08-07.txt").read_text(encoding="utf-8")) == 10


@pytest.mark.parametrize("stem", sorted(KEY))
def test_deal_currencies_matches_key(stem):
    assert deal_currencies(raw_text(stem)) == KEY[stem]["currencies"]


def test_deal_currencies_benchmark_filings():
    raw_dir = Path(__file__).resolve().parent.parent / "data" / "raw_filings"
    for deal in [
        "AAPL_FWP_TermSheet_2025-05-06",
        "MSFT_FWP_TermSheet_2017-01-31",
        "ORCL_FWP_TermSheet_2025-09-24",
        "GOOGL_FWP_TermSheet_2026-08-07",
    ]:
        assert deal_currencies((raw_dir / f"{deal}.txt").read_text(encoding="utf-8")) == ["USD"]


def test_deal_currencies_ignores_concurrent_offering_pattern():
    text = (
        "Pricing Term Sheet\n"
        "Issuer: The Procter & Gamble Company\n"
        "Title: $500,000,000 4.500% Notes due 2030\n"
        "Concurrent Offering: €500,000,000 of 3.250% Notes due 2030\n"
        "CUSIP: 742718EU3\n"
    )
    assert deal_currencies(text) == ["USD"]


def test_both_yields_kept_when_the_filing_states_two():
    pg = KEY["PG_FWP_TermSheet_GBP_2017-04-27"]["bonds"]
    assert [(b["Yield (%)"], b["Semi-annual yield (%)"]) for b in pg] == [(1.394, 1.389), (1.809, 1.801)]
    ibm = KEY["IBM_FWP_TermSheet_GBP_2015-07-29"]["bonds"][0]
    assert (ibm["Yield (%)"], ibm["Semi-annual yield (%)"]) == (None, 2.662)


def test_extracted_currency_matches_key():
    from score_test_set import pair_bonds
    from structure import structure_filing_extractions
    for path in sorted((TEST_SET_DIR / "extractions").glob("*_extractions.jsonl")):
        stem = path.name.removesuffix("_extractions.jsonl")
        df, _ = structure_filing_extractions(path)
        pairs = pair_bonds(df, KEY[stem]["bonds"])
        for k, r in pairs:
            assert r is not None
            assert r.get("Currency") == k["Currency"]
