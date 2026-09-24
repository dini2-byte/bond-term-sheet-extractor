# AI-Native Debt Capital Markets (DCM) Comps Table Engine
**AI Native Accounting (AINA) Foundation Scholarship Submission**  
**Applicant**: Aidin Marke  
**Repository**: `aidin/bond-term-sheet-extractor`  
**Word Count**: ~500 words  

---

### 1. Problem Statement
In Debt Capital Markets (DCM) investment banking, junior analysts spend countless hours manually extracting pricing and covenant data from SEC EDGAR filings—primarily Final Pricing Term Sheets (Form FWP) and 100+ page Prospectus Supplements (Form 424B2)—to build comparable pricing ("comps") tables. 

This process is slow, tedious, and prone to costly transcription errors. A misquoted coupon rate, inverted benchmark spread, or incorrect par call date entered into an Excel financial model can compromise a live client pitch or misprice secondary debt offerings. In underwriting and financial accounting, a confidently wrong number is far worse than no number. Existing generative AI tools frequently hallucinate values or produce unanchored numbers without audit trails, rendering them unusable for institutional finance desks.

### 2. Architecture & Technical Implementation
The **Bond Term Sheet Extractor** is built on a core principle: **Trustworthiness Over Ambition**. Every extracted metric must possess an unbroken cryptographic and spatial audit trail back to the primary document.

The pipeline comprises six modular stages:
1. **Filing Ingestion (`fetch.py`)**: Connects directly to the SEC EDGAR API via `dgunning/edgartools`, ensuring automated SEC user-agent compliance to retrieve primary machine-readable text filings.
2. **Grounded Extraction Engine (`extract.py` & `fields.py`)**: Utilizes `google/langextract` powered by Google Gemini. The engine defines a 19-field DCM debt schema with few-shot multi-tranche tagging. To prevent rate-limit bottlenecks on Gemini's API, the engine buffers documents into optimal single-request contexts (`max_char_buffer=40000`). Crucially, every extraction produces a verified character interval (`char_interval`).
3. **Comps Structuring & Normalization (`structure.py`)**: Recombines extracted entities into tabular tranche records, inherits deal-wide parameters (issuer, credit ratings, trade date, settlement date, lead left bookrunners), and standardizes financial units (coupons to float percentages, principal amounts to millions, benchmark spreads to integer basis points).
4. **Programmatic Sanity Gate (`validate.py`)**: Enforces non-negotiable financial rules before data export: economic bounds (coupon 0–15%, issue price 90–110, spread 0–1,000 bps), date sequencing (`Maturity Date > Trade Date`), and source grounding validation. Ungrounded values are immediately flagged.
5. **Analyst Interface (`app.py`)**: A streamlined Streamlit web dashboard allowing analysts to upload term sheets, inspect interactive color-highlighted source documents, audit exact character spans cell by cell, and download production-grade Excel workbooks (`.xlsx`).

### 3. Quantitative Evaluation & Benchmark Results
The system was evaluated against a benchmark 4-tranche investment-grade corporate debt issuance (`AAPL` FWP: 2028, 2030, 2032, and 2035 notes) using an automated evaluation framework (`evaluate.py`) matched against a hand-verified ground truth answer key:
- **Field-Level Accuracy**: **100.0%** (56 / 56 fields correctly extracted across all 4 tranches).
- **Source Grounding Fidelity**: **100.0%** (56 / 56 fields anchored to exact character offsets).
- **Hallucination Rate**: **0.0%** (zero fabricated entities).
- **Sanity Validation Pass Rate**: **100.0%** (all economic and chronological checks passed).

### 4. Scope Boundaries & Future Work
To maintain near-zero error tolerances, the MVP scope is intentionally bounded:
- **Scope**: Fixed-rate investment-grade corporate bonds from digital SEC filings.
- **Out of Scope**: Floating-rate debt (SOFR spreads), convertible securities, amortizing structures, and scanned physical PDFs requiring optical character recognition.
