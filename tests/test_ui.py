from collections import OrderedDict
from pathlib import Path
import pytest

from structure import structure_filing_extractions
from ui import (
    SCORED_FIELDS,
    load_document_text,
    scored_grounding,
    source_quote,
    TABLE_COLUMNS,
    TEXT_COLUMNS,
    plain_status,
    plain_check,
    size_label,
    table_frame,
    not_exact_mask,
    cell_source,
    _format_cell_display_value,
)


class TestScoredFields:
    def test_scored_fields_14_pairs_and_order(self):
        expected_pairs = [
            ("Issuer", "issuer"),
            ("Ratings", "ratings"),
            ("Trade Date", "trade_date"),
            ("Settlement Date", "settlement_date"),
            ("Principal ($M)", "principal_amount"),
            ("Coupon (%)", "coupon"),
            ("Issue Price", "issue_price"),
            ("Yield (%)", "yield_to_maturity"),
            ("Spread (bps)", "spread_bps"),
            ("Benchmark Treasury", "benchmark_treasury"),
            ("Maturity Date", "maturity_date"),
            ("Day Count", "day_count"),
            ("Par Call Date", "par_call_date"),
            ("CUSIP", "cusip"),
        ]
        assert len(SCORED_FIELDS) == 14
        assert list(SCORED_FIELDS.items()) == expected_pairs


class TestLoadDocumentText:
    def test_load_document_text_reads_first_line_text(self):
        fixture_path = Path("data/fixtures/AAPL_FWP_TermSheet_2025-05-06_extractions.jsonl")
        doc_text = load_document_text(fixture_path)
        assert isinstance(doc_text, str)
        assert len(doc_text) > 0
        assert "Apple Inc." in doc_text

    def test_load_document_text_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_document_text(tmp_path / "missing.jsonl")


class TestScoredGrounding:
    def test_scored_grounding_aapl_gives_92_9(self):
        fixture_path = Path("data/fixtures/AAPL_FWP_TermSheet_2025-05-06_extractions.jsonl")
        _, audit_records = structure_filing_extractions(fixture_path)
        res = scored_grounding(audit_records)
        assert res["grounded"] == 52
        assert res["extracted"] == 56
        assert round(res["percent"], 1) == 92.9

    @pytest.mark.parametrize(
        "fixture_stem, expected_grounded_pct",
        [
            ("AAPL_FWP_TermSheet_2025-05-06", 92.9),
            ("MSFT_FWP_TermSheet_2017-01-31", 32.2),
            ("ORCL_FWP_TermSheet_2025-09-24", 100.0),
        ],
    )
    def test_scored_grounding_matches_benchmark_report(
        self, fixture_stem: str, expected_grounded_pct: float
    ):
        fixture_path = Path(f"data/fixtures/{fixture_stem}_extractions.jsonl")
        _, audit_records = structure_filing_extractions(fixture_path)
        res = scored_grounding(audit_records)
        actual_pct = round(res["percent"], 1)
        assert actual_pct == expected_grounded_pct, (
            f"{fixture_stem}: expected Grounded (%) in report to be {expected_grounded_pct}, "
            f"got {actual_pct} ({res['grounded']}/{res['extracted']} fields)"
        )

    def test_scored_grounding_googl(self):
        # GOOGL has 2 floating-rate tranches shown in the app but not scored by the benchmark.
        # Benchmark scored 24.3% (27/111 across 6 fixed tranches).
        # In the app, all 8 tranches are shown, giving 26.0% (34/131 fields).
        fixture_path = Path("data/fixtures/GOOGL_FWP_TermSheet_2026-08-07_extractions.jsonl")
        _, audit_records = structure_filing_extractions(fixture_path)
        res = scored_grounding(audit_records)
        assert res["grounded"] == 34
        assert res["extracted"] == 131
        assert round(res["percent"], 1) == 26.0


