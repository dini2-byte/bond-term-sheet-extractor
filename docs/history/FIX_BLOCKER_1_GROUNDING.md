> Historical plan from 2026-09-24, kept as a record of the review. Its numbers come from the one-deal benchmark and are out of date. Current numbers: output/accuracy_benchmark_report.md.

# Fix Blocker 1: Strict Source Grounding

**Assignee**: Gemini
**Reviewer**: Claude Code
**Branch**: `fix/strict-grounding` (branch off `master`)
**Scope**: Grounding only. Do NOT touch anything listed under "Out of scope".

---

## Problem

`structure.py:86` sets `"grounded": char_interval is not None`. Any extraction with *any* offset counts as grounded, even when LangExtract itself says the alignment is weak.

Cached AAPL run (`output/AAPL_FWP_TermSheet_2025-05-06_extractions.jsonl`, 57 extractions):

| `alignment_status` | Count |
|---|---|
| `match_exact` | 37 |
| `match_fuzzy` | 14 |
| `match_lesser` | 6 |

The 6 `match_lesser` spans are wrong. Example: 2028 tranche `coupon` = `"4.000%"`, but `char_interval` = `[4429:4431]`. The document text at that offset is `"4."` and sits inside the **2030** tranche section. Same for the 2028 `tranche_name`, `principal_amount`, `maturity_date`, `issue_price`, and `make_whole_call`.

The app drill-down shows these wrong offsets with a "✅ Grounded" badge.

## Definition of "grounded" (new rule)

An extraction is grounded **only if all three hold**:

1. `char_interval` is not `None`
2. `alignment_status == "match_exact"`
3. `doc_text[start_pos:end_pos].strip() == extraction_text.strip()`

`doc_text` is the `"text"` key of the JSONL record. If `"text"` is missing, nothing is grounded.

## Required changes

### 1. `structure.py`

- Read `doc_text = data.get("text", "")` in `structure_filing_extractions`.
- Add a helper `assess_grounding(item: dict, doc_text: str) -> dict` returning:
  ```python
  {
      "grounded": bool,             # the 3-part rule above
      "alignment_status": str | None,
      "span_text": str | None,      # doc_text[start:end], or None if no interval
      "grounding_quality": str,     # one of the values below
  }
  ```
  `grounding_quality` values, checked in this order:
  - `"none"`: `char_interval` is None
  - `"no_source_text"`: `doc_text` empty
  - `"span_mismatch"`: span text != extraction text (regardless of alignment_status)
  - `"exact"`: `match_exact` and span matches
  - `"fuzzy"`: `match_fuzzy`
  - `"partial"`: `match_lesser` or any other status
- Merge the helper's output into each `field_data` dict (keep the existing `raw` and `char_interval` keys).
- Keep the helper short and pure. It must not mutate `item`.

### 2. `validate.py`

In `validate_tranche`, replace the single `UNGROUNDED` loop with:
- `grounding_quality == "none"` or `"no_source_text"` → `UNGROUNDED: <field> not anchored to source text`
- any other non-grounded field → `WEAK_GROUNDING: <field> (<grounding_quality>, span '<span_text>' vs '<raw>')`
  Truncate `span_text` and `raw` to 40 chars in the message.

### 3. `extract.py`

The console audit (lines ~50-62) counts `char_interval is not None` as grounded. Change it to print the counts from `alignment_status` (exact / fuzzy / lesser / none). Don't change anything else in `extract.py`.

### 4. `app.py` — drill-down tab only (`tab1`)

- Add columns `Alignment` (alignment_status) and `Source Span Text` (span_text).
- Badge: `✅ Exact` if grounded, `⚠️ Weak (<quality>)` if an interval exists but it isn't grounded, `❌ Ungrounded` if there's no interval.

### 5. `evaluate.py`

No code change needed. It already reads `raw_meta["grounded"]`, which will now be strict. Confirm it still runs.

## Tests (write these FIRST, watch them fail, then implement)

The existing mock in `tests/test_structure.py::test_mock_filing_structuring` has no `"text"` key and no `alignment_status`. Update it: add a `"text"` string whose offsets match every extraction exactly, and add `"alignment_status": "match_exact"` to each item. Existing asserts must keep passing.

New tests in `tests/test_structure.py`:
- `test_assess_grounding_exact`: exact status + matching span → grounded True, quality `"exact"`
- `test_assess_grounding_fuzzy_not_grounded`: `match_fuzzy` with matching span → grounded False, quality `"fuzzy"`
- `test_assess_grounding_span_mismatch`: `match_exact` but span text differs → grounded False, quality `"span_mismatch"`
- `test_assess_grounding_no_interval`: → grounded False, quality `"none"`
- `test_assess_grounding_no_doc_text`: → grounded False, quality `"no_source_text"`
- Extend `test_cached_aapl_fwp_extractions`: the 2028 tranche's `coupon` has `grounded is False` and `grounding_quality == "span_mismatch"` (span `"4."` != `"4.000%"`, and span mismatch is checked before alignment status)

New tests in `tests/test_validate.py`:
- weak field produces a flag starting with `WEAK_GROUNDING: coupon`
- field with no interval still produces `UNGROUNDED: coupon`
- fully exact tranche produces no grounding flags

## Expected results (Claude will check these numbers)

- `pytest -v`: all old + new tests pass, none skipped (the cached AAPL JSONL is on disk locally)
- `python3 evaluate.py`: **Field Accuracy stays 100.0% (56/56). Source Grounding drops to 57.1% (32/56).**
- `python3 validate.py`: the AAPL tranches now show `FLAGGED` with `WEAK_GROUNDING` entries. That is correct behavior.

If your grounding number is not 57.1%, stop and report why. Do not tune the rule to raise it.

## Out of scope (separate blockers, do NOT change)

- Hardcoded "100%" metric card in `app.py` and hardcoded hallucination line in `evaluate.py` (Blocker 2)
- `fields.py` prompt examples (Blocker 3)
- Adding benchmark deals / answer keys (Blocker 4)
- `.gitignore` / committing fixtures (Blocker 5)
- `SUBMISSION.md`, `README.md`, `CLAUDE_REVIEW_HANDOFF.md`: no doc edits yet
- Re-running the Gemini extraction. Work only from the existing cached JSONL.
- `matches_value` leniency, tranche ordering, `clean_principal`

## Deliverable

One commit on `fix/strict-grounding`:
```
fix: require exact alignment for source grounding
```
Then report back with:
1. `git diff --stat master...fix/strict-grounding`
2. Full `pytest -v` output
3. Full `python3 evaluate.py` output
