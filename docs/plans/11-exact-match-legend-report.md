# Slice 11: Exact match legend report

## Commits

- `0260f4c` `fix: count fuzzy spans as word for word`
- `f6dfbfc` `fix: show amber legend only when needed`
- `c0965f9` `fix: ignore whitespace-only span differences`

## Test suite summary

`330 passed in 14.12s`

## Existing tests changed

1. `tests/test_ui.py::TestSlice6UiHelpers::test_plain_check_flagged_with_multiple_issues`
Changed issue strings from `fuzzy` to `span_mismatch`.
Reason: fuzzy grounding issues are now filtered out in `plain_check` and return "OK", so testing multiple issue aggregation requires non-fuzzy grounding issues like `span_mismatch`.

2. `tests/test_ui.py::TestSlice6UiHelpers::test_plain_status`
Added `"grounding_quality": "span_mismatch"` to the case asserting "Found, but the match is not exact".
Reason: `plain_status` now maps fuzzy grounding to "Found word for word". A "not exact" status requires a non-fuzzy grounding quality like `span_mismatch`.

3. `tests/test_ui.py::TestSlice6UiHelpers::test_table_frame`
Changed `assert tf["Check"].iloc[0] != "OK"` to `assert tf["Check"].iloc[0] == "OK"`.
Reason: AAPL row 0 was previously flagged only for a fuzzy settlement_date weak grounding issue. With fuzzy issues filtered out, the tranche check is "OK".

4. `tests/test_app_ui.py::test_saved_filing_opens_free`
Added `assert LEGEND_TEXT not in text`.
Reason: verified that the amber legend does not render on the AAPL deal where all cells match word for word.

## Task 4 changes

1. `tests/test_ui.py::TestSlice11ExactMatch::test_not_exact_mask_fixture_amber_counts`
Changed expected amber cell count from 23 to 0 for GOOGL, and from 6 to 0 for MSFT.
Reason: with whitespace-only differences between filing line breaks and raw values treated as word for word, zero amber cells remain.

2. `tests/test_app_ui.py::test_legend_shows_when_a_cell_is_not_exact`
Set `item["extraction_text"] = "9.999%"` for the edited coupon extraction.
Reason: the test previously changed only `alignment_status` while leaving span text identical to raw text. Because identical text is word for word regardless of alignment quality, an explicit extraction text mismatch is needed to verify amber cell rendering.

## Amber cell count per fixture

- AAPL: before 0, after 0
- GOOGL: before 68, after 0
- MSFT: before 47, after 0
- ORCL: before 0, after 0

Across the 4 fixtures, all 115 amber cells in GOOGL and MSFT are cleared. 86 cells were cleared by treating fuzzy grounding as word for word, and the remaining 29 were cleared by normalizing whitespace runs and line breaks between filing spans and raw extraction text.
