> Historical plan from 2026-09-24, kept as a record of the review. Its numbers come from the one-deal benchmark and are out of date. Current numbers: output/accuracy_benchmark_report.md.

# Fix Blocker 2: Replace Hardcoded Metrics With Computed Ones

**Assignee**: Gemini
**Reviewer**: Claude Code
**Branch**: `fix/computed-metrics` (branch off `master` at `827a199`)
**Scope**: The two hardcoded headline numbers only. Do NOT touch anything listed under "Out of scope".

---

## Problem

Two headline numbers are typed in, not measured:

| Location | Hardcoded text | Why it's wrong |
|---|---|---|
| `evaluate.py:168` | `False Positive / Hallucination Rate: 0.0%` | Never computed. Would print 0.0% for any extraction. |
| `app.py:156` | Source Grounding card shows `100%` | Never computed. Real value for the AAPL deal after Blocker 1 is 63.9%. |

## Definitions

**Not-in-Source value**: an extracted value (not `None`) whose text, after collapsing all whitespace runs to a single space and stripping, does NOT appear anywhere in the whitespace-collapsed document text. This is the honest, checkable meaning of "hallucination" for this project: the model returned text that isn't in the filing.

**Not-in-Source Rate** = Not-in-Source values / extracted values (fields where a value was extracted). Missing fields are not counted as hallucinations.

**Exact Grounding (app card)** = fields with `grounded is True` / all fields across all tranches in `audit_records` (the same per-field records the drill-down tab shows).

## Required changes

### 1. `structure.py`

- Add a small pure helper `normalize_ws(s: str) -> str` that collapses whitespace runs (`re.sub(r"\s+", " ", s).strip()`).
- In `assess_grounding`, add a key `"found_in_source": bool` to **every** return path:
  `True` if `normalize_ws(extraction_text)` is a non-empty substring of `normalize_ws(doc_text)`, else `False`. With empty `doc_text` it is `False`.
  Compute it once at the top of the function, not once per branch.
- Add `grounding_summary(audit_records: list[dict]) -> dict` returning:
  ```python
  {"grounded": int, "total": int, "pct": float}  # pct = 0.0 when total == 0
  ```
  counting every field in every `audit_records[i]["fields"]`.

### 2. `evaluate.py`

- In `evaluate_deal`, add a column `"In Source"` to each result row:
  `raw_meta.get("found_in_source", False)` if `actual_val is not None`, else `None`.
- Extract the summary math out of `run_evaluation` into
  `compute_summary_metrics(eval_df: pd.DataFrame) -> dict` returning:
  ```python
  {
      "total": int, "correct": int, "accuracy_pct": float,
      "grounded": int, "grounding_pct": float,
      "extracted": int,        # rows where Extracted is not None
      "not_in_source": int,    # rows where In Source is False
      "not_in_source_pct": float,  # not_in_source / extracted * 100, 0.0 if extracted == 0
  }
  ```
- `run_evaluation` uses this dict for both the console scorecard and the markdown report.
- Replace the hardcoded report line with:
  `- **Not-in-Source (Hallucination) Rate**: **{pct:.1f}%** ({not_in_source}/{extracted} extracted values not found verbatim in filing)`
- Add the same line to the console scorecard, under `Source Grounding`.
- Regenerate `output/accuracy_benchmark_report.md` by running `python3 evaluate.py`.

### 3. `app.py`

- Import `grounding_summary` from `structure`.
- Replace the hardcoded `100%` card with the computed `pct` formatted `{pct:.1f}%`, and a sub-label `{grounded}/{total} fields exact`.
- Card value color: green `#16A34A` only when `pct == 100.0`, otherwise amber `#D97706`.
- Rename the card label from `Source Grounding` to `Exact Grounding`.
- Nothing else in `app.py` changes.

## Tests (write these FIRST, watch them fail, then implement)

`tests/test_structure.py`:
- `test_assess_grounding_found_in_source_true`: text present in doc with different whitespace (e.g. `"Aaa\n   AA+"` vs doc `"Aaa AA+"`) → `found_in_source is True`
- `test_assess_grounding_found_in_source_false`: text absent from doc → `False`
- `test_assess_grounding_found_in_source_no_doc`: empty doc → `False`
- The existing 5 `assess_grounding` tests must still pass; add an assert on `found_in_source` to at least the span_mismatch test (the value `"4.000%"` is absent from `"01234567894.200%extra"`, so `False`).
- `test_grounding_summary`: 2 tranches, 3 fields total, 2 grounded → `{"grounded": 2, "total": 3, "pct": 66.66...}` (use `pytest.approx`)
- `test_grounding_summary_empty`: `[]` → `total == 0`, `pct == 0.0`

`tests/test_evaluate.py`:
- `test_compute_summary_metrics`: hand-built `eval_df` with 4 rows: 3 correct, 2 grounded, 1 row with `Extracted=None`, 1 row with `In Source=False` → assert every key in the returned dict
- `test_compute_summary_metrics_no_extractions`: all `Extracted=None` → `not_in_source_pct == 0.0`, no ZeroDivisionError

## Expected results (Claude will check these numbers)

On the cached AAPL JSONL:
- `pytest -v`: all tests pass (28 existing + new), none skipped
- `python3 evaluate.py`:
  - Field Accuracy **100.0% (56/56)**, unchanged
  - Source Grounding **57.1% (32/56)**, unchanged
  - Not-in-Source Rate **0.0% (0/56)**, now computed
- `grounding_summary(audit)` for AAPL → **46 / 72 = 63.9%** (this is what the app card will show)

0.0% not-in-source is the real result here: every extracted value does appear somewhere in the filing. The grounding problems are about *where* the offsets point, which the 57.1% already captures. If your numbers differ, stop and report why. Do not adjust the definitions to hit them.

## Out of scope (do NOT change)

- Grounding rule from Blocker 1 (`assess_grounding` logic for `grounded` / `grounding_quality`); only add the new key
- `fields.py` prompt examples (Blocker 3)
- New benchmark deals / answer keys (Blocker 4)
- `.gitignore` / committing fixtures (Blocker 5)
- `matches_value` leniency, tranche ordering, `clean_principal`
- `SUBMISSION.md`, `README.md`, `CLAUDE_REVIEW_HANDOFF.md`, sidebar text in `app.py`: doc edits come after all blockers
- Re-running the Gemini extraction

## Deliverable

One commit on `fix/computed-metrics`:
```
fix: compute grounding and not-in-source metrics instead of hardcoding
```
Then report back with:
1. `git diff --stat master...fix/computed-metrics`
2. Full `pytest -v` output
3. Full `python3 evaluate.py` output