class TestSourceQuote:
    def test_source_quote_wraps_span_in_mark(self):
        doc = "The interest rate is 4.000% per annum payable semi-annually."
        # "4.000%" starts at 21, ends at 27
        quote = source_quote(doc, 21, 27, context=20)
        assert "<mark>4.000%</mark>" in quote

    def test_source_quote_leading_and_trailing_ellipsis(self):
        doc = "A" * 100 + "TARGET" + "B" * 100
        start = 100
        end = 106
        quote = source_quote(doc, start, end, context=20)
        assert quote.startswith("...")
        assert quote.endswith("...")
        assert "<mark>TARGET</mark>" in quote

    def test_source_quote_no_ellipsis_when_not_cut(self):
        doc = "Short text with TARGET inside."
        start = doc.index("TARGET")
        end = start + len("TARGET")
        quote = source_quote(doc, start, end, context=60)
        assert "..." not in quote
        assert "<mark>TARGET</mark>" in quote

    def test_source_quote_escapes_script_tag(self):
        payload = "</td><script>alert(1)</script>"
        doc = f"Prefix text {payload} suffix text."
        start = doc.index(payload)
        end = start + len(payload)
        quote = source_quote(doc, start, end, context=20)
        assert "<script>" not in quote
        assert "&lt;script&gt;" in quote
        assert "<mark>" in quote

    def test_source_quote_keeps_non_ascii(self):
        doc = "Offering size is € 1.5bn senior unsecured notes."
        span = "€ 1.5bn"
        start = doc.index(span)
        end = start + len(span)
        quote = source_quote(doc, start, end, context=20)
        assert "€ 1.5bn" in quote
        assert "<mark>€ 1.5bn</mark>" in quote

    def test_source_quote_collapses_whitespace(self):
        doc = "Line one\n\n   and   two   <TARGET>   three\n\nfour"
        span = "<TARGET>"
        start = doc.index(span)
        end = start + len(span)
        quote = source_quote(doc, start, end, context=30)
        assert "\n" not in quote
        assert "   " not in quote
        assert "<mark>&lt;TARGET&gt;</mark>" in quote

    def test_source_quote_handles_none_or_missing(self):
        assert source_quote("Some text", None, None) == ""
        assert source_quote("", 0, 5) == ""



class TestReviewFixes:
    def test_source_quote_does_not_start_or_end_mid_word(self):
        doc = "alpha bravo charlie delta echo"
        start = doc.index("charlie")
        result = source_quote(doc, start, start + len("charlie"), context=4)
        assert "avo" not in result
        assert "del" not in result
        assert "<mark>charlie</mark>" in result


