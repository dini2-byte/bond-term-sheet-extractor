# Slice 6: Make the page easy to follow

**Implementer**: agy
**Reviewer**: Claude Code
**Branch**: `slice-06-friendly`, cut from `master` at `92026ea`
**Due**: 2026-10-14

Read `CONTEXT.md` first. Its terms stay in code, tests and the README. The visible page text uses the plain words in this plan instead.

## Goal

AINA reviewers are accounting and finance people, not bond desk analysts. Slice 5 made the page look clean, but a first-time visitor still does not know what to do. The page opens on internal terms ("grounded", "not-in-source", "Flagged"), the source view sits below the fold and every AAPL row says "Flagged" with no reason.

After this slice the page walks a visitor through three steps: pick a deal, read the table, click any number to see the sentence it came from. Every term is explained where it appears.

## Rules

- Write each test before its code change. Show it failing, then passing.
- Do not commit. Claude commits after review.
- Do not touch: `fields.py`, `extract.py`, `evaluate.py`, `structure.py`, `validate.py`, `fetch.py`, `data/`, `output/`, `CONTEXT.md`, `docs/`, `README.md`, `.streamlit/config.toml`.
- No Gemini API calls. No extraction runs. No network calls in tests.
- All 146 existing tests must pass, except tests of code this slice deletes on purpose. List every deleted or changed test and why.
- Keep the security behavior: password gate with `check_password`, upload size check, uploads in their own temp dir with `log_attempt=False`, the full filing loaded through `visualization_src`, and every piece of extracted or filing text escaped before it reaches HTML.
- No CSS `font-family` rules. The theme config sets the fonts.

## Plain words for the page

Use these in visible text. Code names stay as they are.

| Internal term | Page text |
|---|---|
| grounded | found word for word |
| not grounded (extracted, no exact match) | found, but the match is not exact |
| not extracted / Not found | not in the filing |
| not-in-source | made up (not in the filing) |
| FLAGGED / PASSED | Check: reason / OK |
| field accuracy | values right |

Never show these on the page: "grounded", "not-in-source", "FLAGGED", "PASSED", "engine", "hallucination", "ground truth", "proprietary", "AI-native", "trustworthiness", "gate". No emoji. No em dashes or en dashes.

## Task A: Helpers in `ui.py`

All pure, no Streamlit imports.

1. `TABLE_COLUMNS`: an ordered list of `(label, source_column, field_class, help_text)` for the table, in this order:
   - Tranche, `Tranche`, None, "One bond in the deal. A deal often sells several bonds with different maturities."
   - Size ($M), `Principal ($M)`, `principal_amount`, "Amount of this bond sold, in millions of dollars."
   - Coupon, `Coupon (%)`, `coupon`, "Yearly interest rate the issuer pays."
   - Price, `Issue Price`, `issue_price`, "Price paid per 100 of face value."
   - Yield, `Yield (%)`, `yield_to_maturity`, "Return to an investor who buys at the issue price and holds to maturity."
   - Spread (bps), `Spread (bps)`, `spread_bps`, "Extra yield over the matching US Treasury, in basis points (1 bp = 0.01%)."
   - Treasury, `Benchmark Treasury`, `benchmark_treasury`, "The US Treasury the spread is measured against."
   - Maturity, `Maturity Date`, `maturity_date`, "Date the bond is repaid."
   - Par call, `Par Call Date`, `par_call_date`, "Date after which the issuer can repay early at 100."
   - CUSIP, `CUSIP`, `cusip`, "The bond's 9-character ID."
   - Check, (built by item 3), None, "OK, or the first thing worth checking in this row."
2. `plain_status(meta) -> str`: `"Found word for word"` when `meta["grounded"] is True`; `"Found, but the match is not exact"` when a value was extracted but is not grounded; `"Not in the filing"` when nothing was extracted (missing meta, `raw` is None or "Not found").
3. `plain_check(status, issues) -> str`: `"OK"` for `PASSED`. For `FLAGGED`, `"Check: "` plus the first reason in plain words, plus `" (+N more)"` when there are more. Map the codes from `validate.py`: `UNGROUNDED` and `WEAK_GROUNDING` give "<field label> not word for word" (use the `TABLE_COLUMNS` label, or the `SCORED_FIELDS` column name for fields not in the table, lower-cased), `SUSPICIOUS_COUPON` "coupon looks unusual", `MISSING_COUPON` "coupon missing", `PRICE_DEVIATION` "price far from 100", `SPREAD_ANOMALY` "spread looks unusual", `DATE_SEQUENCE_ERROR` "dates out of order". Unknown codes give "see validation details".
4. `table_frame(validated_df) -> pd.DataFrame`: the table with `TABLE_COLUMNS` labels in order, the Check column from `plain_check`, and a fresh 0..n-1 index.
5. `not_exact_mask(validated_df, audit_records) -> pd.DataFrame`: same shape and labels as `table_frame`, True where a value was extracted but is not grounded.
6. `cell_source(audit_records, row, label, validated_df, doc_text) -> dict | None`: for a clicked cell, returns `{"field": label, "tranche": <tranche name>, "value": <displayed value>, "status": plain_status(...), "quote_html": source_quote(...) or ""}`. Returns None for the Tranche and Check columns.
7. Delete `comps_table_html` and `field_rows` if nothing uses them after Task B, together with their tests.

