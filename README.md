# Bond Term Sheet Extractor

> **AI-Native Debt Capital Markets (DCM) Comps Table Engine with Exact Source Grounding**  
> *Developed for the AI Native Accounting (AINA) Foundation Scholarship ($5,000)*

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B.svg)](https://streamlit.io/)
[![Evaluation Accuracy](https://img.shields.io/badge/Benchmark%20Accuracy-100%25-brightgreen.svg)]()

---

## 1. The Problem
In Debt Capital Markets (DCM) investment banking, junior analysts spend hours manually compiling "comps tables" (comparable pricing tables) by sifting through final pricing term sheets (Form FWP) and 100+ page prospectus supplements (Form 424B2 / 424B5). 

Manual copy-pasting across multi-tranche deals is slow and prone to errors. A misquoted coupon, inverted spread, or wrong par call date entered into an Excel model can compromise a live client pitch or secondary market pricing desk.

In financial underwriting: **a confidently wrong number is far worse than no number.**

---

## 2. What This Tool Does
The **Bond Term Sheet Extractor** automatically pulls SEC EDGAR debt filings, extracts all core pricing and structural terms across every bond tranche, and structures them into an analyst-ready comparison table downloadable to Excel.

### Core Non-Negotiable Principle: Trustworthiness
1. **Precise Source Grounding**: Every extracted number or date is linked to its exact character offsets in the source filing. The user can click any cell to view the exact text quote behind it.
2. **Strict Refusal ("Not Found")**: If a term is not present in the document, it is labeled `"Not found"`. The model never infers, extrapolates, or hallucinates.
3. **Automated Sanity Validation**: Built-in rules flag suspicious values before export:
   - Coupon within standard bounds (`0.00% – 15.00%`)
   - Issue price near par (`90.00 – 110.00`)
   - Spread plausible (`0 – 1,000 bps`)
   - Chronological consistency: `Maturity Date > Trade Date` and `Settlement Date >= Trade Date`
   - Ungrounded Extractions: Dropped or flagged immediately.

---

## 3. Open-Source Foundations & Attribution
This project stands on two open-source libraries:
1. [`google/langextract`](https://github.com/google/langextract) (Apache-2.0): Provides Gemini-powered structured extraction with character-level source grounding (`char_interval`), multi-pass extraction, and animated HTML document highlighting.
2. [`dgunning/edgartools`](https://github.com/dgunning/edgartools) (MIT): Connects directly to the SEC EDGAR API with required SEC user-agent compliance to retrieve FWP term sheets and 424B prospectuses.

### Original Work Built on Top
The proprietary layer developed specifically for this scholarship project:
- **DCM 19-Field Taxonomy & Prompting Engine** (`fields.py`): Defined specialized DCM debt fields and few-shot examples with multi-tranche tagging (`attributes={'tranche': '...'}`).
- **Comps Table Structuring & Normalization** (`structure.py`): Groups extractions into tranche rows, distributes deal-level attributes (issuer, ratings, trade date, bookrunners), normalizes data into standard finance units ($M principal, float coupons, integer bps), and generates clean `.xlsx` spreadsheets.
- **Finance Sanity Validator** (`validate.py`): Programmatic audit of economic bounds, date sequencing, and source grounding.
- **Empirical Accuracy Framework** (`evaluate.py`): Hand-verified answer key comparing extractions against ground truth.
- **Analyst Web Application** (`app.py`): Streamlit dashboard with interactive source drill-down, live Excel export, and embedded highlighted document view.

---

## 4. Evaluation Benchmark Results

Tested against the benchmark 4-tranche Apple Inc. corporate bond deal (`AAPL` FWP, May 2025: 2028, 2030, 2032, and 2035 notes):

| Metric | Result | Target Benchmark |
|---|---|---|
| **Field Accuracy Rate** | **100.0%** (56 / 56 fields) | > 95% |
| **Source Grounding Fidelity** | **100.0%** (56 / 56 grounded) | 100% |
| **Hallucination / False Positive Rate** | **0.0%** | 0.0% |
| **Sanity Validation Pass Rate** | **100.0%** (4 / 4 tranches passed) | 100% |

### Detailed Field Breakdown
- **Deal-Level Terms**: Issuer (100%), Ratings (100%), Trade Date (100%), Settlement Date (100%)
- **Tranche Pricing Terms**: Principal Amount (100%), Coupon (100%), Issue Price (100%), Yield to Maturity (100%), Benchmark Treasury (100%), Spread (100%)
- **Structure & Covenants**: Maturity Date (100%), Day Count (100%), Par Call Date (100%), CUSIP (100%)

---

## 5. Quickstart & Local Installation

### Prerequisites
- Python 3.11+
- Google AI Studio Gemini API key (Free tier supported)

### Setup
```bash
# Clone the repository
git clone https://github.com/aidin/bond-term-sheet-extractor.git
cd bond-term-sheet-extractor

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and paste your GEMINI_API_KEY
```

### Running the System
```bash
# 1. Download test filings from SEC EDGAR
python3 fetch.py

# 2. Run extraction and grounding on a term sheet
python3 extract.py data/raw_filings/AAPL_FWP_TermSheet_2025-05-06.txt

# 3. Structure into comps table and Excel
python3 structure.py

# 4. Run finance validation check
python3 validate.py

# 5. Run accuracy benchmark scorecard
python3 evaluate.py

# 6. Launch the Streamlit Web Application
streamlit run app.py
```
Open `http://localhost:8501` in your browser.

---

## 6. Known Limitations & Scope Boundaries
To maintain high reliability, the system operates within defined scope boundaries:
1. **Fixed-Rate Corporate Debt Only**: Currently optimized for benchmark fixed-rate senior notes. Floating rate notes (SOFR + spread), convertible bonds, amortizing debt, and asset-backed securities (ABS) are currently out of scope.
2. **Digital SEC Filings Only**: Processes machine-readable text filings (EDGAR HTML/TXT). Scanned physical PDF term sheets require an upstream OCR pipeline.
3. **Syndicate Covenants**: Detailed indenture covenants (change-of-control puts, negative pledge carveouts) are summarized by optional redemption features; full covenant analysis requires legal indenture parsing.
