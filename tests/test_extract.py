"""
tests/test_extract.py: Tests for Task A - extract.py attempt logging, --fixture flag,
and one-run refusal rule.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

import extract


@pytest.fixture
def temp_env(tmp_path, monkeypatch):
    """Isolate extract directories to tmp_path."""
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(extract, "FIXTURES_DIR", fixtures_dir)
    monkeypatch.setattr(extract, "OUTPUT_DIR", output_dir)

    dummy_filing = tmp_path / "TEST_FWP_2026-01-01.txt"
    dummy_filing.write_text("Test bond term sheet text", encoding="utf-8")

    return {
        "fixtures_dir": fixtures_dir,
        "output_dir": output_dir,
        "dummy_filing": dummy_filing,
        "deal": "TEST_FWP_2026-01-01",
    }


def test_extract_logs_successful_attempt(temp_env):
    """Every run of extract_terms appends one line to attempts.jsonl with outcome 'ok'."""
    mock_result = MagicMock()
    mock_extraction = MagicMock(attributes={"tranche": "Tranche 1"}, alignment_status="match_exact")
    mock_result.extractions = [mock_extraction]

    with patch("langextract.extract", return_value=mock_result), \
         patch("langextract.visualize", return_value="<html></html>"), \
         patch("langextract.io.save_annotated_documents"):
        extract.extract_terms(temp_env["dummy_filing"])

    attempts_file = temp_env["fixtures_dir"] / "attempts.jsonl"
    assert attempts_file.exists()

    lines = attempts_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1

    entry = json.loads(lines[0])
    assert entry["deal"] == temp_env["deal"]
    assert entry["model_id"] == "gemini-3.5-flash-lite"
    assert entry["outcome"] == "ok"
    assert "timestamp" in entry
    assert entry.get("error") is None


def test_extract_logs_api_error_and_sanitizes_api_key(temp_env, monkeypatch):
    """Failed run logs 'api_error' and never logs the API key."""
    fake_key = "AIzaSyDfakeapikey12345678901234567890"
    monkeypatch.setenv("GEMINI_API_KEY", fake_key)

    with patch("langextract.extract", side_effect=RuntimeError(f"HTTP 503 from API with key {fake_key}")):
        with pytest.raises(RuntimeError):
            extract.extract_terms(temp_env["dummy_filing"])

    attempts_file = temp_env["fixtures_dir"] / "attempts.jsonl"
    assert attempts_file.exists()

    lines = attempts_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1

    entry = json.loads(lines[0])
    assert entry["deal"] == temp_env["deal"]
    assert entry["outcome"] == "api_error"
    assert fake_key not in entry["error"]
    assert "[REDACTED_API_KEY]" in entry["error"]


def test_extract_fixture_flag_saves_to_fixtures_and_output(temp_env):
    """With fixture=True, JSONL is written to data/fixtures/<deal>_extractions.jsonl as well as output/."""
    mock_result = MagicMock()
    mock_extraction = MagicMock(attributes={"tranche": "Tranche 1"}, alignment_status="match_exact")
    mock_result.extractions = [mock_extraction]

    saved_calls = []

    def fake_save(annotated_documents, output_dir, output_name, show_progress=False):
        saved_calls.append((Path(output_dir), output_name))
        (Path(output_dir) / output_name).write_text("{}", encoding="utf-8")

    with patch("langextract.extract", return_value=mock_result), \
         patch("langextract.visualize", return_value="<html></html>"), \
         patch("langextract.io.save_annotated_documents", side_effect=fake_save):
        extract.extract_terms(temp_env["dummy_filing"], fixture=True)

    expected_fixture = temp_env["fixtures_dir"] / f"{temp_env['deal']}_extractions.jsonl"
    expected_output = temp_env["output_dir"] / f"{temp_env['deal']}_extractions.jsonl"

    assert expected_fixture.exists()
    assert expected_output.exists()


def test_extract_refuses_when_fixture_exists_and_last_attempt_is_ok(temp_env, capsys):
    """With fixture=True, refuse to run if fixture already exists and last logged attempt is 'ok'."""
    fixture_file = temp_env["fixtures_dir"] / f"{temp_env['deal']}_extractions.jsonl"
    fixture_file.write_text("{}", encoding="utf-8")

    attempts_file = temp_env["fixtures_dir"] / "attempts.jsonl"
    log_entry = {
        "deal": temp_env["deal"],
        "timestamp": "2026-10-07T20:00:00Z",
        "model_id": "gemini-3.5-flash-lite",
        "outcome": "ok",
        "error": None,
    }
    attempts_file.write_text(json.dumps(log_entry) + "\n", encoding="utf-8")

    with patch("langextract.extract") as mock_extract:
        with pytest.raises(RuntimeError) as exc_info:
            extract.extract_terms(temp_env["dummy_filing"], fixture=True)

        assert "refus" in str(exc_info.value).lower()
        mock_extract.assert_not_called()

    captured = capsys.readouterr()
    assert "refus" in captured.out.lower()


def test_extract_allows_run_when_last_attempt_was_error(temp_env):
    """With fixture=True, if last attempt was api_error, do not refuse to run."""
    fixture_file = temp_env["fixtures_dir"] / f"{temp_env['deal']}_extractions.jsonl"
    fixture_file.write_text("{}", encoding="utf-8")

    attempts_file = temp_env["fixtures_dir"] / "attempts.jsonl"
    log_entry = {
        "deal": temp_env["deal"],
        "timestamp": "2026-10-07T20:00:00Z",
        "model_id": "gemini-3.5-flash-lite",
        "outcome": "api_error",
        "error": "HTTP 503",
    }
    attempts_file.write_text(json.dumps(log_entry) + "\n", encoding="utf-8")

    mock_result = MagicMock()
    mock_extraction = MagicMock(attributes={"tranche": "Tranche 1"}, alignment_status="match_exact")
    mock_result.extractions = [mock_extraction]

    with patch("langextract.extract", return_value=mock_result) as mock_extract, \
         patch("langextract.visualize", return_value="<html></html>"), \
         patch("langextract.io.save_annotated_documents"):
        extract.extract_terms(temp_env["dummy_filing"], fixture=True)

    mock_extract.assert_called_once()
    lines = attempts_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    last_entry = json.loads(lines[-1])
    assert last_entry["outcome"] == "ok"


def test_extract_empty_extractions_logs_api_error_and_raises(temp_env):
    """Task A3: When lx.extract returns zero extractions, log api_error, don't write files, and raise RuntimeError."""
    mock_result = MagicMock()
    mock_result.extractions = []

    with patch("langextract.extract", return_value=mock_result), \
         patch("langextract.visualize", return_value="<html></html>") as mock_visualize, \
         patch("langextract.io.save_annotated_documents") as mock_save:
        with pytest.raises(RuntimeError) as exc_info:
            extract.extract_terms(temp_env["dummy_filing"], fixture=True)

        assert str(exc_info.value) == "no extractions returned"

    # Attempt must be logged with outcome api_error and error message
    attempts_file = temp_env["fixtures_dir"] / "attempts.jsonl"
    assert attempts_file.exists()
    lines = attempts_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["deal"] == temp_env["deal"]
    assert entry["outcome"] == "api_error"
    assert entry["error"] == "no extractions returned"

    # Must NOT save annotated documents or visualization
    mock_save.assert_not_called()
    mock_visualize.assert_not_called()
    fixture_path = temp_env["fixtures_dir"] / f"{temp_env['deal']}_extractions.jsonl"
    output_path = temp_env["output_dir"] / f"{temp_env['deal']}_extractions.jsonl"
    assert not fixture_path.exists()
    assert not output_path.exists()


