# Slice 12: Blank number checks report

## Commit

- `ee5cd3e` `fix: skip range checks on blank numbers`

## Test suite summary

`340 passed in 13.19s`

## Check values per fixture

Before:
- AAPL: `{'OK'}`
- GOOGL: `{'OK', 'Spread looks unusual'}`
- MSFT: `{'OK'}`
- ORCL: `{'OK'}`

After:
- AAPL: `{'OK'}`
- GOOGL: `{'OK'}`
- MSFT: `{'OK'}`
- ORCL: `{'OK'}`

## Changes

1. `validate.py`: Added `_is_blank` helper treating `None` and `float("nan")` as blank values. Updated `validate_tranche` coupon, price and spread checks to bypass bounds checks when fields are blank.
2. `tests/test_validate.py`: Added unit tests verifying `float("nan")` skips `SPREAD_ANOMALY` and `PRICE_DEVIATION`, `float("nan")` coupon yields `MISSING_COUPON` without `SUSPICIOUS_COUPON`, and out-of-range spread still triggers `SPREAD_ANOMALY`.
3. `tests/test_ui.py`: Added `TestSlice12BlankChecks` verifying GOOGL floating rate notes are marked `"OK"` without `"Spread looks unusual"`.
