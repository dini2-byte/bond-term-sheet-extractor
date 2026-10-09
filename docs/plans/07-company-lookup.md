# Slice 7: Try another company

**Implementer**: agy
**Reviewer**: Claude Code
**Branch**: `slice-07-lookup`, cut from `master` after slice 6 merges
**Due**: 2026-10-19

Read `CONTEXT.md` and `docs/plans/06-friendly-page.md` first. The plain-words table and the "never show" list from slice 6 apply to every new string.

## Goal

Visitors can only look at four sample deals. This slice lets a visitor type a ticker, pick one of that company's recent bond term sheets from SEC EDGAR and run the extraction live, with a daily cap so a public page cannot use up the owner's Gemini quota.

Claude checked EDGAR on 2026-10-08 with edgartools: AAPL, KO, T and CAT each return several bond term sheets among their latest 15 FWP filings in 3 to 4 seconds. JPM has 23,181 FWP filings and none of the latest 15 are plain bond term sheets, because banks file many structured-note FWPs. The page must handle that case with a clear message.

## Rules

- Write each test before its code change. Show it failing, then passing.
- Do not commit. Claude commits after review.
- Do not touch: `fields.py`, `extract.py`, `evaluate.py`, `structure.py`, `validate.py`, `fetch.py`, `data/`, `output/`, `CONTEXT.md`, `docs/`, `README.md`.
- No Gemini API calls. No extraction runs. Tests make no network calls: mock edgartools and `extract_terms`.
- All existing tests must still pass.
- Live runs from this path always use `log_attempt=False` and their own temp dir, like uploads.
- Every piece of filing text and every value from EDGAR is escaped before it reaches HTML.

## Task A: `lookup.py`

New module, no Streamlit imports.

1. `TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")`. `normalize_ticker(raw) -> str` strips and upper-cases the input and raises `ValueError("Enter a stock ticker, for example KO.")` when it does not match.
2. `is_bond_term_sheet(text) -> bool`: True when the first 4,000 characters match `(pricing|final)\s+term\s+sheet` (case-insensitive), the text contains `CUSIP` and it matches `Notes due \d{4}`.
3. `find_term_sheets(ticker, scan=25, max_chars=60_000, company_cls=edgar.Company) -> list[dict]`: looks at the latest `scan` FWP filings for the ticker and keeps those where `is_bond_term_sheet` is True and the text is at most `max_chars` long. Each result has `accession`, `filing_date` (ISO string), `chars`, `bond_count` (number of distinct 9-character CUSIPs in the text) and `text`. Newest first. An unknown ticker raises `LookupError("No SEC filer found for <TICKER>.")`. `company_cls` is a parameter so tests can pass a fake.
4. `get_edgar_identity(secrets) -> str | None`: `EDGAR_IDENTITY` from Streamlit secrets, then the environment. Returns None when neither is set. Never fall back to the placeholder in `fetch.py`.
5. `RunBudget(daily_limit=20, session_limit=3, today=date.today)`: tracks runs per calendar day across the whole site. `remaining() -> int`, `can_run(session_runs) -> tuple[bool, str | None]` (False with "Today's 20 free runs are used up. Try again tomorrow." or "You've used your 3 runs for this visit.") and `record_run()`. The count resets when `today()` changes. `today` is injectable for tests.

## Task B: App changes

1. In step 1, above the sample deal picker, add `st.segmented_control` with two options: "Sample deals" and "Another company". "Sample deals" shows the slice 6 picker.
2. "Another company":
   - If `get_edgar_identity` returns None, show "Company lookup is not set up on this deployment." and nothing else.
   - Otherwise a text input "Stock ticker" (placeholder "KO") and a "Find term sheets" button. Wrap `find_term_sheets` in `st.cache_data(ttl=86400, show_spinner=False)` keyed on the ticker, and show a spinner "Searching SEC EDGAR..." while it runs.
   - Results: `st.radio` labelled "Recent bond term sheets", one option per result, label like "Filed 2026-08-10 · 3 bonds". Under it a link "View on SEC EDGAR" to the filing index page for the selected accession.
   - No results: "No bond term sheets in <TICKER>'s latest 25 SEC filings. Banks and brokers file many structured-note filings, which this tool skips." plus a link to the company's EDGAR FWP list.
   - Invalid ticker, unknown ticker or an EDGAR error: show the plain message from `ValueError` or `LookupError`, or "SEC EDGAR did not respond. Try again in a minute." for anything else. Log the exception server-side; never show a traceback.
   - An "Extract" button with the line "<N> of 20 free runs left today" next to it. Keep one `RunBudget` for the whole app with `st.cache_resource`, and the per-visitor count in `st.session_state`. Check `can_run` before running and show its message when False.
   - On Extract: write the selected `text` to a new temp dir, call `extract_terms(path, model_id="gemini-3.5-flash-lite", log_attempt=False, output_dir=temp_dir)`, call `record_run()` only after a successful run, then show the result in the same steps 2 and 3 as a sample deal. The deal line reads "<TICKER> · term sheet filed <date> · live run". Show "Extracting with Gemini. This takes about 20 seconds." while it runs.
   - Gemini errors: "The extraction did not finish. Your run was not counted." and no `record_run()`.
3. The "How well does it work?" section stays about the sample deals. For a live run, add one muted line under step 2: "Live run: there is no hand-checked answer for this deal, so check values against the filing text."

## Task C: Tests

1. `tests/test_lookup.py`: `normalize_ticker` accepts " ko " and "BRK.B" and rejects "", "KO;rm" and "TOOLONGTICKER1"; `is_bond_term_sheet` on a short fake pricing term sheet and on a structured-note style text; `find_term_sheets` with a fake company class (filters, `max_chars`, newest first, `bond_count`, unknown ticker); `RunBudget` daily reset with an injected `today`, the daily cap and the session cap.
2. `tests/test_app_ui.py`: with `find_term_sheets` and `extract_terms` mocked, choosing "Another company", entering a ticker and pressing Extract shows the extracted deal; when `EDGAR_IDENTITY` is not set the lookup shows the not-set-up message; when the budget is used up the Extract button shows the cap message and `extract_terms` is not called.

## Deliverable

Leave changes uncommitted on `slice-07-lookup`. Report:
1. `git status --short` and `git diff --stat`
2. Failing then passing output for each new test
3. Full `python3 -m pytest -q`
4. Output of `streamlit run app.py --server.headless true` for 15 seconds, with no errors or warnings
5. Anything you were unsure about

## After agy: Aidin and Claude

Aidin adds `EDGAR_IDENTITY = "Aidin Marke <email>"` to the Streamlit secrets. SEC asks automated tools for a real name and contact email. With Aidin's OK, Claude runs one live lookup and one extraction on the deployed app (uses one Gemini call) and checks the JPM empty state.
