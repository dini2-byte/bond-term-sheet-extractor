# Slice 12: blank numbers are missing, not unusual

**Implementer:** agy (headless, `gemini-3.8-flash-high`)
**Reviewer:** Claude
**Branch:** `slice-12-blank-checks`, from `master` at the current HEAD

## Problem

On the GOOGL 2026-08-07 deal the two floating rate notes show "Spread looks unusual" in the Check column. A floating rate note has no spread to a Treasury, so its `Spread (bps)` is blank. In the DataFrame that blank is `NaN`, not `None`. `validate_tranche` only skips `None`, so it runs `0 <= nan <= 1000`, which is False, and flags `SPREAD_ANOMALY: nan bps outside standard bounds`.

The coupon and issue price checks have the same hole. A `NaN` coupon is reported as `SUSPICIOUS_COUPON: nan%` when it should be `MISSING_COUPON`. A `NaN` price is reported as `PRICE_DEVIATION: nan` when it should not be flagged at all.

`evaluate.py` calls `validate_comps_table` but never reads `Validation Status` or `Validation Issues`, so benchmark scores do not move.

## Global Constraints

- Change only `validate.py`, `tests/test_validate.py`, `tests/test_ui.py` and the report. Do not change `structure.py`, `evaluate.py`, `extract.py`, `ui.py`, `views/`, the fixtures or `output/`.
- Make no Gemini calls. Never touch real R2: do not read R2 values from `.env` and do not run `seed_cache.py`. Never run `git stash`.
- Write tests first and watch them fail. Run `python -m pytest -q` and show it passing before each commit.
- Commit subjects: Conventional Commits prefix, imperative mood, 50 characters or fewer, no trailing period. No Oxford commas. No AI attribution of any kind: no `Co-Authored-By` trailers and no "Generated with" lines.
- Do not push or merge.

## Task 1: treat NaN as blank in the range checks

**Files:** `validate.py`, `tests/test_validate.py`, `tests/test_ui.py`

In `validate.py` add `import math` and this helper above `validate_tranche`:

```python
def _is_blank(value: Any) -> bool:
    """None, or a float NaN from a blank DataFrame cell."""
    return value is None or (isinstance(value, float) and math.isnan(value))
```

In `validate_tranche`, replace the three `is not None` tests:
- Coupon: `if coupon is not None:` becomes `if not _is_blank(coupon):`. The `else` branch still appends `"MISSING_COUPON"`.
- Price: `if price is not None:` becomes `if not _is_blank(price):`.
- Spread: `if spread is not None:` becomes `if not _is_blank(spread):`.

Tests in `tests/test_validate.py`, reusing the existing `valid_tranche_row` and `valid_audit_fields` fixtures. Write them before the code change and confirm they fail first:
- `float("nan")` spread: no flag starts with `"SPREAD_ANOMALY"`.
- `float("nan")` issue price: no flag starts with `"PRICE_DEVIATION"`.
- `float("nan")` coupon: `"MISSING_COUPON"` is in the flags and no flag starts with `"SUSPICIOUS_COUPON"`.
- A real out-of-range spread, e.g. `1500`, still gives a `SPREAD_ANOMALY` flag.

Test in `tests/test_ui.py`: for the GOOGL fixture `data/fixtures/GOOGL_FWP_TermSheet_2026-08-07_extractions.jsonl`, build `vdf = validate_comps_table(df, audit_records)` and `tf = table_frame(vdf, audit_records)`. Assert `"Spread looks unusual"` is not in `tf["Check"].tolist()`, and assert rows 0 and 1 (the two floating rate notes) are `"OK"`.

Commit: `fix: skip range checks on blank numbers`

## Task 2: report

Write `docs/plans/12-blank-number-checks-report.md` with:
- the commit
- the final `python -m pytest -q` summary line
- the set of `Check` values per fixture before and after, for all 4 fixtures in `data/fixtures/*_extractions.jsonl`. Before: AAPL `{'OK'}`, GOOGL `{'OK', 'Spread looks unusual'}`, MSFT `{'OK'}`, ORCL `{'OK'}`

Commit: `docs: add slice 12 report`. Then stop.
