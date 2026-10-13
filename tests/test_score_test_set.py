"""
tests/test_score_test_set.py: Scoring extractor output against the non-dollar test set key.
"""

import pandas as pd

from score_test_set import pair_bonds, score_bond, score_deal, spread_source


def key_bond(**overrides):
    bond = {
        "Tranche": "3.375% notes due 2037", "Currency": "EUR", "Size (M)": 500.0,
        "Coupon (%)": 3.375, "Issue Price": 98.927, "Yield (%)": 3.479, "Semi-annual yield (%)": None,
        "Spread to mid-swaps (bps)": 88, "Benchmark kind": "German government",
        "Benchmark text": "DBR 4.000% due January 4, 2037", "Spread to benchmark (bps)": 108.2,
        "Maturity Date": "August 15, 2037", "Par Call Date": "May 15, 2037",
        "Day Count": "Actual / Actual (ICMA)", "Coupon frequency": "Annual",
        "ISIN": "XS2874154946", "Common Code": "287415494", "CUSIP": "191216DW7",
    }
    bond.update(overrides)
    return bond


def extracted_row(**overrides):
    row = {
        "Tranche": "3.375% notes due 2037", "Principal ($M)": 500.0, "Coupon (%)": 3.375,
        "Issue Price": 98.927, "Yield (%)": 3.479, "Spread (bps)": 108.2,
        "Benchmark Treasury": "DBR 4.000% due January 4, 2037 for 2037 notes",
        "Maturity Date": "August 15, 2037", "CUSIP": "191216DW7", "Currency": "EUR",
    }
    row.update(overrides)
    return row


class TestPairBonds:
    def test_pairs_by_coupon_and_maturity_year_in_any_order(self):
        a = key_bond()
        b = key_bond(Tranche="3.750% notes due 2053", **{"Coupon (%)": 3.75, "Maturity Date": "August 15, 2053"})
        df = pd.DataFrame([
            extracted_row(**{"Coupon (%)": 3.75, "Maturity Date": "August 15, 2053"}),
            extracted_row(),
        ])
        pairs = pair_bonds(df, [a, b])
        assert pairs[0][1]["Coupon (%)"] == 3.375
        assert pairs[1][1]["Coupon (%)"] == 3.75

    def test_unmatched_key_bond_pairs_with_none(self):
        pairs = pair_bonds(pd.DataFrame([extracted_row()]), [key_bond(**{"Coupon (%)": 9.9})])
        assert pairs == [(key_bond(**{"Coupon (%)": 9.9}), None)]

    def test_floating_note_pairs_by_name(self):
        frn = key_bond(Tranche="Floating Rate Notes Due 2028", **{"Coupon (%)": None, "Maturity Date": "February 3, 2028"})
        row = extracted_row(Tranche="Floating Rate Notes", **{"Coupon (%)": None, "Maturity Date": "February 3, 2028"})
        assert pair_bonds(pd.DataFrame([row]), [frn])[0][1] is not None


class TestScoreBond:
    def test_all_right(self):
        result = score_bond(key_bond(), extracted_row())
        assert all(v is True for v in result.values() if v is not None)
        assert result["Benchmark"] is True

    def test_mid_swap_spread_is_wrong(self):
        assert score_bond(key_bond(), extracted_row(**{"Spread (bps)": 88}))["Spread"] is False

    def test_missing_currency_column_scores_false(self):
        row = extracted_row()
        del row["Currency"]
        assert score_bond(key_bond(), row)["Currency"] is False

    def test_missing_row_scores_every_field_false(self):
        assert set(score_bond(key_bond(), None).values()) == {False}

    def test_null_key_value_not_scored(self):
        result = score_bond(key_bond(**{"Spread to benchmark (bps)": None, "Benchmark text": None}), extracted_row())
        assert result["Spread"] is None and result["Benchmark"] is None

    def test_semi_annual_yield_counts_when_no_plain_yield(self):
        bond = key_bond(**{"Yield (%)": None, "Semi-annual yield (%)": 2.662})
        assert score_bond(bond, extracted_row(**{"Yield (%)": 2.662}))["Yield"] is True


class TestSpreadSource:
    def test_labels(self):
        assert spread_source(key_bond(), extracted_row()) == "benchmark"
        assert spread_source(key_bond(), extracted_row(**{"Spread (bps)": 88})) == "mid-swaps"
        assert spread_source(key_bond(), extracted_row(**{"Spread (bps)": 2})) == "other"
        assert spread_source(key_bond(), extracted_row(**{"Spread (bps)": None})) == "missing"
        assert spread_source(key_bond(), None) == "missing"


def test_score_deal_counts_bonds_and_fields():
    entry = {"bond_count": 2, "bonds": [key_bond(), key_bond(Tranche="x", **{"Coupon (%)": 3.75, "Maturity Date": "August 15, 2053"})]}
    result = score_deal(pd.DataFrame([extracted_row()]), entry)
    assert result["bond_count_right"] is False
    assert result["extracted_bonds"] == 1
    assert result["fields"]["Size"] == (1, 2)
