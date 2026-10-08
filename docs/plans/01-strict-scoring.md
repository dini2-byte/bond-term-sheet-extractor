# Slice 1: Strict scoring, CUSIP pairing, committed fixtures

**Implementer**: agy
**Reviewer**: Claude Code
**Branch**: `slice-01-strict-scoring` (already created from `fix/prompt-leakage`, which holds the Blocker 3 fix)
**Due**: 2026-10-12

Read `CONTEXT.md` first and use its terms. Read `docs/adr/0001-exact-match-grounding.md`.

## Goal

Make the benchmark numbers trustworthy before new deals are added in slice 2. Today the scorer accepts substring matches, pairs tranches by list position, reads its input from a gitignored folder and handles only one deal. After this slice, field accuracy must use strict per-field rules, tranches must pair by CUSIP, and a fresh clone must be able to run `evaluate.py` and the tests.

The goal is correct scoring, not a high score. Field accuracy on AAPL may drop below 100%. Report whatever number comes out.

**This slice makes no Gemini API calls.** Do not run `extract.py`.

## Rules

- Write each test before its code change. Run it and show it failing, then make it pass.
- Do not commit. Leave all changes in the working tree. Claude commits after review.
- Do not touch: `fields.py`, `extract.py`, `app.py`, `data/answer_key.json`, `SUBMISSION.md`, `README.md`, or any `.md` file in the repo root.
- Do not edit an existing test only to make it pass, except the one stale test named in Task B.

## Task A: Commit the AAPL extraction as a fixture

1. Create `data/fixtures/`.
2. Copy `output/AAPL_FWP_TermSheet_2025-05-06_extractions.jsonl` to `data/fixtures/AAPL_FWP_TermSheet_2025-05-06_extractions.jsonl`. Copy the file byte for byte. Do not regenerate it.
3. Add `FIXTURES_DIR = Path("data/fixtures")` to `evaluate.py`. `evaluate.py` reads extractions from `FIXTURES_DIR / f"{deal_key}_extractions.jsonl"`.
4. Tests that read the cached AAPL extraction must read the fixture. They must fail, not skip, when the fixture is missing.
5. Confirm that `.gitignore` does not ignore `data/fixtures/`.

## Task B: Fix the stale structure test

`tests/test_structure.py::test_cached_aapl_fwp_extractions` asserts that the 2028 coupon is `span_mismatch`. The Blocker 3 re-run removed that defect, so the assertion is out of date.

Change only the last block of that test:
- The 2028 coupon is grounded, with `grounding_quality == "exact"`.
- The settlement date of every tranche is not grounded, because its alignment is fuzzy (`May 12, 2025 (T+5)`).

Keep all other assertions in the test.

## Task C: Strict `matches_value`

Replace the lenient rules in `evaluate.py::matches_value`. Remove the substring rule (`exp_str in act_str or act_str in exp_str`) completely. Use one rule per field:

| Field(s) | Rule |
|---|---|
| Coupon (%), Issue Price, Yield (%) | Equal after rounding both values to 3 decimal places |
| Principal ($M) | Equal after rounding both values to 1 decimal place |
| Spread (bps) | Integer equality |
| Trade Date, Settlement Date, Maturity Date, Par Call Date | Parse both to a calendar date and compare. Remove a trailing parenthetical first, so `May 12, 2025 (T+5)` parses as May 12, 2025. A value that does not parse is incorrect |
| Ratings | Split both values on `/`. From each part, remove parentheticals and agency names (Moody's, S&P, Fitch). Compare the resulting grade lists, in order, case-sensitive |
| CUSIP | Exact match after removing whitespace and converting to uppercase |
| Issuer, Benchmark Treasury, Day Count | Equal after `normalize_text`. No substring match |

`None` and `None` still match. `None` and a value still do not match.

Required test cases (add to `tests/test_evaluate.py`; add more as needed):
- `matches_value("APPLE INC.", "Apple Inc.", "Issuer")` is True
- `matches_value("Apple", "Apple Inc.", "Issuer")` is False
- `matches_value("May 12, 2025 (T+5)", "May 12, 2025", "Settlement Date")` is True
- `matches_value("May 13, 2025", "May 12, 2025", "Settlement Date")` is False
- `matches_value("Aaa (Moody's) / AA+ (S&P)", "Aaa / AA+", "Ratings")` is True
- `matches_value("Aaa / AA", "Aaa / AA+", "Ratings")` is False
- `matches_value("Aaa", "Aaa / AA+", "Ratings")` is False
- `matches_value(4.0, 4.00, "Coupon (%)")` is True
- `matches_value(4.005, 4.0, "Coupon (%)")` is False
- `matches_value(" 037833ey2 ", "037833EY2", "CUSIP")` is True

## Task D: Pair tranches by CUSIP

Replace index-based pairing in `evaluate_deal`.

1. For each answer-key tranche, find the extracted tranche with the same CUSIP (compare with the CUSIP rule from Task C).
2. If no CUSIP matches, fall back to the extracted tranche with the same maturity date (use the date rule from Task C).
3. Each extracted tranche can pair with only one answer-key tranche.
4. If an answer-key tranche has no pair, score every field of that tranche as incorrect, with `Extracted = None`, not grounded and `In Source = None`.
5. Extracted tranches with no pair are not scored. Count them and report them as "unmatched extracted tranches".
6. Read audit grounding data from the paired extracted tranche, not by list position.

Required tests:
- Extracted tranches in reverse order still pair correctly.
- A tranche with a wrong CUSIP but the correct maturity date pairs by maturity date.
- A tranche with no match scores all its fields as incorrect.
- An extra extracted tranche is counted as unmatched and is not scored.

## Task E: `clean_principal` handles words

`structure.py::clean_principal` returns millions. It must handle:

| Input | Output |
|---|---|
| `$1,500,000,000` | 1500.0 |
| `$1.5 billion` | 1500.0 |
| `$750 million` | 750.0 |
| `US$1,000,000,000` | 1000.0 |
| `$500,000,000 aggregate principal amount` | 500.0 |

Add one test per row to `tests/test_structure.py`.

## Task F: Evaluate every deal in the answer key

1. `run_evaluation` iterates over every deal key in `data/answer_key.json`. Remove the hardcoded `deal_key`.
2. If a deal has no fixture, raise `FileNotFoundError` that names the deal and the expected fixture path.
3. Compute metrics for each deal and for all deals together.
4. Console output and `output/accuracy_benchmark_report.md` must start with one headline line in this exact shape:
   `Field accuracy: 97.6% (164/168 fields, 4 deals, 14 tranches)`
   Then show grounded % (with count) and not-in-source % (with count) for all deals together.
5. After the headline, show a per-deal table (deal, tranches, fields, correct, accuracy %, grounded %, unmatched extracted tranches), then the per-field table, then the discrepancy log with a Deal column.
6. Use the term "Not-in-source" everywhere. Remove the word "Hallucination" from `evaluate.py` output and from the report.
7. Regenerate `output/accuracy_benchmark_report.md` by running `python3 evaluate.py` against the fixture.

## Deliverable

Leave changes uncommitted on `slice-01-strict-scoring`. Then report:
1. `git status --short` and `git diff --stat`
2. For each task, the failing test output before the change and the passing output after
3. Full `python3 -m pytest -q` output at the end
4. Full `python3 evaluate.py` output
5. Any place where you were unsure and what you chose