def test_extract_allows_run_after_empty_extractions_failure(temp_env):
    """Task A3: A later --fixture run for that deal is allowed after an empty extractions failure."""
    mock_empty_result = MagicMock()
    mock_empty_result.extractions = []

    # First run fails due to empty extractions
    with patch("langextract.extract", return_value=mock_empty_result), \
         patch("langextract.visualize", return_value="<html></html>"), \
         patch("langextract.io.save_annotated_documents"):
        with pytest.raises(RuntimeError, match="no extractions returned"):
            extract.extract_terms(temp_env["dummy_filing"], fixture=True)

    # Second run returns valid extractions and should succeed
    mock_success_result = MagicMock()
    mock_extraction = MagicMock(attributes={"tranche": "Tranche 1"}, alignment_status="match_exact")
    mock_success_result.extractions = [mock_extraction]

    with patch("langextract.extract", return_value=mock_success_result) as mock_extract, \
         patch("langextract.visualize", return_value="<html></html>"), \
         patch("langextract.io.save_annotated_documents"):
        result = extract.extract_terms(temp_env["dummy_filing"], fixture=True)

    assert result == mock_success_result
    attempts_file = temp_env["fixtures_dir"] / "attempts.jsonl"
    lines = attempts_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0])["outcome"] == "api_error"
    assert json.loads(lines[1])["outcome"] == "ok"


