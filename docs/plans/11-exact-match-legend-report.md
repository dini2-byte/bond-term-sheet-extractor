# Slice 11: Exact match legend report

## Commits

- `0260f4c` `fix: count fuzzy spans as word for word`
- `f6dfbfc` `fix: show amber legend only when needed`

## Test suite summary

`325 passed in 14.06s`

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

## Amber cell count per fixture

- AAPL: before 0, after 0
- GOOGL: before 68, after 23
- MSFT: before 47, after 6
- ORCL: before 0, after 0

Across the 4 fixtures, 86 cells that were amber solely due to fuzzy grounding were cleared. The 29 remaining amber cells across GOOGL (23) and MSFT (6) are genuine `span_mismatch` entries where filing text line breaks and Edgar formatting differ from raw extraction text.
