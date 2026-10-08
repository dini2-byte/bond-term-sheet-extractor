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

---

# Task G: Review follow-ups (added 2026-10-07)

Claude's review and a Python review of Tasks A-F found the problems below. Fix them on the same branch, test first, same rules as above. Two of them (G1, G2) are defects in this plan, not in the code: the plan's ratings rule cannot work on real filings, and the comps table should show clean dates.

All of G1-G9 must land before slice 2 runs the benchmark, because no scoring or normalisation change is allowed after that run.

## G1: Normalise ratings in the comps table (`structure.py`)

Add `normalize_ratings(raw: str | None) -> str | None` to `structure.py` and use it for the comps-table `Ratings` column. Keep the raw text in the audit record (grounding uses the raw text).

It returns the rating grades in order of appearance, joined by `" / "`. Remove parentheticals first. A grade is a Moody's grade (`Aaa`, `Aa1`-`Aa3`, `A1`-`A3`, `Baa1`-`Baa3`, `Ba1`-`Ba3`, `B1`-`B3`, `Caa1`-`Caa3`, `Ca`, `C`) or an S&P/Fitch grade (`AAA`, `AA`, `A`, `BBB`, `BB`, `B`, `CCC`, each with optional `+` or `-`, plus `CC`, `C`, `D`), matched as a whole token. Return `None` when no grade is found.

Required tests:

| Input | Output |
|---|---|
| `Aaa (stable) by Moody’s Investors Service, Inc.\nAA+ (stable) by Standard & Poor’s Ratings Services` | `Aaa / AA+` |
| `Moody’s, Aaa (negative outlook); S&P, AAA (stable outlook)` | `Aaa / AAA` |
| `Moody’s: Aa2 (Stable); S&P: AA+ (Stable)` | `Aa2 / AA+` |
| `A1 by Moody’s Investor Service, Inc.\nAA by Standard & Poor’s Ratings Services\nAA- by Fitch Ratings Inc.` | `A1 / AA / AA-` |
| `Aaa / AA+` | `Aaa / AA+` |
| `Not rated` | `None` |

In `evaluate.py`, the `Ratings` rule becomes: `normalize_ratings(actual) == normalize_ratings(expected)`, both not `None`. Remove `clean_ratings_part`.

## G2: Normalise dates in the comps table (`structure.py`)

Add `normalize_date(raw: str | None) -> str | None`. It finds the first full date in the text, written as `Month D, YYYY` (full or 3-letter month name, comma optional), and returns it as `Month D, YYYY` with the full month name. Return `None` if there is no full date. Use it for the comps-table columns Trade Date, Settlement Date, Maturity Date and Par Call Date. Keep raw text in the audit record.

Required tests: `On or after April 12, 2028` gives `April 12, 2028`. `May 12, 2025 (T+5)` gives `May 12, 2025`. `Sept. 14, 2026` is out of scope (return `None` is acceptable). `May 2028` gives `None`. `2028` gives `None`.

## G3: Strict date parsing in `evaluate.py`

Replace `dateutil.parser.parse`. It fills a missing day or month from today, so `May 2028` parses as May 7, 2028. Use `normalize_date` from G2 on both sides and compare the strings, both not `None`. Remove the `dateutil` import.

## G4: `clean_principal` with commas and unit words

Strip commas before matching the unit words. Add `mm` as a million unit. Required tests: `$1,500 million` gives 1500.0. `1,250.5 million` gives 1250.5. `$2,000mm` gives 2000.0. `£1,250,000,000` gives 1250.0.

## G5: Two-pass tranche pairing

Pairing is greedy, so the maturity fallback can take a tranche that a later answer-key tranche matches exactly by CUSIP. Pair in two passes: first every answer-key tranche by CUSIP, then the maturity fallback over the tranches left on both sides. Remove the index fallback completely. Give the mock rows in the existing tests a CUSIP so they pair by CUSIP.

Required test: extracted `[{CUSIP: B, maturity: Jan 1, 2030}, {CUSIP: A, maturity: Jan 1, 2030}]`, key `[{CUSIP: X, maturity: Jan 1, 2030}, {CUSIP: B, maturity: Jan 1, 2030}]`. The key tranche with CUSIP B pairs with extracted B.