class TestSlice6UiHelpers:
    def test_table_columns_spec_and_order(self):
        expected_labels = [
            "Tranche",
            "Size ($M)",
            "Coupon",
            "Price",
            "Yield",
            "Spread (bps)",
            "Benchmark",
            "Maturity",
            "Par call",
            "CUSIP",
            "Check",
        ]
        assert [col[0] for col in TABLE_COLUMNS] == expected_labels
        assert len(TABLE_COLUMNS) == 11
        # Check source columns and field classes
        assert TABLE_COLUMNS[0] == ("Tranche", "Tranche", None, "One bond in the deal. A deal often sells several bonds with different maturities.")
        assert TABLE_COLUMNS[1] == ("Size ($M)", "Principal ($M)", "principal_amount", "Amount of this bond sold, in millions of dollars.")
        assert TABLE_COLUMNS[2] == ("Coupon", "Coupon (%)", "coupon", "Yearly interest rate the issuer pays.")
        assert TABLE_COLUMNS[3] == ("Price", "Issue Price", "issue_price", "Price paid per 100 of face value.")
        assert TABLE_COLUMNS[4] == ("Yield", "Yield (%)", "yield_to_maturity", "Return to an investor who buys at the issue price and holds to maturity.")
        assert TABLE_COLUMNS[5] == ("Spread (bps)", "Spread (bps)", "spread_bps", "Extra yield over the benchmark bond, in basis points (1 bp = 0.01%).")
        assert TABLE_COLUMNS[6] == ("Benchmark", "Benchmark Treasury", "benchmark_treasury", "The government bond the spread is measured against, such as a US Treasury, German Bund or UK Gilt.")
        assert TABLE_COLUMNS[7] == ("Maturity", "Maturity Date", "maturity_date", "Date the bond is repaid.")
        assert TABLE_COLUMNS[8] == ("Par call", "Par Call Date", "par_call_date", "Date after which the issuer can repay early at 100.")
        assert TABLE_COLUMNS[9] == ("CUSIP", "CUSIP", "cusip", "The bond's 9-character ID.")
        assert TABLE_COLUMNS[10] == ("Check", None, None, "OK, or the first thing worth checking in this row.")

    def test_plain_status(self):
        assert plain_status({"grounded": True, "raw": "4.000%"}) == "Found word for word"
        assert plain_status({"grounded": False, "raw": "4.000%"}) == "Found, but the match is not exact"
        assert plain_status({"grounded": False, "raw": "Not found"}) == "Not in the filing"
        assert plain_status({"grounded": False, "raw": None}) == "Not in the filing"
        assert plain_status({"grounded": False, "raw": ""}) == "Not in the filing"
        assert plain_status({}) == "Not in the filing"
        assert plain_status(None) == "Not in the filing"

    def test_plain_check_passed(self):
        assert plain_check("PASSED", "None (All checks passed)") == "OK"
        assert plain_check("PASSED", "") == "OK"

    def test_plain_check_flagged_with_multiple_issues(self):
        issues = [
            "WEAK_GROUNDING: coupon (fuzzy, span '4%' vs '4.000%')",
            "WEAK_GROUNDING: maturity_date (fuzzy, span '2028' vs 'May 12, 2028')",
        ]
        res = plain_check("FLAGGED", issues)
        assert res == "Coupon not exact (+1 more)"

        # Also supports semicolon-separated string
        str_issues = "WEAK_GROUNDING: coupon (fuzzy); WEAK_GROUNDING: maturity_date (fuzzy)"
        assert plain_check("FLAGGED", str_issues) == "Coupon not exact (+1 more)"

    def test_plain_check_code_mappings(self):
        assert plain_check("FLAGGED", ["SUSPICIOUS_COUPON: 20% outside plausible range"]) == "Coupon looks unusual"
        assert plain_check("FLAGGED", ["MISSING_COUPON"]) == "Coupon missing"
        assert plain_check("FLAGGED", ["PRICE_DEVIATION: 80 deviates significantly"]) == "Price far from 100"
        assert plain_check("FLAGGED", ["SPREAD_ANOMALY: 2000 bps outside bounds"]) == "Spread looks unusual"
        assert plain_check("FLAGGED", ["DATE_SEQUENCE_ERROR: Maturity <= Trade Date"]) == "Dates out of order"
        assert plain_check("FLAGGED", ["UNGROUNDED: trade_date not anchored to source text"]) == "Trade date not exact"
        assert plain_check("FLAGGED", ["UNKNOWN_CODE: something went wrong"]) == "See validation details"

    def test_table_frame(self):
        from validate import validate_comps_table
        fixture_path = Path("data/fixtures/AAPL_FWP_TermSheet_2025-05-06_extractions.jsonl")
        df, audit_records = structure_filing_extractions(fixture_path)
        vdf = validate_comps_table(df, audit_records)
        tf = table_frame(vdf)

        expected_labels = [col[0] for col in TABLE_COLUMNS]
        assert list(tf.columns) == expected_labels
        assert len(tf) == len(vdf)
        assert list(tf.index) == list(range(len(vdf)))
        assert tf["Coupon"].iloc[0] == 4.0
        assert tf["Check"].iloc[0] != "OK"

    def test_not_exact_mask_shape_and_values(self):
        from validate import validate_comps_table
        fixture_path = Path("data/fixtures/AAPL_FWP_TermSheet_2025-05-06_extractions.jsonl")
        df, audit_records = structure_filing_extractions(fixture_path)
        vdf = validate_comps_table(df, audit_records)
        tf = table_frame(vdf)
        mask = not_exact_mask(vdf, audit_records)

        assert mask.shape == tf.shape
        assert list(mask.columns) == list(tf.columns)
        assert list(mask.index) == list(tf.index)
        assert not mask["Tranche"].any()
        assert not mask["Check"].any()
        assert not mask["Coupon"].iloc[0]

    def test_cell_source_tranche_and_check_return_none(self):
        from validate import validate_comps_table
        fixture_path = Path("data/fixtures/AAPL_FWP_TermSheet_2025-05-06_extractions.jsonl")
        df, audit_records = structure_filing_extractions(fixture_path)
        vdf = validate_comps_table(df, audit_records)
        doc_text = load_document_text(fixture_path)

        assert cell_source(audit_records, 0, "Tranche", vdf, doc_text) is None
        assert cell_source(audit_records, 0, "Check", vdf, doc_text) is None

    def test_cell_source_aapl_first_row_coupon(self):
        from validate import validate_comps_table
        fixture_path = Path("data/fixtures/AAPL_FWP_TermSheet_2025-05-06_extractions.jsonl")
        df, audit_records = structure_filing_extractions(fixture_path)
        vdf = validate_comps_table(df, audit_records)
        doc_text = load_document_text(fixture_path)

        cs = cell_source(audit_records, 0, "Coupon", vdf, doc_text)
        assert cs is not None
        assert cs["field"] == "Coupon"
        assert cs["tranche"] == "4.000% Notes due 2028"
        assert cs["value"] == "4.000%"
        assert cs["status"] == "Found word for word"
        assert "<mark>4.000%</mark>" in cs["quote_html"]



