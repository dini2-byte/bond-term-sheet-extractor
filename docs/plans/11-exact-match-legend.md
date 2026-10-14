# Slice 11: amber only when the match is really not exact

**Implementer:** agy (headless, `gemini-3.8-flash-high`)
**Reviewer:** Claude
**Branch:** `slice-11-exact-match`, from `master` at `ab92cad`

## Problem

Under the comps table the page always shows the line "Match not exact. Click to check.", even when every cell in the table is word for word. Visitors read it as "these numbers are wrong".

The amber cells themselves are also mostly wrong. On the GOOGL fixture 68 cells are amber and on MSFT 47. In every one of those 115 cells the value matches the filing text word for word at the cited spot. They are amber only because langextract reports `alignment_status == "match_fuzzy"`. That status describes how langextract found the span, not whether the text matches.

`structure.assess_grounding` already checks the text. It returns `grounding_quality == "fuzzy"` only after confirming that `doc_text[start:end].strip() == extraction_text.strip()`. A text mismatch returns `"span_mismatch"` before that check is reached. So `"fuzzy"` always means the cited span equals the value exactly.

## Goal

1. A cell counts as word for word when `grounded is True` or `grounding_quality == "fuzzy"`.
2. The legend under the table appears only when at least one cell in the table is amber, with clearer wording.
3. The Check column stops reporting "X not exact" for fuzzy-only issues.

## Global Constraints

- Display layer only. Do NOT change `structure.py`, `validate.py`, `evaluate.py`, `extract.py`, the fixtures or `output/`. The benchmark stays strict and its numbers do not move.
- Make no Gemini calls. Never touch real R2: do not read R2 values from `.env` and do not run `seed_cache.py`.
- Write tests first. Run `python -m pytest -q` and show it passing before each commit.
- Page text rules from `tests/test_app_ui.py` still apply: no em dashes or en dashes, no emoji, none of the never-show words.
- Commit subjects: Conventional Commits prefix, imperative mood, 50 characters or fewer, no trailing period. No Oxford commas. No AI attribution of any kind: no `Co-Authored-By` trailers and no "Generated with" lines.
- Do not push or merge.

## Task 1: one rule for "word for word" in `ui.py`

**Files:** `ui.py`, `tests/test_ui.py`

Add this to `ui.py` above `plain_status`:

```python
def is_word_for_word(meta: dict[str, Any] | None) -> bool:
    """
    True when the cited span in the filing equals the extracted value.
    'fuzzy' grounding means langextract located the span loosely, but
    structure.assess_grounding has already checked the span text matches.
    """
    if not meta or not isinstance(meta, dict):
        return False
    return meta.get("grounded") is True or meta.get("grounding_quality") == "fuzzy"
```

Use it in two places:
- `plain_status`: replace `if meta.get("grounded") is True:` with `if is_word_for_word(meta):`.
- `not_exact_mask`: replace `if meta.get("grounded") is not True:` with `if not is_word_for_word(meta):`. Update the docstring to say "not word for word" in place of "not grounded".

In `plain_check`, drop fuzzy-only grounding issues before choosing the first issue. After `issue_list` is built, add:

```python
    issue_list = [i for i in issue_list if not FUZZY_ISSUE.match(i)]
    if not issue_list:
        return "OK"
```

with a module constant `FUZZY_ISSUE = re.compile(r"^WEAK_GROUNDING:\s*\S+\s*\(fuzzy\b")`. Keep the existing "See validation details" return for the case where the list was already empty before filtering.

Tests in `tests/test_ui.py`. Add these and make them fail before the code change:
- `is_word_for_word` returns True for `{"grounded": True}` and for `{"grounded": False, "grounding_quality": "fuzzy"}`. It returns False for `"span_mismatch"`, `"partial"`, `"none"`, `{}` and `None`.
- `plain_status({"grounded": False, "grounding_quality": "fuzzy", "raw": "4.000%"}) == "Found word for word"`.
- `plain_status({"grounded": False, "grounding_quality": "span_mismatch", "raw": "4.000%"}) == "Found, but the match is not exact"`.
- `plain_check("FLAGGED", ["WEAK_GROUNDING: coupon (fuzzy, span '4.000%' vs '4.000%')"]) == "OK"`.
- `plain_check("FLAGGED", ["WEAK_GROUNDING: coupon (fuzzy, span 'a' vs 'a')", "WEAK_GROUNDING: maturity_date (span_mismatch, span '2028' vs 'May 12, 2028')"]) == "Maturity not exact"`. If the existing field-label map gives a different label for `maturity_date`, assert that label instead and say so in the report.
- For each of the 4 fixtures in `data/fixtures/*_extractions.jsonl`: `not_exact_mask(vdf, audit_records).values.any()` is False. This is the regression test. All 115 amber cells in GOOGL and MSFT match word for word.

