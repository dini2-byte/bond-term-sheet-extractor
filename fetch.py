"""
fetch.py: Pulls sample bond term sheets (FWP) and prospectus supplements (424B2/424B5)
from SEC EDGAR using edgartools and saves raw text for extraction testing.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from edgar import set_identity, Company

load_dotenv()

# SEC EDGAR identification header
SEC_IDENTITY = os.getenv("EDGAR_IDENTITY", "Baruch Student bstudent@baruch.cuny.edu")
set_identity(SEC_IDENTITY)

OUTPUT_DIR = Path("data/raw_filings")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Selection of benchmark investment-grade corporate deals
DEALS_TO_FETCH = [
    {"ticker": "AAPL", "form": "FWP", "label": "AAPL_FWP_TermSheet"},
    {"ticker": "MSFT", "form": "FWP", "label": "MSFT_FWP_TermSheet"},
    {"ticker": "AMZN", "form": "FWP", "label": "AMZN_FWP_TermSheet"},
    {"ticker": "GOOGL", "form": "FWP", "label": "GOOGL_FWP_TermSheet"},
    {"ticker": "AAPL", "form": "424B2", "label": "AAPL_424B2_Prospectus"},
]

def fetch_filings():
    print(f"Connecting to SEC EDGAR using identity: {SEC_IDENTITY}")
    manifest = []
    
    for deal in DEALS_TO_FETCH:
        ticker = deal["ticker"]
        form = deal["form"]
        label = deal["label"]
        print(f"\nSearching {ticker} for form {form}...")
        
        try:
            company = Company(ticker)
            filings = company.get_filings(form=form)
            if not filings or len(filings) == 0:
                print(f"  [!] No filings found for {ticker} form {form}")
                continue
            
            latest = filings[0]
            filing_date = str(latest.filing_date)
            text_content = latest.text()
            
            filename = f"{label}_{filing_date}.txt"
            filepath = OUTPUT_DIR / filename
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(text_content)
                
            char_count = len(text_content)
            manifest.append({
                "ticker": ticker,
                "form": form,
                "date": filing_date,
                "chars": char_count,
                "file": filename
            })
            print(f"  [✓] Saved: {filename} ({char_count:,} characters)")
            
        except Exception as e:
            print(f"  [x] Error fetching {ticker} {form}: {e}")

    print("\n--- Download Manifest ---")
    print(f"{'Ticker':<8} {'Form':<8} {'Date':<12} {'Chars':<10} {'Saved File'}")
    print("-" * 65)
    for item in manifest:
        print(f"{item['ticker']:<8} {item['form']:<8} {item['date']:<12} {item['chars']:<10} {item['file']}")

if __name__ == "__main__":
    fetch_filings()