## Task B: Rewrite the `app.py` layout

Top to bottom:

1. **Title and one sentence.** "Bond Term Sheet Extractor", then: "Turn a bond term sheet into a comps table, with every number traced back to the SEC filing."
2. **How to use it.** A short numbered list: "1. Pick a deal. 2. Read the table. 3. Click any number to see the sentence it came from."
3. **Step 1: Pick a deal.** Subheader "1. Pick a deal". `st.selectbox` labelled "Sample deals", AAPL first by default. Under it, the deal line from slice 5 (issuer, size, bond count, pricing date). Say "bonds" in the deal line instead of "tranches".
4. **Step 2: Read the table.** Subheader "2. Read the table".
   - `st.dataframe(styled, hide_index=True, on_select="rerun", selection_mode="single-cell", key="comps", column_config=...)`. `styled` is `table_frame(...)` with a pandas `Styler` that gives cells in `not_exact_mask` the background `#FFF1B8`. Each column gets its `help_text` from `TABLE_COLUMNS` and the same number formats as today.
   - Set `selection_default` so the Coupon cell of the first row is selected on first load. Check the 1.64 schema for single-cell selections and say what it was.
   - One line under the table: a small `#FFF1B8` swatch, then "Found, but the match is not exact. Click it to see the filing text."
   - The "Download .xlsx" button, unchanged.
5. **Step 3: Check any number.** Subheader "3. Check any number". Read the selected cell from `st.session_state["comps"]`. If it maps to a value, show a short card: field and bond name, the value in large text, the status from `plain_status` (green `#1E6B3A` for found word for word, amber `#8A5A00` for not exact, muted for not in the filing) and the quote from `quote_html` under the heading "From the filing". If nothing is selected or the Tranche or Check column is selected, show: "Click any number in the table to see the sentence it came from."
6. **How well does it work?** Subheader "How well does it work?". Three plain sentences built from `parse_accuracy_report` numbers, skipping any sentence whose numbers cannot be parsed (no literal fallbacks):
   - "On 4 sample deals with hand-checked answers, it got 344 of 350 values right (98.3%)."
   - "55.5% of values were found word for word in the filing. The rest are marked in the table so you can check them."
   - "None were made up: 0 of 335 values were missing from the filing."
   Then the muted scoring-change line from slice 5, and one muted line for this deal: "This deal: 92.9% found word for word (52 of 56 values, all 4 bonds)."
7. **Collapsed sections**, unchanged in behavior: "Full filing with highlights", "Validation details" (rename of "Validation checks"; it may show the raw issue codes) and "Try your own term sheet" (password upload).
8. **Footer**, unchanged.

## Task C: Tests

1. `tests/test_ui.py`: tests for every new helper. Include: `plain_check` on a `FLAGGED` row with two `WEAK_GROUNDING` issues gives "Check: <label> not word for word (+1 more)"; `cell_source` on the Tranche column gives None; `cell_source` on the AAPL first-row Coupon cell gives status "Found word for word" and a quote with `<mark>4.000%</mark>`; `not_exact_mask` has the same shape as `table_frame`.
2. `tests/test_app_ui.py`: the app runs with no exceptions; there is one dataframe with `selection_mode` single-cell; on first load the step 3 card shows `4.000%`; no markdown, HTML or widget label on the page contains a word from the "never show" list (case-insensitive) or an emoji; the three step subheaders appear in order.

## Deliverable

Leave changes uncommitted on `slice-06-friendly`. Report:
1. `git status --short` and `git diff --stat`
2. Failing then passing output for each new test
3. Full `python3 -m pytest -q`
4. Output of `streamlit run app.py --server.headless true` for 15 seconds, with no errors or warnings
5. The `selection_default` schema you used and where you found it
6. Every test you deleted or changed, and why
7. Anything you were unsure about

## After agy: Claude checks

Claude clicks through all four deals in a browser at 1440px and 390px wide, checks that clicking a tinted cell shows the right sentence and reads every visible string against the plain-words table.