Two existing tests encode the old behavior: `test_plain_check_flagged_with_multiple_issues` uses `(fuzzy, ...)` issues and `test_plain_status` asserts `{"grounded": False, ...}` maps to "not exact". Switch their issue strings from `fuzzy` to `span_mismatch` and give the `plain_status` case `"grounding_quality": "span_mismatch"`. Keep the expected outputs. List both edits in the report.

Commit: `fix: count fuzzy spans as word for word`

## Task 2: show the legend only when a cell is amber

**Files:** `views/results.py`, `views/about.py`, `tests/test_results.py` (create it if it does not exist; otherwise add to it), `tests/test_app_ui.py`

In `views/results.py`:
- Change `LEGEND_TEXT` to `"Amber cells do not match the filing text word for word. Click one to compare."`
- Add `def needs_legend(mask: pd.DataFrame) -> bool: return bool(mask.values.any())`.
- `_render_table` currently computes `mask` internally. Change its return type to `tuple[tuple[int, str] | None, bool]`, returning `(selection, needs_legend(mask))`. Update the one caller in `render_results`.
- In `render_results`, call `st.html(...)` for the legend only when that bool is True.

In `views/about.py`, replace the fourth `HOW_IT_WORKS` sentence with:
`"An amber cell means the value does not match the filing text word for word. Click it to compare."`

Tests:
- `needs_legend` is False for an all-False frame and True when one cell is True.
- In `tests/test_app_ui.py::test_saved_filing_opens_free`, add `assert LEGEND_TEXT not in text`. Import `LEGEND_TEXT` from `views.results`. AAPL has no amber cells.
- Add `test_legend_shows_when_a_cell_is_not_exact` to `tests/test_app_ui.py`. Copy the AAPL fixture JSONL into a temp file and change one extraction so its text no longer matches the filing. Use the `search` helper with a fake `extract_terms` that writes this edited JSONL, and pick the unsaved `NEW_SHEET`. Click "Extract · uses 1 run" and assert `LEGEND_TEXT` is in `all_text(at)`. The simplest edit: in the `extractions` list, find the first entry whose `extraction_class` is `coupon` and, change `alignment_status` to `"match_lesser"`. `assess_grounding` then returns `"partial"`. Before writing the test, read `structure.py` and confirm this field drives grounding.

Commit: `fix: show amber legend only when needed`

## Task 3: report

Write `docs/plans/11-exact-match-legend-report.md` with:
- the commits
- the final `python -m pytest -q` summary line
- every existing test you changed, with the reason
- the amber cell count per fixture before and after (before: AAPL 0, GOOGL 68, MSFT 47, ORCL 0)

Commit: `docs: add slice 11 report`. Then stop.

## Task 4 (follow-up after review): whitespace-only differences are word for word

Review found 29 amber cells still left (GOOGL 23, MSFT 6). All 29 have `grounding_quality == "span_mismatch"`, and in every one the only difference between `span_text` and `raw` is whitespace: line breaks and runs of spaces from the filing layout. Example: span `'4.625%\n                    per annum'` vs raw `'4.625% per annum'`. These match word for word and must not be amber. The report called them genuine mismatches. That is wrong; correct it.

**Files:** `ui.py`, `views/results.py`, `tests/test_ui.py`, `tests/test_app_ui.py` if needed, `docs/plans/11-exact-match-legend-report.md`

