import pandas as pd

from views.results import (
    STATUS_TAGS,
    build_deal_line,
    column_config_for,
    excel_bytes,
    source_panel_html,
    status_tag,
)


class TestBuildDealLine:
    def test_build_deal_line_usd(self):
        df = pd.DataFrame({
            "Issuer": ["Apple Inc.", "Apple Inc."],
            "Currency": ["USD", "USD"],
            "Principal ($M)": [1500.0, 3000.0],
            "Trade Date": ["May 5, 2025", "May 5, 2025"],
        })
        line = build_deal_line(df)
        assert line == "Apple Inc. · $4.5bn senior notes · 2 bonds · priced May 5, 2025"

    def test_build_deal_line_eur_1bn(self):
        df = pd.DataFrame({
            "Issuer": ["Coca-Cola Co", "Coca-Cola Co"],
            "Currency": ["EUR", "EUR"],
            "Principal ($M)": [500.0, 500.0],
            "Trade Date": ["August 9, 2024", "August 9, 2024"],
        })
        line = build_deal_line(df)
        assert line == "Coca-Cola Co · €1bn senior notes · 2 bonds · priced August 9, 2024"

    def test_build_deal_line_gbp_750m(self):
        df = pd.DataFrame({
            "Issuer": ["Test Issuer"],
            "Currency": ["GBP"],
            "Principal ($M)": [750.0],
        })
        line = build_deal_line(df)
        assert line == "Test Issuer · £750m senior notes · 1 bond"

    def test_build_deal_line_mixed_eur_and_gbp(self):
        df = pd.DataFrame({
            "Issuer": ["AT&T Inc."] * 5,
            "Currency": ["EUR", "EUR", "EUR", "EUR", "GBP"],
            "Principal ($M)": [1000.0, 1250.0, 1000.0, 850.0, 550.0],
            "Trade Date": ["July 27, 2026"] * 5,
        })
        line = build_deal_line(df)
        assert line == "AT&T Inc. · €4.1bn and £550m senior notes · 5 bonds · priced July 27, 2026"


def test_status_tags():
    assert status_tag("Found word for word") == "WORD FOR WORD"
    assert status_tag("Found, but the match is not exact") == "NOT EXACT"
    assert status_tag("Not in the filing") == "NOT IN THE FILING"
    assert set(STATUS_TAGS.values()) == {"WORD FOR WORD", "NOT EXACT", "NOT IN THE FILING"}


def test_source_panel_escapes_text_and_keeps_the_quote_html():
    cs = {"field": "Coupon", "tranche": "4.000% Notes <2028>", "value": "4.000%",
          "status": "Found word for word", "quote_html": "Coupon: <mark>4.000%</mark>"}
    out = source_panel_html(cs)
    assert "Coupon · 4.000% Notes &lt;2028&gt;" in out
    assert '<div class="tse-value">4.000%</div>' in out
    assert '<span class="tse-tag">WORD FOR WORD</span>' in out
    assert '<div class="tse-quote">Coupon: <mark>4.000%</mark></div>' in out


def test_source_panel_without_quote_has_no_quote_block():
    cs = {"field": "Par call", "tranche": "2030", "value": "Not in the filing",
          "status": "Not in the filing", "quote_html": ""}
    assert "tse-quote" not in source_panel_html(cs)


def test_column_config_uses_the_deal_currency():
    eur = pd.DataFrame({"Currency": ["EUR"]})
    assert "Size (€M)" in column_config_for(eur)
    usd = pd.DataFrame({"Currency": ["USD"]})
    assert "Size ($M)" in column_config_for(usd)


def test_excel_bytes_is_an_xlsx_file():
    data = excel_bytes(pd.DataFrame({"Tranche": ["2028"]}))
    assert data[:2] == b"PK"


from views.search import SAVED_TAG, runs_hint, sheet_label


def _sheet(bond_count, currencies):
    return {"accession": "0001-24-000001", "filing_date": "2024-08-09", "chars": 1, "bond_count": bond_count,
            "currencies": currencies, "text": ""}


def test_sheet_labels_name_the_currency():
    assert sheet_label(_sheet(2, ["EUR"]), saved=False) == "Filed 2024-08-09 · 2 bonds in euros"
    assert sheet_label(_sheet(1, ["GBP"]), saved=False) == "Filed 2024-08-09 · 1 bond in pounds"
    assert sheet_label(_sheet(5, ["EUR", "GBP"]), saved=False) == "Filed 2024-08-09 · 5 bonds in euros and pounds"
    assert sheet_label(_sheet(4, ["USD"]), saved=False) == "Filed 2024-08-09 · 4 bonds"


def test_saved_sheets_carry_the_tag():
    assert sheet_label(_sheet(4, ["USD"]), saved=True) == f"Filed 2024-08-09 · 4 bonds  {SAVED_TAG}"


def test_runs_hint():
    assert runs_hint(18, 20) == "18 of 20 runs left today · saved results are free"
