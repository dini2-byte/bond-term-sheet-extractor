"""
demo.py: Testable logic for demo mode and public deployment.
Encapsulates deal discovery, source highlighting runtime generation,
password authentication, upload validation, and accuracy report parsing.
"""

import hmac
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

import langextract as lx
from evaluate import load_scoring_changes


MAX_UPLOAD_SIZE_BYTES = 500 * 1024  # 500 KB limit


def format_deal_label(issuer: str, trade_date: str) -> str:
    """Format human-readable deal label for benchmark deal selector."""
    return f"{issuer} - {trade_date}"


def list_benchmark_deals(
    fixtures_dir: Path | str = Path("data/fixtures"),
    answer_key_path: Path | str = Path("data/answer_key.json"),
) -> list[dict[str, Any]]:
    """
    List benchmark deals that have an extraction fixture in data/fixtures/.
    Labels each deal by issuer and trade date, not filename.
    """
    fixtures_dir = Path(fixtures_dir)
    answer_key_path = Path(answer_key_path)

    if not fixtures_dir.exists():
        return []

    # Read answer key if present for authoritative labels
    answer_keys: dict[str, list[dict[str, Any]]] = {}
    if answer_key_path.exists():
        try:
            with open(answer_key_path, "r", encoding="utf-8") as f:
                answer_keys = json.load(f)
        except Exception:
            answer_keys = {}

    deals = []
    fixture_files = sorted(fixtures_dir.glob("*_extractions.jsonl"))

    for fixture_path in fixture_files:
        deal_key = fixture_path.name.replace("_extractions.jsonl", "")

        issuer = None
        trade_date = None

        if deal_key in answer_keys and answer_keys[deal_key]:
            first_tranche = answer_keys[deal_key][0]
            issuer = first_tranche.get("Issuer")
            trade_date = first_tranche.get("Trade Date")

        # Fallback to reading metadata directly from fixture JSONL
        if not issuer or not trade_date:
            try:
                with open(fixture_path, "r", encoding="utf-8") as f:
                    for line in f:
                        doc = json.loads(line)
                        for ext in doc.get("extractions", []):
                            e_class = ext.get("extraction_class")
                            e_text = ext.get("extraction_text")
                            if e_class == "issuer" and not issuer:
                                issuer = e_text
                            elif e_class == "trade_date" and not trade_date:
                                trade_date = e_text
                        if issuer and trade_date:
                            break
            except Exception:
                pass

        issuer = issuer or deal_key
        trade_date = trade_date or "Unknown Date"
        label = format_deal_label(issuer, trade_date)

        deals.append({
            "deal_key": deal_key,
            "label": label,
            "fixture_path": fixture_path,
        })

    return deals


def build_visualization_html(fixture_path: Path | str) -> str:
    """Build interactive highlighted source HTML view at runtime using langextract.visualize."""
    fixture_path = Path(fixture_path)
    if not fixture_path.exists():
        raise FileNotFoundError(f"Fixture file not found: {fixture_path}")
    return str(lx.visualize(str(fixture_path)))


def check_password(provided_password: str | None, expected_password: str | None) -> bool:
    """Compare provided password with expected password using constant-time comparison."""
    if not provided_password or not expected_password:
        return False
    return hmac.compare_digest(str(provided_password), str(expected_password))


def check_upload_size(size_bytes: int, max_bytes: int = MAX_UPLOAD_SIZE_BYTES) -> tuple[bool, str | None]:
    """Check whether uploaded file size is within the allowed threshold (500 KB)."""
    if size_bytes > max_bytes:
        limit_kb = max_bytes // 1024
        actual_kb = size_bytes / 1024
        return False, f"Upload rejected: file size ({actual_kb:.1f} KB) exceeds the {limit_kb} KB limit."
    return True, None


def get_gemini_api_key(secrets: dict[str, Any] | None = None) -> str | None:
    """
    Retrieve Gemini API key from Streamlit secrets first, then environment.
    Never prints or logs the key.
    """
    if secrets:
        key = secrets.get("GEMINI_API_KEY")
        if key and isinstance(key, str) and key.strip():
            return key.strip()

    env_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if env_key and env_key.strip():
        return env_key.strip()

    return None


def save_uploaded_filing(content: bytes, target_dir: Path | str | None = None) -> Path:
    """
    Save uploaded filing bytes under a fixed name inside a temp directory.
    Never uses uploaded.name in a path.
    """
    if target_dir is None:
        target_dir = Path(tempfile.mkdtemp())
    else:
        target_dir = Path(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

    file_path = target_dir / "term_sheet.txt"
    file_path.write_bytes(content)
    return file_path


def extract_headline_number(headline_str: str) -> str:
    """Extract headline percentage from a headline string."""
    m = re.search(r"(\d+(?:\.\d+)?%)", headline_str)
    return m.group(1) if m else headline_str.strip()


def extract_deal_and_tranche_counts(headline_str: str) -> tuple[int, int]:
    """Extract deal and tranche counts from a headline string."""
    m = re.search(r"(\d+)\s+deals?,\s*(\d+)\s+tranches?", headline_str)
    if m:
        return int(m.group(1)), int(m.group(2))
    return 0, 0


def format_scoring_change_line(change: dict[str, Any]) -> str:
    """Format one scoring change explanation line."""
    headline_num = extract_headline_number(change.get("headline_before", ""))
    change_desc = change.get("change", "").strip().rstrip(".")
    return f"First scored at {headline_num} before this fix: {change_desc}."


def parse_accuracy_report(
    report_path: Path | str = Path("output/accuracy_benchmark_report.md"),
    scoring_changes_path: Path | str = Path("data/fixtures/scoring_changes.jsonl"),
) -> dict[str, Any] | None:
    """
    Parse accuracy benchmark report for UI display.
    Returns None if report file does not exist.
    """
    report_path = Path(report_path)
    if not report_path.exists():
        return None

    try:
        content = report_path.read_text(encoding="utf-8")
    except Exception:
        return None

    headline_line = None
    grounded_line = None
    not_in_source_line = None

    for line in content.splitlines():
        line = line.strip()
        if line.startswith("Field accuracy:"):
            headline_line = line
        elif line.startswith("Grounded:"):
            grounded_line = line
        elif line.startswith("Not-in-source:"):
            not_in_source_line = line

    if not headline_line or not grounded_line or not not_in_source_line:
        return None

    has_scoring_changes = "Scoring changes after the first run" in content

    scoring_change_lines = []
    if has_scoring_changes:
        changes = load_scoring_changes(Path(scoring_changes_path))
        for c in changes:
            scoring_change_lines.append(format_scoring_change_line(c))

    deals, tranches = extract_deal_and_tranche_counts(headline_line)
    deal_word = "deal" if deals == 1 else "deals"
    tranche_word = "tranche" if tranches == 1 else "tranches"
    benchmark_line = (
        f"Benchmark: {deals} {deal_word}, {tranches} {tranche_word}, "
        "answer keys written before each deal was run. Each deal was run through Gemini once."
    )

    return {
        "headline_line": headline_line,
        "grounded_line": grounded_line,
        "not_in_source_line": not_in_source_line,
        "has_scoring_changes": has_scoring_changes,
        "scoring_change_lines": scoring_change_lines,
        "benchmark_line": benchmark_line,
        "deals_count": deals,
        "tranches_count": tranches,
    }
