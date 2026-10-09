# Slice 5: Redesign the app UI

**Implementer**: agy
**Reviewer**: Claude Code
**Branch**: `slice-05-ui`, cut from `master` at `a3b6460`
**Due**: 2026-10-16

Read `CONTEXT.md` first and use its terms.

## Goal

The app is the first thing AINA reviewers see and it appears in the video. Today it reads as generated: an emoji on every header, made-up product names ("Trustworthiness Engine", "Source Grounding Gate: Active"), centered metric cards with uppercase labels and the core feature (each value linked to its source text) hidden in a tab.

The new page should read like a sell-side research note: a serif headline, one tight numeric table, thin rules, one accent color and footnotes. The source link becomes the main interaction: pick a tranche and see, for each field, the sentence in the filing it came from.

## Rules

- Write each test before its code change. Show it failing, then passing.
- Do not commit. Claude commits after review.
- Do not touch: `fields.py`, `extract.py`, `evaluate.py`, `structure.py`, `validate.py`, `fetch.py`, `data/`, `output/`, `CONTEXT.md`, `docs/`, `README.md`.
- No Gemini API calls. No extraction runs.
- All 112 existing tests must still pass. If an existing test checks UI text that this slice removes on purpose, update that test and list each change in your report.
- Keep the security behavior from slices 3 and 4: password gate with `check_password`, upload size check, uploads in their own temp dir with `log_attempt=False`, and the highlighted filing loaded through `visualization_src`.

## Task A: `ui.py`, pure render helpers

New module `ui.py`. No Streamlit imports in it, so every function is testable on its own.

1. `SCORED_FIELDS`: an ordered dict from comps table column to field class, the same 14 pairs as `field_class_map` in `evaluate.py` (`"Coupon (%)": "coupon"` and so on). Copy it; do not import from inside `evaluate_deal`.
2. `load_document_text(jsonl_path) -> str`: returns the `text` value from the first line of a fixture JSONL.
3. `scored_grounding(audit_records) -> dict`: grounded count, extracted count and percent, counting only the 14 scored field classes and only fields that were extracted (not "Not found"). Test first: for each of the four benchmark fixtures, the percent must equal the deal's "Grounded (%)" in `output/accuracy_benchmark_report.md` to one decimal place. AAPL must give 92.9. If any deal does not match, stop and report why instead of changing the rule.
4. `source_quote(doc_text, start, end, context=60) -> str`: returns HTML. Up to `context` characters before and after the span, whitespace collapsed, the span wrapped in `<mark>`, a leading or trailing ellipsis when text was cut. Every piece of filing text goes through `html.escape` before the `<mark>` tags are added.
5. `comps_table_html(df, audit_records) -> str`: an HTML `<table>` with these columns in this order: Tranche, Size ($M), Coupon, Price, Yield, Spread (bps), Benchmark, Maturity, Par call, CUSIP, Checks. No index column. Numbers right-aligned with the same formats the app uses today. A value that was extracted but is not grounded gets a superscript dagger (`<sup>†</sup>`). A missing value shows "n/a" in the muted color. Every cell value goes through `html.escape`. Wrap the table in a `<div class="table-wrap">` so it scrolls sideways on a phone.
6. `field_rows(audit_entry, doc_text) -> list[dict]`: one row per scored field for one tranche, in `SCORED_FIELDS` order, with keys `field`, `value`, `status` (one of `"exact"`, `"not exact"`, `"not found"`) and `quote_html` (from `source_quote`, or an empty string when not found).

Tests in `tests/test_ui.py`. Include:
- an extracted value of `</td><script>alert(1)</script>` comes out of `comps_table_html` and `source_quote` with no `<script>` substring;
- `source_quote` keeps non-ASCII text such as `"€ 1.5bn"`;
- the four-deal grounding match from item 3.

## Task B: Theme

1. In `.streamlit/config.toml`, keep the `[server]` section as it is. Replace `[theme]` with: `base = "light"`, white background, text `#1A1A1A`, secondary background `#F7F7F5`, primary (accent) `#1F3A5F`.
2. Fonts: headings in Source Serif 4, body in IBM Plex Sans. Check the Streamlit 1.64 docs for theme font options (`font`, `headingFont` and loading from a Google Fonts URL) and use config if it works. Use CSS only for what config cannot do. Say in your report which way you used.
3. Numbers in the comps table use `font-variant-numeric: tabular-nums`.
4. Put the CSS in one `st.html("<style>...</style>")` call at the top of `app.py`. Keep it short: page max width about 1180px, table rules (1px `#D9D9D9` lines, no zebra stripes, no rounded corners), `mark` background `#FFF1B8`, muted text `#5F6368`.