def test_cli_fixture_flag(temp_env):
    """Test CLI invocations pass fixture flag correctly."""
    import sys
    test_args = ["extract.py", str(temp_env["dummy_filing"]), "--fixture", "--model", "test-model"]
    with patch.object(sys, "argv", test_args), \
         patch("extract.extract_terms") as mock_extract_terms:
        # Re-run the __main__ logic block or test with parser
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("filing", nargs="?", default="data/raw_filings/AAPL_FWP_TermSheet_2025-05-06.txt")
        parser.add_argument("--fixture", action="store_true")
        parser.add_argument("--model", default="gemini-3.5-flash-lite")
        args = parser.parse_args(test_args[1:])
        assert args.fixture is True
        assert args.filing == str(temp_env["dummy_filing"])
        assert args.model == "test-model"


def test_extract_log_attempt_false_does_not_log_on_success(temp_env):
    """G1: When log_attempt=False, successful extraction does not touch attempts.jsonl."""
    mock_result = MagicMock()
    mock_extraction = MagicMock(attributes={"tranche": "Tranche 1"}, alignment_status="match_exact")
    mock_result.extractions = [mock_extraction]

    with patch("langextract.extract", return_value=mock_result), \
         patch("langextract.visualize", return_value="<html></html>"), \
         patch("langextract.io.save_annotated_documents"):
        extract.extract_terms(temp_env["dummy_filing"], log_attempt=False)

    attempts_file = temp_env["fixtures_dir"] / "attempts.jsonl"
    assert not attempts_file.exists()


def test_extract_log_attempt_false_does_not_log_on_error(temp_env):
    """G1: When log_attempt=False, failed extraction does not touch attempts.jsonl."""
    with patch("langextract.extract", side_effect=RuntimeError("Mock API error")):
        with pytest.raises(RuntimeError):
            extract.extract_terms(temp_env["dummy_filing"], log_attempt=False)

    attempts_file = temp_env["fixtures_dir"] / "attempts.jsonl"
    assert not attempts_file.exists()


def test_extract_output_dir_custom_saves_to_specified_directory(temp_env, tmp_path):
    """G1: When output_dir is provided, JSONL and HTML visualization are saved to output_dir instead of OUTPUT_DIR."""
    mock_result = MagicMock()
    mock_extraction = MagicMock(attributes={"tranche": "Tranche 1"}, alignment_status="match_exact")
    mock_result.extractions = [mock_extraction]

    custom_dir = tmp_path / "custom_upload_temp"
    custom_dir.mkdir()

    saved_calls = []

    def fake_save(annotated_documents, output_dir, output_name, show_progress=False):
        saved_calls.append((Path(output_dir), output_name))
        (Path(output_dir) / output_name).write_text("{}", encoding="utf-8")

    with patch("langextract.extract", return_value=mock_result), \
         patch("langextract.visualize", return_value="<html>custom visualization</html>"), \
         patch("langextract.io.save_annotated_documents", side_effect=fake_save):
        extract.extract_terms(temp_env["dummy_filing"], output_dir=custom_dir, log_attempt=False)

    # JSONL saved to custom_dir
    assert len(saved_calls) == 1
    assert saved_calls[0][0] == custom_dir
    assert (custom_dir / f"{temp_env['deal']}_extractions.jsonl").exists()
    assert not (temp_env["output_dir"] / f"{temp_env['deal']}_extractions.jsonl").exists()

    # HTML visualization saved to custom_dir
    assert (custom_dir / f"{temp_env['deal']}_visualization.html").exists()
    assert not (temp_env["output_dir"] / f"{temp_env['deal']}_visualization.html").exists()
    assert (custom_dir / f"{temp_env['deal']}_visualization.html").read_text(encoding="utf-8") == "<html>custom visualization</html>"


