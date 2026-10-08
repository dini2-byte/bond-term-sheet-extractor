"""
fetch.py: Pulls sample bond term sheets (FWP) and prospectus supplements (424B2/424B5)
from SEC EDGAR using edgartools and saves raw text for extraction testing.
"""

import os
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from edgar import set_identity, get_by_accession_number

load_dotenv()

# SEC EDGAR identification header
SEC_IDENTITY = os.getenv("EDGAR_IDENTITY", "Baruch Student bstudent@baruch.cuny.edu")
set_identity(SEC_IDENTITY)

OUTPUT_DIR = Path("data/raw_filings")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Pinned benchmark investment-grade corporate deals
DEALS_TO_FETCH = [
    {
        "ticker": "AAPL",
        "form": "FWP",
        "label": "AAPL_FWP_TermSheet",
        "accession": "0001140361-25-017410",
    },
    {
        "ticker": "MSFT",
        "form": "FWP",
        "label": "MSFT_FWP_TermSheet",
        "accession": "0001193125-17-024075",
    },
    {
        "ticker": "ORCL",
        "form": "FWP",
        "label": "ORCL_FWP_TermSheet",
        "accession": "0001193125-25-215807",
    },
    {
        "ticker": "GOOGL",
        "form": "FWP",
        "label": "GOOGL_FWP_TermSheet",
        "accession": "0001193125-26-338750",
    },
]

def fetch_filings(output_dir: Path = OUTPUT_DIR) -> list[dict[str, Any]]:
    print(f"Connecting to SEC EDGAR using identity: {SEC_IDENTITY}")
    manifest = []
    output_dir.mkdir(parents=True, exist_ok=True)

    for deal in DEALS_TO_FETCH:
        ticker = deal["ticker"]
        form = deal["form"]
        label = deal["label"]
        accession = deal["accession"]
        print(f"\nFetching {label} ({ticker} accession {accession})...")

        try:
            filing = get_by_accession_number(accession)
            if not filing:
                print(f"  [!] Filing not found for accession {accession}")
                continue

            filing_date = str(filing.filing_date)
            text_content = filing.text()

            filename = f"{label}_{filing_date}.txt"
            filepath = output_dir / filename

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(text_content)

            char_count = len(text_content)
            manifest.append({
                "ticker": ticker,
                "form": form,
                "accession": accession,
                "date": filing_date,
                "chars": char_count,
                "file": filename,
            })
            print(f"  [✓] Saved: {filename} ({char_count:,} characters)")

        except Exception as e:
            print(f"  [x] Error fetching {ticker} {accession}: {e}")

    print("\n--- Download Manifest ---")
    print(f"{'Ticker':<8} {'Form':<8} {'Accession':<25} {'Date':<12} {'Chars':<10} {'Saved File'}")
    print("-" * 80)
    for item in manifest:
        print(f"{item['ticker']:<8} {item['form']:<8} {item['accession']:<25} {item['date']:<12} {item['chars']:<10} {item['file']}")

    return manifest

if __name__ == "__main__":
    fetch_filings()