## G6: NaN is a missing value

After pandas, a missing value is `NaN`, not `None`. At the top of `matches_value`, and for each `actual_val` in `evaluate_deal`, turn a scalar `NaN` into `None`. Use the converted value for `Grounded` too, so a missing value is never grounded. Required test: key `{CUSIP: B, Par Call Date: None}` against an extracted row with `Par Call Date` NaN scores Correct=True and Grounded=False.

## G7: Metric denominators

- **Field accuracy**: correct / all answer-key fields (unchanged).
- **Grounded %**: grounded / fields with an extracted value (not `None`). Today it divides by all fields, which mixes misses into grounding.
- **Not-in-source %**: not-in-source / fields with an extracted value (same denominator as grounded %).

Show each denominator in the headline lines, for example `Grounded: 92.9% (52/56 extracted fields)`.

## G8: Report unmatched extracted tranches in the headline

Add a fourth headline line: `Unmatched extracted tranches: N`. They are not scored, but they must be visible.

## G9: Small fixes

- `run_evaluation` must not crash when the combined results are empty. Build every results frame with explicit columns.
- The Spread rule rejects `bool` values.
- Principal: compare `abs(a - b) <= 0.05` after converting both to float, instead of `round(x, 1)` on both sides.

## G deliverable

Same report shape as above: failing then passing output per item, full `pytest -q`, full `python3 evaluate.py`.

---

# Task H: Second review follow-ups (added 2026-10-07)

A second Python review confirmed G1-G9 and found these. All must land before slice 2, same rules as above, test first.

## H1: "Not found" is a missing value

`structure.py` still fills Benchmark Treasury, Day Count, CUSIP and Issuer with the string `"Not found"` when nothing was extracted, while Ratings and the dates use `None`. An answer key of `null` against `"Not found"` then scores wrong, which punishes the extractor for correctly reporting Not found (MSFT states no day count, so this hits 7 fields). Make every comps-table field use `None` for "nothing extracted". The app may still display `None` as "Not found" (that is a display concern; leave `app.py` alone in this task). In `matches_value`, also treat the string `"Not found"` as `None`, as a safety net.

Required test: key `{Day Count: null}` against an extracted tranche with no day_count extraction scores Correct=True, Grounded=False, and the field is not counted as extracted.

## H2: Bare "A" must not match outside a rating context

`normalize_ratings("N/A")` returns `"A"`, and `"A rating of Aa1 / AA+"` returns `"A / Aa1 / AA+"`. Fix:
- Return `None` for `N/A`, `NA`, `Not rated`, `NR` (case-insensitive, whole value).
- A token that is a single letter (`A`, `B`, `C`, `D`) counts only when it is followed, after optional whitespace, by `/`, `;`, `,`, `(`, end of text, or the words `by`, `from`, `\n`; or preceded by `/`, `;`, `:`, `,`. Otherwise skip it.

Required tests: `N/A` gives `None`. `A rating of Aa1 / AA+` gives `Aa1 / AA+`. `Baa1 / A / A-` gives `Baa1 / A / A-`. `A (stable) by S&P` gives `A`. All existing G1 tests still pass.

## H3: `normalize_date` accepts common abbreviations and rejects impossible dates

Accept `Sept`, and an optional `.` after an abbreviated month (`Sep. 9, 2025`, `Sept. 9, 2025`, `Aug. 26, 2030`). Validate with `datetime.date(year, month, day)`; return `None` if it raises (`Feb 31, 2025` gives `None`).

## H4: Extracted-field denominator

Grounded % and not-in-source % divide by "fields with an extracted value". Count a field as extracted when its comps-table value is not `None` (after H1), not by whether an audit entry exists. A field with a value but no audit entry counts as extracted, not grounded and not in source. Add a test for that case.

## H5: `clean_principal` handles `B` and `MM`

`$1.5B` gives 1500.0, `$750MM` gives 750.0, `$2bn` gives 2000.0. Keep all existing principal tests passing.

## H deliverable

Same report shape: failing then passing output per item, full `pytest -q`, full `python3 evaluate.py`.
