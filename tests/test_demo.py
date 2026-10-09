import json
import os
import tempfile
from pathlib import Path
import pytest

from demo import (
    list_benchmark_deals,
    format_deal_label,
    build_visualization_html,
    check_password,
    check_upload_size,
    get_gemini_api_key,
    save_uploaded_filing,
    parse_accuracy_report,
    extract_headline_number,
    extract_deal_and_tranche_counts,
    format_scoring_change_line,
    visualization_src,
    MAX_UPLOAD_SIZE_BYTES,
)


class TestDealListing:
    def test_format_deal_label(self):
        assert format_deal_label("Apple Inc.", "May 5, 2025") == "Apple Inc. - May 5, 2025"
        assert format_deal_label("Oracle Corporation", "September 24, 2025") == "Oracle Corporation - September 24, 2025"

    def test_list_benchmark_deals_returns_known_fixtures(self):
        deals = list_benchmark_deals()
        assert len(deals) == 4
        deal_keys = [d["deal_key"] for d in deals]
        assert "AAPL_FWP_TermSheet_2025-05-06" in deal_keys
        assert "MSFT_FWP_TermSheet_2017-01-31" in deal_keys
        assert "ORCL_FWP_TermSheet_2025-09-24" in deal_keys
        assert "GOOGL_FWP_TermSheet_2026-08-07" in deal_keys

    def test_deal_labels_match_glossary_and_example(self):
        deals = list_benchmark_deals()
        labels = {d["deal_key"]: d["label"] for d in deals}
        assert labels["AAPL_FWP_TermSheet_2025-05-06"] == "Apple Inc. - May 5, 2025"
        assert labels["MSFT_FWP_TermSheet_2017-01-31"] == "Microsoft Corporation - January 30, 2017"
        assert labels["ORCL_FWP_TermSheet_2025-09-24"] == "Oracle Corporation - September 24, 2025"
        assert labels["GOOGL_FWP_TermSheet_2026-08-07"] == "Alphabet Inc. - August 6, 2026"

    def test_list_benchmark_deals_ignores_non_deal_jsonl(self, tmp_path):
        fixtures_dir = tmp_path / "fixtures"
        fixtures_dir.mkdir()
        # Non-deal files
        (fixtures_dir / "attempts.jsonl").write_text('{"deal": "AAPL"}\n')
        (fixtures_dir / "scoring_changes.jsonl").write_text('{"date": "2026-10-08"}\n')
        # One valid fixture
        mock_doc = {
            "document_id": "test_doc",
            "text": "Issuer: TestCorp\nTrade Date: June 1, 2025\n",
            "extractions": [
                {"extraction_class": "issuer", "extraction_text": "TestCorp"},
                {"extraction_class": "trade_date", "extraction_text": "June 1, 2025"}
            ]
        }
        (fixtures_dir / "TEST_FWP_TermSheet_2025-06-01_extractions.jsonl").write_text(json.dumps(mock_doc) + "\n")

        deals = list_benchmark_deals(fixtures_dir=fixtures_dir, answer_key_path=tmp_path / "nonexistent.json")
        assert len(deals) == 1
        assert deals[0]["deal_key"] == "TEST_FWP_TermSheet_2025-06-01"
        assert deals[0]["label"] == "TestCorp - June 1, 2025"


class TestSourceHighlighting:
    def test_build_visualization_html(self):
        fixture_path = Path("data/fixtures/AAPL_FWP_TermSheet_2025-05-06_extractions.jsonl")
        html = build_visualization_html(fixture_path)
        assert isinstance(html, str)
        assert len(html) > 1000
        assert "lx-highlight" in html


class TestVisualizationSrc:
    def test_visualization_src_prefix_and_roundtrip(self):
        import base64
        prefix = "data:text/html;charset=utf-8;base64,"
        sample_html = "<html><body><h1>Deal Terms: € 1.5bn</h1></body></html>"
        result = visualization_src(sample_html)
        assert result.startswith(prefix)
        encoded_data = result[len(prefix):]
        decoded = base64.b64decode(encoded_data.encode("ascii")).decode("utf-8")
        assert decoded == sample_html

    def test_visualization_src_no_script_substring(self):
        malicious_html = "<p>Test</p></script><script>alert(1)</script>"
        result = visualization_src(malicious_html)
        assert "<script>" not in result