1. In `ui.py`, import `normalize_ws` from `structure` (it already exists there; do not change `structure.py`). Extend `is_word_for_word` to also return True when `meta.get("span_text")` is not None and `normalize_ws(meta["span_text"]) == normalize_ws(meta.get("raw") or "")`, and that normalized value is non-empty. Update its docstring.
2. The Check column must agree with the cells. `plain_check` only sees issue strings, which are truncated to 40 characters, so it cannot tell whitespace-only mismatches apart. Give it an optional third parameter `audit_fields: dict[str, Any] | None = None`. When provided, drop every `UNGROUNDED` or `WEAK_GROUNDING` issue whose field name (the first token after the colon) has `is_word_for_word(audit_fields[field])` True. Keep the `FUZZY_ISSUE` filter for when `audit_fields` is None.
3. Give `table_frame` an optional `audit_records: list[dict[str, Any]] | None = None` parameter and pass `audit_records[i]["fields"]` to `plain_check` for row `i` when available. In `views/results.py`, pass `audit_records` to `table_frame` in `_render_table`. Leave every other caller unchanged.
4. Tests, written first:
   - `is_word_for_word({"grounded": False, "grounding_quality": "span_mismatch", "span_text": "4.625%\n     per annum", "raw": "4.625% per annum"})` is True. With `"raw": "4.000% per annum"` it is False. With `"span_text": None` it is False.
   - `plain_check("FLAGGED", ["WEAK_GROUNDING: coupon (span_mismatch, span 'x' vs 'y')"], {"coupon": {"span_text": "4.625%\n per annum", "raw": "4.625% per annum", "grounding_quality": "span_mismatch"}}) == "OK"`.
   - Change `test_not_exact_mask_fixture_amber_counts` so every fixture expects 0, as the Task 1 plan required.
   - For each of the 4 fixtures, `table_frame(vdf, audit_records)["Check"]` contains no value ending in `"not exact"` or `"not exact (+N more)"` for any N.
   - The `test_legend_shows_when_a_cell_is_not_exact` AppTest must still pass. If it relied on whitespace, change the edited extraction so its `extraction_text` really differs from the filing, e.g. set `extraction_text` to `"9.999%"`.
5. Update the report: after counts must be 0 for all 4 fixtures. Remove the "genuine span_mismatch" sentence. Add a Task 4 section listing the changed tests and why.

Commit: `fix: ignore whitespace-only span differences`, then amend nothing. Make a separate commit `docs: update slice 11 report` for the report. Then stop.

## Task 5 (follow-up after review): split issue strings only between issues

The MSFT fixture's Check column shows "See validation details (+1 more)". The page no longer has a validation details section. The cause: `validate.py` joins issues with `"; "`, and `plain_check` splits the string on every `";"`. The MSFT ratings issue quotes `"Moody’s, Aaa (negative outlook); S&P, AA"`, so the split produces a broken fragment `"S&P, AA' vs ..."` with no known code.

**Files:** `ui.py`, `tests/test_ui.py`, `docs/plans/11-exact-match-legend-report.md`

1. Add a module constant in `ui.py`:
   `ISSUE_CODES = ("UNGROUNDED", "WEAK_GROUNDING", "SUSPICIOUS_COUPON", "MISSING_COUPON", "PRICE_DEVIATION", "SPREAD_ANOMALY", "DATE_SEQUENCE_ERROR")`
   and `ISSUE_SPLIT = re.compile(r";\s*(?=(?:" + "|".join(ISSUE_CODES) + r")\b)")`.
2. In `plain_check`, when `issues` is a string, split with `ISSUE_SPLIT.split(issues)` in place of `issues.split(";")`. Keep the rest of that line (strip, drop empty, drop "none" entries) as it is.
3. Tests, written first:
   - The exact MSFT string below must give `"OK"` with `audit_fields=None`. All issues in it are fuzzy except bookrunners, and bookrunners is `span_mismatch`, so with `audit_fields=None` it must give `"Bookrunners not exact"` or whatever label the field map gives. Assert the real output and explain it in the report. Build the string in the test as `"; ".join([...])` from these issues:
     - `"WEAK_GROUNDING: issuer (fuzzy, span 'MICROSOFT CORPORATION' vs 'MICROSOFT CORPORATION')"`
     - `"WEAK_GROUNDING: ratings (fuzzy, span 'Moody’s, Aaa (negative outlook); S&P, AA' vs 'Moody’s, Aaa (negative outlook); S&P, AA')"`
     - `"WEAK_GROUNDING: issue_price (fuzzy, span '99.933%' vs '99.933%')"`
   - With those three only, the result is `"OK"`. Before the fix it is `"See validation details"`.
   - For each of the 4 fixtures, `table_frame(vdf, audit_records)["Check"]` contains no value starting with `"See validation details"`.
4. Add a Task 5 section to the report.

Commit: `fix: split check issues only at issue codes`, then `docs: update slice 11 report`. Then stop.