## Task C: Rewrite the `app.py` layout

`app.py` keeps only layout and Streamlit calls. No sidebar. Top to bottom:

1. **Header.** `st.set_page_config(page_title="Bond Term Sheet Extractor", layout="wide", initial_sidebar_state="collapsed")`, no `page_icon` emoji. Title "Bond Term Sheet Extractor". One line under it: "Pulls pricing terms for investment-grade bond deals out of SEC term sheets and builds a comps table. Every value links to the text it came from." The deal picker (`st.selectbox`, label "Deal") sits to the right of the title in a column.
2. **Deal line.** One line: issuer, total size, tranche count and trade date, for example "Apple Inc. · $4.5bn senior notes · 4 tranches · priced May 5, 2025". Build it from the comps table, not by hand.
3. **Benchmark line.** One line from `parse_accuracy_report`: field accuracy, grounded and not-in-source, then "4 deals". Under it, in muted small text, the scoring change: "First scored 88.0% (308/350). A CUSIP formatting fix after the run, with no new extraction, gave 98.3%." Take the numbers from the parsed report, not literals. Thin rule below.
4. **Comps table.** `st.html(comps_table_html(...))`. Above it on the right, the Excel download as a plain `st.download_button` labelled "Download .xlsx". Under the table, the footnote: "† Not grounded: the value was extracted but its text is not an exact match in the filing." Then one muted line with this deal's grounded figure from `scored_grounding`, for example "Grounded: 92.9% (52/56 extracted fields)".
5. **Where each value came from.** Heading "Where each value came from". `st.segmented_control` with one option per tranche, labelled by maturity year when the tranches have distinct years, otherwise by tranche name. Default to the first tranche. Below it, an HTML table from `field_rows`: Field, Value, Status, Source text. Status is plain text ("exact", "not exact", "not found"), with "not exact" in the accent color and "not found" muted.
6. **Collapsed sections**, each an `st.expander`, closed by default:
   - "Full filing with highlights": the existing `st.iframe(visualization_src(...), height=600, width="stretch")`.
   - "Validation checks": per tranche, the status, the issues, bookrunners, ratings and trade/settlement dates, as plain text.
   - "Try your own term sheet": the password field, then the uploader and an "Extract" button, with the same logic and messages as today. After a successful extraction, the page shows the uploaded deal in the same layout (deal line, table, sources) in place of the selected benchmark deal, with the deal line saying "Uploaded term sheet". If `APP_PASSWORD` is not set, the expander shows "Live extraction is disabled on this deployment" and nothing else.
7. **Footer.** Thin rule, then one muted line: "Code: github.com/dini2-byte/bond-term-sheet-extractor. Built on langextract and edgartools."

Copy rules for every string in the app:
- No emoji anywhere. No uppercase-transformed labels.
- Never use: "engine", "hallucination", "ground truth", "proprietary", "AI-native", "trustworthiness", "gate", "analyst-ready".
- Use the glossary words from `CONTEXT.md`: grounded, not-in-source, answer key, benchmark, field accuracy, tranche, deal, comps table.
- No em dashes or en dashes in UI text.

## Task D: App tests

In a new file `tests/test_app_ui.py`, using `streamlit.testing.v1.AppTest`:
1. The app runs with no exceptions and shows the AAPL deal by default.
2. The rendered comps table HTML contains `4.000%` and `4.200%` and no row index column.
3. Selecting the 2030 option in the segmented control shows a source row whose quote contains `4.200%` inside a `<mark>`.
4. No rendered markdown, HTML or widget label in the app contains a character in the emoji ranges `U+1F300` to `U+1FAFF` or `U+2600` to `U+27BF`, or any of the banned words above (case-insensitive).
5. There is no sidebar content.

## Deliverable

Leave changes uncommitted on `slice-05-ui`. Report:
1. `git status --short` and `git diff --stat`
2. Failing then passing output for each new test
3. Full `python3 -m pytest -q`
4. Output of `streamlit run app.py --server.headless true` for 15 seconds, with no errors or deprecation warnings
5. Which way you loaded fonts (config or CSS) and what the 1.64 docs said
6. Any existing test you changed, and why
7. Anything you were unsure about

## After agy: Claude checks

Claude runs the app and takes screenshots at 1440px and 390px wide, checks the source rows for all four deals and checks that the grounded figure for each deal matches the README table.
