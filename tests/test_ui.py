from collections import OrderedDict
from pathlib import Path
import pytest

from structure import structure_filing_extractions
from ui import (
    SCORED_FIELDS,
    load_document_text,
    scored_grounding,
    source_quote,
    comps_table_html,
    field_rows,
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


class TestCompsTableHtml:
    def test_comps_table_html_columns_and_order(self):
        fixture_path = Path("data/fixtures/AAPL_FWP_TermSheet_2025-05-06_extractions.jsonl")
        df, audit_records = structure_filing_extractions(fixture_path)
        html = comps_table_html(df, audit_records)
        assert '<div class="table-wrap">' in html
        assert "<table>" in html

        expected_cols = [
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
            "Checks",
        ]
        # Check all expected headers appear in exact order in the HTML
        last_pos = -1
        for col in expected_cols:
            header_str = f">{col}<"
            pos = html.find(header_str)
            assert pos != -1, f"Column header {col} not found in comps table"
            assert pos > last_pos, f"Column header {col} is out of order"
            last_pos = pos

    def test_comps_table_html_no_index_column(self):
        fixture_path = Path("data/fixtures/AAPL_FWP_TermSheet_2025-05-06_extractions.jsonl")
        df, audit_records = structure_filing_extractions(fixture_path)
        html = comps_table_html(df, audit_records)
        # Check table headers: exactly 11 <th> elements for 11 columns
        th_count = html.count("</th>")
        assert th_count == 11

    def test_comps_table_html_right_aligns_numbers_and_formats(self):
        fixture_path = Path("data/fixtures/AAPL_FWP_TermSheet_2025-05-06_extractions.jsonl")
        df, audit_records = structure_filing_extractions(fixture_path)
        html = comps_table_html(df, audit_records)
        assert "4.000%" in html
        assert "4.200%" in html
        # Check numeric alignment
        assert 'class="num"' in html or 'text-align: right' in html

    def test_comps_table_html_escapes_script_tag(self):
        import pandas as pd
        df = pd.DataFrame([{
            "Tranche": "</td><script>alert(1)</script>",
            "Principal ($M)": 1000.0,
            "Coupon (%)": 4.0,
            "Issue Price": 99.8,
            "Yield (%)": 4.1,
            "Spread (bps)": 25,
            "Benchmark Treasury": "UST",
            "Maturity Date": "May 1, 2030",
            "Par Call Date": "April 1, 2030",
            "CUSIP": "123456789",
            "Validation Status": "PASSED",
        }])
        html = comps_table_html(df, [])
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_comps_table_html_dagger_for_ungrounded(self):
        fixture_path = Path("data/fixtures/MSFT_FWP_TermSheet_2017-01-31_extractions.jsonl")
        df, audit_records = structure_filing_extractions(fixture_path)
        html = comps_table_html(df, audit_records)
        # MSFT has ungrounded extracted fields, which must receive a superscript dagger
        assert "<sup>†</sup>" in html

    def test_comps_table_html_missing_value_shows_na_muted(self):
        import pandas as pd
        df = pd.DataFrame([{
            "Tranche": "Test Tranche",
            "Principal ($M)": None,
            "Coupon (%)": None,
            "Issue Price": None,
            "Yield (%)": None,
            "Spread (bps)": None,
            "Benchmark Treasury": None,
            "Maturity Date": None,
            "Par Call Date": None,
            "CUSIP": None,
            "Validation Status": None,
        }])
        html = comps_table_html(df, [])
        assert "n/a" in html
        assert "muted" in html


class TestFieldRows:
    def test_field_rows_14_rows_and_order(self):
        fixture_path = Path("data/fixtures/AAPL_FWP_TermSheet_2025-05-06_extractions.jsonl")
        _, audit_records = structure_filing_extractions(fixture_path)
        doc_text = load_document_text(fixture_path)
        rows = field_rows(audit_records[0]["fields"], doc_text)
        assert len(rows) == 14
        expected_fields = list(SCORED_FIELDS.keys())
        actual_fields = [r["field"] for r in rows]
        assert actual_fields == expected_fields

    def test_field_rows_keys_and_statuses(self):
        fixture_path = Path("data/fixtures/AAPL_FWP_TermSheet_2025-05-06_extractions.jsonl")
        _, audit_records = structure_filing_extractions(fixture_path)
        doc_text = load_document_text(fixture_path)
        rows = field_rows(audit_records[0]["fields"], doc_text)
        for r in rows:
            assert set(r.keys()) == {"field", "value", "status", "quote_html"}
            assert r["status"] in {"exact", "not exact", "not found"}

    def test_field_rows_not_found_has_empty_quote(self):
        audit_entry = {
            "coupon": {"raw": "Not found", "grounded": False},
        }
        rows = field_rows(audit_entry, "Some filing text")
        coupon_row = next(r for r in rows if r["field"] == "Coupon (%)")
        assert coupon_row["status"] == "not found"
        assert coupon_row["quote_html"] == ""

    def test_field_rows_exact_has_mark_in_quote(self):
        fixture_path = Path("data/fixtures/AAPL_FWP_TermSheet_2025-05-06_extractions.jsonl")
        _, audit_records = structure_filing_extractions(fixture_path)
        doc_text = load_document_text(fixture_path)
        rows = field_rows(audit_records[0]["fields"], doc_text)
        exact_rows = [r for r in rows if r["status"] == "exact"]
        assert len(exact_rows) > 0
        assert any("<mark>" in r["quote_html"] for r in exact_rows)



class TestReviewFixes:
    def test_source_quote_does_not_start_or_end_mid_word(self):
        doc = "alpha bravo charlie delta echo"
        start = doc.index("charlie")
        result = source_quote(doc, start, start + len("charlie"), context=4)
        assert "avo" not in result
        assert "del" not in result
        assert "<mark>charlie</mark>" in result

    def test_checks_column_uses_sentence_case(self):
        from structure import structure_filing_extractions
        from validate import validate_comps_table
        df, audit = structure_filing_extractions(
            "data/fixtures/AAPL_FWP_TermSheet_2025-05-06_extractions.jsonl"
        )
        html_out = comps_table_html(validate_comps_table(df, audit), audit)
        assert "FLAGGED" not in html_out and "PASSED" not in html_out
        assert "Flagged" in html_out
