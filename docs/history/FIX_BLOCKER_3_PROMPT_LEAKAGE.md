> Historical plan from 2026-09-24, kept as a record of the review. Its numbers come from the one-deal benchmark and are out of date. Current numbers: output/accuracy_benchmark_report.md.

# Fix Blocker 3: Remove Benchmark-Deal Values From the Prompt

**Assignee**: Gemini
**Reviewer**: Claude Code
**Branch**: `fix/prompt-leakage` (branch off `master` at `f2be14f`)
**Scope**: Remove test-set leakage from `fields.py`, add a guard test, re-run the one extraction. Do NOT touch anything listed under "Out of scope".

---

## Goal (read this first)

The goal is **a clean, honest benchmark**, not a higher score. The prompt currently contains values copied from the exact deal we score against, so the 100% accuracy number is contaminated. After this fix the accuracy and grounding numbers may go **down**. That is acceptable and expected to be reported as-is.

Do NOT rewrite the prompt to improve grounding or accuracy. Do NOT add instructions or examples tailored to the Apple filing's layout.

## Problem

Values from the AAPL benchmark deal (`data/answer_key.json`) appear in `fields.py`:

| Location | Leaked value | Where it comes from in AAPL |
|---|---|---|
| `PROMPT_DESCRIPTION` coupon example | `4.000%` | 2028 Notes coupon |
| `PROMPT_DESCRIPTION` issue_price example | `99.804%` | 2028 Notes price |
| `PROMPT_DESCRIPTION` yield example | `4.070%` | 2028 Notes yield |
| `PROMPT_DESCRIPTION` spread example | `25 basis points` | 2028 Notes spread |
| `SAMPLE_TERM_SHEET` 2035 tranche coupon (+ its extraction) | `4.200%` | 2030 Notes coupon |
| `SAMPLE_TERM_SHEET` principal amounts | `$1,500,000,000`, `$1,000,000,000` | 2028 / 2030-2035 principal |

## Required changes

### 1. Guard test FIRST: `tests/test_fields.py` (new file)

Write this test before touching `fields.py`, and confirm it FAILS on current `master`.

- Load `data/answer_key.json`. Iterate over **every deal and every tranche** in it (so deals added in Blocker 4 are covered automatically).
- Build a set of "leak strings" per tranche, formatted the way term sheets print them:
  - Coupon: `f"{c:.3f}%"` (e.g. `4.000%`)
  - Issue Price: `f"{p:.3f}"` (e.g. `99.804`)
  - Yield: `f"{y:.3f}%"`
  - Spread: `f"{s} basis points"` and `f"+{s} bps"` and `f"{s} bps"`
  - Principal: `f"${p * 1_000_000:,.0f}"` (e.g. `$1,500,000,000`)
  - CUSIP: as-is
  - Benchmark Treasury, Maturity Date, Par Call Date, Trade Date, Settlement Date: as-is
  - **Excluded** (too generic to be leakage): Issuer, Ratings, Day Count
- Build the searchable prompt text:
  `PROMPT_DESCRIPTION + SAMPLE_TERM_SHEET + every extraction_text in FEW_SHOT_EXAMPLES`
- `test_prompt_contains_no_benchmark_values`: assert no leak string is a substring of that text. On failure, the message must list every leaked string and which deal/tranche/field it came from.
- Keep the leak-string builder a small helper function in the test file, with one unit test of its own (`test_leak_strings_formatting`) using a hand-built tranche dict.

### 2. `fields.py`

- Change the four `(e.g. ...)` examples in `PROMPT_DESCRIPTION` to values not in the answer key. Suggested: `5.125%`, `99.612%`, `5.214%`, `85 basis points or +85 bps`.
- Change `SAMPLE_TERM_SHEET` so no value collides with the answer key:
  - 2035 tranche coupon `4.200%` → e.g. `5.375%` (update the tranche title `4.200% Notes due 2035` and both matching `Extraction` entries)
  - Principal amounts → e.g. `$1,250,000,000` and `$750,000,000`; keep the header total consistent (`$2,000,000,000 Senior Notes`)
- Every `extraction_text` in `FEW_SHOT_EXAMPLES` must still appear verbatim in `SAMPLE_TERM_SHEET` (LangExtract needs that for the few-shot alignment). Add a test for this: `test_few_shot_extractions_are_verbatim_in_sample`.
- Change nothing else in `fields.py`: same field list, same instructions, same structure.

### 3. Re-run the extraction (one API call)

The cached `output/AAPL_FWP_TermSheet_2025-05-06_extractions.jsonl` was produced with the contaminated prompt, so it must be regenerated.

```bash
cp output/AAPL_FWP_TermSheet_2025-05-06_extractions.jsonl output/AAPL_FWP_TermSheet_2025-05-06_extractions.pre_blocker3.jsonl
python3 extract.py data/raw_filings/AAPL_FWP_TermSheet_2025-05-06.txt
python3 evaluate.py
```

- Same model (`gemini-3.5-flash-lite`), same settings. Run it **once**. Do not re-run to get a better result.
- Keep the `.pre_blocker3.jsonl` backup (it's gitignored) so Claude can diff old vs new.

### 4. Existing tests after the re-run

Some tests read the cached AAPL JSONL (`test_cached_aapl_fwp_extractions`, `test_run_evaluation_e2e`). If any of them fail after the re-run because the extraction output changed:
- **Do NOT edit those tests to make them pass.**
- Stop and report the failing assertions verbatim. Claude will decide whether the test or the code is wrong.

## Expected results (Claude will check)

- `tests/test_fields.py` fails on `master`, passes on the branch
- All other tests: pass, or failures reported per section 4
- `python3 evaluate.py`: new accuracy / grounding / not-in-source numbers, **whatever they are**. There is no target number for this blocker.
- `git diff master...fix/prompt-leakage -- fields.py` shows only the value swaps described above

## Out of scope (do NOT change)

- Prompt wording, instructions, field list, or adding examples to "improve" results
- `structure.py`, `validate.py`, `evaluate.py`, `app.py`, `extract.py`
- Answer keys / new deals (Blocker 4)
- `.gitignore` / committing fixtures (Blocker 5)
- `matches_value` leniency, tranche ordering, `clean_principal`
- `SUBMISSION.md`, `README.md`, `CLAUDE_REVIEW_HANDOFF.md`
- Re-running the extraction more than once

## Deliverable

One commit on `fix/prompt-leakage`:
```
fix: remove benchmark-deal values from extraction prompt
```
Include the regenerated `output/accuracy_benchmark_report.md`.

Then report back with:
1. `git diff --stat master...fix/prompt-leakage`
2. `pytest -v` output from **before** the fields.py change (showing `test_fields.py` failing) and **after**
3. Full `python3 extract.py` console output (alignment counts)
4. Full `python3 evaluate.py` output