class TestPasswordAndUpload:
    def test_check_password_correct(self):
        assert check_password("my-secret-pw", "my-secret-pw") is True

    def test_check_password_incorrect(self):
        assert check_password("wrong-pw", "my-secret-pw") is False

    def test_check_password_empty_or_none(self):
        assert check_password("", "my-secret-pw") is False
        assert check_password(None, "my-secret-pw") is False
        assert check_password("my-secret-pw", "") is False
        assert check_password("my-secret-pw", None) is False
        assert check_password(None, None) is False

    def test_check_upload_size_within_limit(self):
        ok, msg = check_upload_size(400 * 1024)
        assert ok is True
        assert msg is None

    def test_check_upload_size_exact_boundary(self):
        ok, msg = check_upload_size(500 * 1024)
        assert ok is True
        assert msg is None

    def test_check_upload_size_exceeds_limit(self):
        ok, msg = check_upload_size(501 * 1024)
        assert ok is False
        assert msg is not None
        assert "500 KB" in msg

    def test_get_gemini_api_key_priority(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "env-key")
        secrets = {"GEMINI_API_KEY": "secret-key"}
        assert get_gemini_api_key(secrets) == "secret-key"

    def test_get_gemini_api_key_env_fallback(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "env-key")
        assert get_gemini_api_key({}) == "env-key"
        assert get_gemini_api_key(None) == "env-key"

    def test_get_gemini_api_key_google_env_fallback(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("GOOGLE_API_KEY", "google-env-key")
        assert get_gemini_api_key({}) == "google-env-key"

    def test_save_uploaded_filing_fixed_name(self, tmp_path):
        content = b"Mock filing text content"
        saved = save_uploaded_filing(content, target_dir=tmp_path)
        assert saved.name == "term_sheet.txt"
        assert saved.read_bytes() == content
        assert "uploaded" not in saved.name


class TestAccuracyReport:
    def test_extract_headline_number(self):
        line = "Field accuracy: 88.0% (308/350 fields, 4 deals, 25 tranches)"
        assert extract_headline_number(line) == "88.0%"
        assert extract_headline_number("88.0%") == "88.0%"

    def test_extract_deal_and_tranche_counts(self):
        line = "Field accuracy: 98.3% (344/350 fields, 4 deals, 25 tranches)"
        deals, tranches = extract_deal_and_tranche_counts(line)
        assert deals == 4
        assert tranches == 25

    def test_format_scoring_change_line(self):
        change = {
            "date": "2026-10-08",
            "change": "CUSIP cell keeps only the 9-character CUSIP; it had kept the ISIN too, which failed every CUSIP and broke tranche pairing in GOOGL",
            "headline_before": "Field accuracy: 88.0% (308/350 fields, 4 deals, 25 tranches)",
        }
        formatted = format_scoring_change_line(change)
        assert formatted == "First scored at 88.0% before this fix: CUSIP cell keeps only the 9-character CUSIP; it had kept the ISIN too, which failed every CUSIP and broke tranche pairing in GOOGL."

    def test_parse_accuracy_report_real_file(self):
        info = parse_accuracy_report()
        assert info is not None
        assert info["headline_line"].startswith("Field accuracy:")
        assert info["grounded_line"].startswith("Grounded:")
        assert info["not_in_source_line"].startswith("Not-in-source:")
        assert info["has_scoring_changes"] is True
        assert len(info["scoring_change_lines"]) >= 1
        assert "First scored at 88.0% before this fix:" in info["scoring_change_lines"][0]
        assert info["benchmark_line"] == "Benchmark: 4 deals, 25 tranches, answer keys written before each deal was run. Each deal was run through Gemini once."

    def test_parse_accuracy_report_missing_file(self, tmp_path):
        assert parse_accuracy_report(report_path=tmp_path / "missing.md") is None


class TestStreamlitDeprecations:
    def test_app_source_has_no_deprecated_components_or_container_width(self):
        """G2: app.py must not contain use_container_width or components.html."""
        app_source = Path("app.py").read_text(encoding="utf-8")
        assert "use_container_width" not in app_source
        assert "components.html" not in app_source
        assert "streamlit.components.v1" not in app_source

    def test_app_renders_iframe_without_deprecation_warnings(self):
        """G2: app.py uses st.iframe and renders highlighted source without exceptions."""
        from streamlit.testing.v1 import AppTest
        import base64
        app_path = Path(__file__).resolve().parent.parent / "app.py"
        at = AppTest.from_file(str(app_path))
        at.run(timeout=10)
        assert len(at.exception) == 0
        iframe_elements = at.get("iframe")
        assert len(iframe_elements) > 0
        src = iframe_elements[0].proto.src
        assert src.startswith("data:text/html;charset=utf-8;base64,")
        decoded = base64.b64decode(src.split(",", 1)[1]).decode("utf-8")
        assert "lx-highlight" in decoded


class TestLiveUploadG1:
    def test_live_upload_passes_log_attempt_false_and_temp_output_dir(self):
        """G1: app.py must pass log_attempt=False and output_dir=<temp_dir> to extract_terms."""
        from streamlit.testing.v1 import AppTest
        from unittest.mock import MagicMock, patch

        mock_extract_terms = MagicMock()
        with patch("extract.extract_terms", mock_extract_terms), patch("app.extract_terms", mock_extract_terms):
            app_path = Path(__file__).resolve().parent.parent / "app.py"
            at = AppTest.from_file(str(app_path))
            at.secrets["APP_PASSWORD"] = "test-pw"
            at.secrets["GEMINI_API_KEY"] = "mock-key"
            at.run(timeout=10)

            # Enter password in 'Try your own term sheet' section
            at.text_input[0].set_value("test-pw").run()
            # Upload a file
            dummy_content = b"Mock bond term sheet content"
            at.file_uploader[0].upload("test_terms.txt", dummy_content).run()
            # Trigger extraction button
            at.button[0].click().run()

            assert mock_extract_terms.called
            call_kwargs = mock_extract_terms.call_args.kwargs
            assert call_kwargs.get("log_attempt") is False
            assert call_kwargs.get("output_dir") is not None
            assert isinstance(call_kwargs.get("output_dir"), Path)
            assert str(call_kwargs.get("output_dir")) != "output"




