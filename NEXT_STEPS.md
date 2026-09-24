# Bond Term Sheet Extractor — Session Handoff & Next Steps

## 1. Current State Summary
- **Phase 0 (Setup)**: Complete.
  - Python 3.12 virtual environment (`.venv`) configured.
  - Dependencies installed: `langextract`, `edgartools`, `pandas`, `openpyxl`, `streamlit`, `python-dotenv`.
  - Git initialized, `.gitignore` protects secrets, `.env` configured with Google AI Studio Gemini API key.
- **Phase 1 (Test Filings via edgartools)**: Complete.
  - `fetch.py` pulled 5 benchmark investment-grade deals into `data/raw_filings/`:
    - `AAPL_FWP_TermSheet_2025-05-06.txt` (4 tranches: 2028, 2030, 2032, 2035 notes)
    - `MSFT_FWP_TermSheet_2017-01-31.txt`
    - `AMZN_FWP_TermSheet_2026-09-09.txt`
    - `GOOGL_FWP_TermSheet_2026-08-07.txt`
    - `AAPL_424B2_Prospectus_2025-05-06.txt` (100+ page prospectus supplement)
- **Phase 2 (LangExtract Engine)**: Configured and ready to run.
  - `fields.py`: Prompt instructions and few-shot examples for 19 DCM bond fields, including multi-tranche tagging with `attributes={"tranche": "<tranche>"}` and deal-level tagging `{"tranche": "all"}`.
  - `extract.py`: Orchestrates LangExtract, audits source character grounding (`char_interval is not None`), saves JSONL, and produces highlighted HTML visualizations (`output/<name>_visualization.html`).
  - **Rate Limit & Chunking Note**: Gemini free tier allows 5 requests/min. LangExtract was tuned with `max_char_buffer=40000` and `max_workers=1` to pack the entire 17KB term sheet into a single API call, avoiding multi-chunk rate limits.

---

## 2. Immediate Next Steps (Starting Next Session)

### Step 2.1: Run Extraction on AAPL FWP
Run the extraction once Google's temporary 503 load spike on free-tier flash models clears:
```bash
cd ~/bond-term-sheet-extractor
source .venv/bin/activate
python3 extract.py data/raw_filings/AAPL_FWP_TermSheet_2025-05-06.txt
```
- Verify `output/AAPL_FWP_TermSheet_2025-05-06_extractions.jsonl` is created.
- Open `output/AAPL_FWP_TermSheet_2025-05-06_visualization.html` in browser to visually verify that all 4 tranches are properly highlighted and grounded.

### Step 2.2: Phase 3 — Structuring into Comps Table (`structure.py`)
Build `structure.py` to:
1. Parse the JSONL extractions.
2. Group extractions by tranche attribute (`2028 Notes`, `2030 Notes`, etc.).
3. Distribute deal-level terms (`issuer`, `trade_date`, `settlement_date`, `ratings`) across all tranche rows.
4. Clean and normalize data:
   - Coupons to float percentages (`4.000%` → `4.00`)
   - Principal amounts to millions (`$1,500,000,000` → `$1,500M`)
   - Spreads to integer basis points (`25 basis points` / `+25 bps` → `25`)
   - Dates to ISO format (`YYYY-MM-DD`)
5. Keep source text offsets attached to each cell for full auditability.

### Step 2.3: Phase 4 — Sanity Validator (`validate.py`)
Implement finance-grade validation rules:
- Flag if `maturity_date <= trade_date` or `settlement_date < trade_date`.
- Flag coupon outside plausible range (0% – 15%).
- Flag issue price outside par bounds (90.00 – 110.00).
- Flag spread outside plausible range (0 – 1000 bps).
- Flag ungrounded extractions (`char_interval is None`) as "Not found / Flagged".

### Step 2.4: Phase 5 — Accuracy Evaluation (`evaluate.py`)
- Create `data/answer_key.csv` by hand-checking the 4 tranches in the AAPL FWP.
- Run `evaluate.py` to compare extraction output vs answer key and compute field-level accuracy percentage for the scholarship writeup.

### Step 2.5: Phase 6 & 7 — Streamlit Application & Cloud Deployment (`app.py`)
- Build clean DCM comps table interface.
- Allow expanding any row/cell to inspect the exact source quote and character offsets.
- One-click Excel download (`.xlsx`) via pandas/openpyxl.
- Deploy to Streamlit Community Cloud and verify incognito URL access.

---

## 3. Reference Files
- Project Root: `/home/dini/bond-term-sheet-extractor`
- WikiBrain Vault: `/mnt/c/Users/aidin/claude.brain/Claude.Brain/wiki/Bond Term Sheet Extractor (AINA Scholarship).md`
- Raw Filings: `/home/dini/bond-term-sheet-extractor/data/raw_filings/`
- Extraction Config: `/home/dini/bond-term-sheet-extractor/fields.py`
- Extractor Script: `/home/dini/bond-term-sheet-extractor/extract.py`
