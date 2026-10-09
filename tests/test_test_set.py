"""
tests/test_test_set.py: Pins the hand-keyed non-dollar test set to its filings.
See data/test_set/README.md for how the deals were picked.
"""

import json
import re
from pathlib import Path

import pytest

from lookup import count_bonds

TEST_SET_DIR = Path(__file__).resolve().parent.parent / "data" / "test_set"
KEY = json.loads((TEST_SET_DIR / "answer_key.json").read_text(encoding="utf-8"))

FIELDS = [
    "Tranche", "Currency", "Size (M)", "Coupon (%)", "Issue Price", "Yield (%)",
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


@pytest.mark.xfail(strict=True, reason="milestone 2: Common Codes are counted as CUSIPs")
@pytest.mark.parametrize("stem", sorted(KEY))
def test_count_bonds_matches_key(stem):
    assert count_bonds(raw_text(stem)) == KEY[stem]["bond_count"]
