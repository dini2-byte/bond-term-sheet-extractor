"""
extract.py: Core extraction engine using Google LangExtract.
Runs Gemini-powered extraction on bond filings, verifies source grounding offsets,
saves annotated JSONL, and outputs interactive HTML visualization.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import langextract as lx
from fields import PROMPT_DESCRIPTION, FEW_SHOT_EXAMPLES

load_dotenv()

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def extract_terms(
    filing_path: str | Path,
    model_id: str = "gemini-3.5-flash-lite",
    extraction_passes: int = 1,
    max_char_buffer: int = 40000,
    max_workers: int = 1,
) -> lx.data.AnnotatedDocument:
    filing_path = Path(filing_path)
    if not filing_path.exists():
        raise FileNotFoundError(f"Filing not found at: {filing_path}")

    print(f"\n[1/4] Reading document: {filing_path.name}")
    with open(filing_path, "r", encoding="utf-8") as f:
        doc_text = f.read()
    print(f"      Document size: {len(doc_text):,} characters")

    print(f"[2/4] Running LangExtract (model: {model_id})...")
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

    extractions = result.extractions or []
    print(f"\n[3/4] Extraction complete. Total entities captured: {len(extractions)}")

    # Grounding & Trustworthiness Audit
    grounded_count = 0
    ungrounded_count = 0
    tranches_found = set()

    for item in extractions:
        tranche = item.attributes.get("tranche", "unassigned") if item.attributes else "unassigned"
        tranches_found.add(tranche)
        if item.char_interval is not None:
            grounded_count += 1
        else:
            ungrounded_count += 1

    print(f"      Grounded (exact source offsets): {grounded_count}")
    print(f"      Ungrounded (flagged / hallucinated): {ungrounded_count}")
    print(f"      Tranches identified: {sorted(list(tranches_found))}")

    # Save structured JSONL
    base_name = filing_path.stem
    jsonl_filename = f"{base_name}_extractions.jsonl"
    lx.io.save_annotated_documents(
        annotated_documents=[result],
        output_dir=OUTPUT_DIR,
        output_name=jsonl_filename,
        show_progress=False,
    )
    print(f"[4/4] Saved structured data: {OUTPUT_DIR / jsonl_filename}")

    # Generate interactive highlighted HTML visualization
    html_content = lx.visualize(result)
    html_filename = f"{base_name}_visualization.html"
    html_path = OUTPUT_DIR / html_filename
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(str(html_content))
    print(f"      Saved HTML visualization: {html_path}")

    return result

if __name__ == "__main__":
    import sys
    test_file = sys.argv[1] if len(sys.argv) > 1 else "data/raw_filings/AAPL_FWP_TermSheet_2025-05-06.txt"
    extract_terms(test_file)