class TestTableFrameReadability:
    def _frame(self, deal):
        from structure import structure_filing_extractions
        from validate import validate_comps_table
        df, audit = structure_filing_extractions(f"data/fixtures/{deal}_extractions.jsonl")
        return table_frame(validate_comps_table(df, audit))

    def test_dates_are_short(self):
        tf = self._frame("MSFT_FWP_TermSheet_2017-01-31")
        assert tf["Maturity"].iloc[0] == "6 Feb 2020"

    def test_missing_text_values_show_na(self):
        tf = self._frame("MSFT_FWP_TermSheet_2017-01-31")
        assert tf["Par call"].iloc[0] == "n/a"


class TestTask4TableLabelsAndFormats:
    def test_size_label(self):
        assert size_label(["USD"]) == "Size ($M)"
        assert size_label(["EUR"]) == "Size (€M)"
        assert size_label(["GBP"]) == "Size (£M)"
        assert size_label(["EUR", "GBP"]) == "Size (M)"
        assert size_label([]) == "Size ($M)"
        assert size_label(None) == "Size ($M)"

    def test_text_columns_contains_benchmark_not_treasury(self):
        assert TEXT_COLUMNS == ("Tranche", "Benchmark", "CUSIP")

    def test_format_cell_display_value_currency_and_spread(self):
        assert _format_cell_display_value(500.0, "Size (€M)", currency="EUR") == "€500.0M"
        assert _format_cell_display_value(300.0, "Size (£M)", currency="GBP") == "£300.0M"
        assert _format_cell_display_value(1500.0, "Size ($M)", currency="USD") == "$1,500.0M"
        assert _format_cell_display_value(108.2, "Spread (bps)") == "+108.2 bps"
        assert _format_cell_display_value(25, "Spread (bps)") == "+25 bps"

    def test_table_frame_usd_deal_keeps_numeric_size_and_whole_spread(self):
        from structure import structure_filing_extractions
        from validate import validate_comps_table
        fixture_path = Path("data/fixtures/AAPL_FWP_TermSheet_2025-05-06_extractions.jsonl")
        df, audit = structure_filing_extractions(fixture_path)
        tf = table_frame(validate_comps_table(df, audit))
        assert "Size ($M)" in tf.columns
        assert tf["Size ($M)"].iloc[0] == 1500.0
        assert tf["Spread (bps)"].iloc[0] == "+25 bps"
        assert "Benchmark" in tf.columns

    def test_table_frame_euro_deal_shows_euro_size_label_and_decimal_spread(self):
        from structure import structure_filing_extractions
        from validate import validate_comps_table
        path = Path("data/test_set/extractions/PG_FWP_TermSheet_EUR_2024-04-22_extractions.jsonl")
        df, audit = structure_filing_extractions(path)
        tf = table_frame(validate_comps_table(df, audit))
        assert "Size (€M)" in tf.columns
        assert tf["Size (€M)"].iloc[0] == 650.0
        assert tf["Spread (bps)"].iloc[0] == "+60.7 bps"

    def test_table_frame_mixed_currency_deal_shows_symbol_in_size_cells(self):
        from structure import structure_filing_extractions
        from validate import validate_comps_table
        path = Path("data/test_set/extractions/T_FWP_TermSheet_EUR_GBP_2026-07-27_extractions.jsonl")
        df, audit = structure_filing_extractions(path)
        tf = table_frame(validate_comps_table(df, audit))
        assert "Size (M)" in tf.columns
        assert tf["Size (M)"].iloc[0] == "€1,000.0M"
        assert tf["Size (M)"].iloc[4] == "£550.0M"

    def test_cell_source_on_benchmark_and_mixed_size(self):
        from structure import structure_filing_extractions
        from validate import validate_comps_table
        aapl_path = Path("data/fixtures/AAPL_FWP_TermSheet_2025-05-06_extractions.jsonl")
        df, audit = structure_filing_extractions(aapl_path)
        vdf = validate_comps_table(df, audit)
        doc_text = load_document_text(aapl_path)
        cs_bmk = cell_source(audit, 0, "Benchmark", vdf, doc_text)
        assert cs_bmk is not None
        assert cs_bmk["field"] == "Benchmark"
        assert cs_bmk["value"] == "3.750% due April 15, 2028"

        t_path = Path("data/test_set/extractions/T_FWP_TermSheet_EUR_GBP_2026-07-27_extractions.jsonl")
        tdf, taudit = structure_filing_extractions(t_path)
        tvdf = validate_comps_table(tdf, taudit)
        tdoc_text = load_document_text(t_path)
        cs_size = cell_source(taudit, 0, "Size (M)", tvdf, tdoc_text)
        assert cs_size is not None
        assert cs_size["value"] == "€1,000.0M"

