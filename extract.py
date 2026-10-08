"""
extract.py: Core extraction engine using Google LangExtract.
Runs Gemini-powered extraction on bond filings, verifies source grounding offsets,
saves annotated JSONL, and outputs interactive HTML visualization.
"""

import json
import os
from pathlib import Path
import re
from datetime import datetime, timezone
from dotenv import load_dotenv
import langextract as lx
from fields import PROMPT_DESCRIPTION, FEW_SHOT_EXAMPLES

load_dotenv()

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FIXTURES_DIR = Path("data/fixtures")
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)


def _sanitize_error(error_msg: str) -> str:
    """Ensure API keys are never written to attempt logs."""
    for env_var in ["GEMINI_API_KEY", "GOOGLE_API_KEY"]:
        key = os.getenv(env_var)
        if key and len(key) > 5 and key in error_msg:
            error_msg = error_msg.replace(key, "[REDACTED_API_KEY]")
    error_msg = re.sub(r"AIza[0-9A-Za-z-_]{35}", "[REDACTED_API_KEY]", error_msg)
    return error_msg


def _get_last_outcome(deal: str) -> str | None:
    """Get the outcome of the most recent logged attempt for a deal."""
    attempts_path = FIXTURES_DIR / "attempts.jsonl"
    if not attempts_path.exists():
        return None
    last_outcome = None
    with open(attempts_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("deal") == deal:
                    last_outcome = entry.get("outcome")
            except json.JSONDecodeError:
                continue
    return last_outcome


def _log_attempt(deal: str, model_id: str, outcome: str, error: str | None = None) -> None:
    """Log an extraction attempt to data/fixtures/attempts.jsonl."""
    attempts_path = FIXTURES_DIR / "attempts.jsonl"
    attempts_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "deal": deal,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model_id": model_id,
        "outcome": outcome,
        "error": _sanitize_error(error) if error else None,
    }
    with open(attempts_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def extract_terms(
    filing_path: str | Path,
    model_id: str = "gemini-3.5-flash-lite",
    extraction_passes: int = 1,
    max_char_buffer: int = 40000,
    max_workers: int = 1,
    fixture: bool = False,
) -> lx.data.AnnotatedDocument:
    filing_path = Path(filing_path)
    if not filing_path.exists():
        raise FileNotFoundError(f"Filing not found at: {filing_path}")

    deal = filing_path.stem
    fixture_path = FIXTURES_DIR / f"{deal}_extractions.jsonl"

    if fixture:
        if fixture_path.exists():
            last_outcome = _get_last_outcome(deal)
            if last_outcome == "ok":
                msg = (
                    f"Refusing to run: fixture for deal '{deal}' already exists at {fixture_path} "
                    f"and last logged attempt was successful ('ok')."
                )
                print(msg)
                raise RuntimeError(msg)

    print(f"\n[1/4] Reading document: {filing_path.name}")
    with open(filing_path, "r", encoding="utf-8") as f:
        doc_text = f.read()
    print(f"      Document size: {len(doc_text):,} characters")

    print(f"[2/4] Running LangExtract (model: {model_id})...")
    try:
        result = lx.extract(
            text_or_documents=doc_text,
            prompt_description=PROMPT_DESCRIPTION,
            examples=FEW_SHOT_EXAMPLES,
            model_id=model_id,
            extraction_passes=extraction_passes,
            max_char_buffer=max_char_buffer,
            max_workers=max_workers,
            temperature=0.0,
        )
    except Exception as e:
        _log_attempt(deal=deal, model_id=model_id, outcome="api_error", error=str(e))
        raise

    extractions = getattr(result, "extractions", None) or []
    if not extractions:
        _log_attempt(deal=deal, model_id=model_id, outcome="api_error", error="no extractions returned")
        raise RuntimeError("no extractions returned")

    print(f"\n[3/4] Extraction complete. Total entities captured: {len(extractions)}")

    # Grounding & Trustworthiness Audit
    exact_count = 0
    fuzzy_count = 0
    lesser_count = 0
    none_count = 0
    tranches_found = set()

    for item in extractions:
        tranche = item.attributes.get("tranche", "unassigned") if item.attributes else "unassigned"
        tranches_found.add(tranche)
        status = getattr(item, "alignment_status", None)
        status = getattr(status, "value", status)
        if status == "match_exact":
            exact_count += 1
        elif status == "match_fuzzy":
            fuzzy_count += 1
        elif status == "match_lesser":
            lesser_count += 1
        else:
            none_count += 1

    print(f"      Alignment: exact={exact_count}, fuzzy={fuzzy_count}, lesser={lesser_count}, none={none_count}")
    print(f"      Tranches identified: {sorted(list(tranches_found))}")

    # Save structured JSONL to output/
    base_name = filing_path.stem
    jsonl_filename = f"{base_name}_extractions.jsonl"
    lx.io.save_annotated_documents(
        annotated_documents=[result],
        output_dir=OUTPUT_DIR,
        output_name=jsonl_filename,
        show_progress=False,
    )
    print(f"[4/4] Saved structured data: {OUTPUT_DIR / jsonl_filename}")

    # Save to data/fixtures/ if --fixture flag is present
    if fixture:
        FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
        lx.io.save_annotated_documents(
            annotated_documents=[result],
            output_dir=FIXTURES_DIR,
            output_name=jsonl_filename,
            show_progress=False,
        )
        print(f"      Saved fixture: {FIXTURES_DIR / jsonl_filename}")

    # Log successful attempt
    _log_attempt(deal=deal, model_id=model_id, outcome="ok", error=None)

    # Generate interactive highlighted HTML visualization
    html_content = lx.visualize(result)
    html_filename = f"{base_name}_visualization.html"
    html_path = OUTPUT_DIR / html_filename
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(str(html_content))
    print(f"      Saved HTML visualization: {html_path}")

    return result


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Extract bond terms from SEC filing.")
    parser.add_argument(
        "filing",
        nargs="?",
        default="data/raw_filings/AAPL_FWP_TermSheet_2025-05-06.txt",
        help="Path to filing text file",
    )
    parser.add_argument(
        "--fixture",
        action="store_true",
        help="Save output to data/fixtures/ and enforce one-run rule",
    )
    parser.add_argument(
        "--model",
        default="gemini-3.5-flash-lite",
        help="Model ID to use for extraction",
    )
    args = parser.parse_args()

    try:
        extract_terms(args.filing, model_id=args.model, fixture=args.fixture)
    except RuntimeError as e:
        sys.exit(1)
