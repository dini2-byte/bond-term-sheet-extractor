# Non-USD display handoff report

Implementer: agy
Branch: non-usd-display
Date: 2026-10-13

## 1. Step 1 outcome

The team ran prompt trial v2b on 2026-10-13 across the 4 benchmark filings and the 10 EUR and GBP test set filings (14 Gemini calls).

### v2b results
- Benchmark field accuracy: 342/350 (97.7%)
- Not-in-source: 0/335 (0.0%)
- Found word for word: 51.9%
- Euro spread and benchmark pair right: 22/22
- Other test set fields: yield 23/26 (T 2025 missed), and benchmark run lost 6 ORCL par call dates

### Decision
The run rejected v2 because benchmark accuracy fell below the required 344/350 threshold (342/350) and test set yield degraded.
Per step 1 instructions, git restored the prompt and its tests from master (`git show master:fields.py > fields.py`, `git show master:tests/test_fields.py > tests/test_fields.py`).
No fixtures in `data/fixtures/` or extractions in `data/test_set/extractions/` changed.
`data/fixtures/attempts.jsonl` logged the run attempts, and the table in `data/test_set/README.md` recorded the results.
The KO mid-swap spread issue remains open as planned.

## 2. PRD metrics against targets

| Metric | Target | Result | Status |
|---|---|---|---|
| Currency detection on 10 EUR and GBP deals | 100% | 27/27 tranches (100%) | Passed |
| Bond count on all 11 test set deals | 100% | 11/11 deals (100%) | Passed |
| Benchmark label | "Benchmark" across all deals | 100% | Passed |
| JPY deal absent from search | 100% excluded | Excluded | Passed |
| Benchmark field accuracy | >= 98.3% (344/350) | 344/350 (98.3%) | Passed |

## 3. Headline numbers

All benchmark headline numbers remain unchanged from master baseline:
- Field accuracy: 98.3% (344/350 fields, 4 deals, 25 tranches)
- Found word for word (grounded): 55.5% (186/335 extracted fields)
- Not in the filing (not-in-source): 0.0% (0/335 extracted fields)
- Unmatched extracted tranches: 2

Because the prompt change failed the gate, no benchmark extractions changed.

## 4. Tests added, changed and deleted

### `tests/test_structure.py`
- Added `TestCleanCurrency`: verifies `clean_currency` on symbols (`$`, `€`, `£`, `¥`) and codes, handles invalid inputs and verifies `Currency` column placement after `Principal ($M)` across the 4 benchmark fixtures.
- Added `TestExportCompsToExcel`: verifies USD export leaves columns unchanged without `Currency`, while non-USD and mixed deals keep `Currency` and rename `Principal ($M)` to `Principal (M)`.

### `tests/test_lookup.py`
- Added `TestDealCurrencies`: verifies `deal_currencies` returns expected currencies for all 11 test set deals, returns `["USD"]` for the 4 benchmark deals and ignores concurrent offerings such as the PG pattern.
- Updated `TestCountBonds`: verifies bond counts for all 11 test set deals without Common Code false positives, and verifies benchmark filings keep their keyed tranche counts.
- Updated `TestFindTermSheets`: verifies non-USD/EUR/GBP deals (JPY) drop out of search results.

### `tests/test_test_set.py`
- Removed strict `xfail` markers on `test_count_bonds_matches_key` (all 11 test set filings pass).
- Added tests verifying extracted bond currencies match test set answers.

### `tests/test_ui.py`
- Added tests for `size_label` and `size_help` across single and multi-currency inputs.
- Verified "Treasury" renamed to "Benchmark" in `TABLE_COLUMNS` and `TEXT_COLUMNS`.
- Verified spread cell formatting keeps decimals when present and formats integers without decimals.

### `tests/test_app_ui.py`
- Added "not supported", "coming soon", "not implemented" and "unavailable" to `NEVER_SHOW`.
- Added `TestBuildDealLine`: verifies currency formatting in deal lines for USD, EUR, GBP and mixed currency deals.
- Added `TestSearchPickerCurrencyLabel`: verifies search picker labels include currency descriptions for non-USD deals while keeping USD deals unmodified.

### `tests/test_fields.py`
- Restored master version after rejecting prompt trial v2b.

## 5. Items skipped, unsure or rule exceptions

- The KO mid-swap spread issue remains open because the v2 prompt failed the step 1 gate.
- No Gemini extraction calls occurred after step 1.
- No rules in `08-non-usd-handoff.md` failed.

## 6. What a reviewer should look at first

1. `app.py`:
   - `build_deal_line`: aggregates amounts by currency and joins with " and " (no Oxford comma).
   - `sheet_label`: appends currency description for non-USD deals.
   - Column configuration: dynamically assigns `NumberColumn` or text `Column` based on currency.
2. `structure.py`:
   - `export_comps_to_excel`: drops `Currency` for USD-only deals; keeps `Currency` and renames `Principal ($M)` to `Principal (M)` for deals containing non-USD tranches.
3. `score_test_set.py`:
   - Currency scores 27/27, size scores 27/27 and bond counts match key on all 11 deals.

## 7. Verification outputs

### pytest

```
........................................................................ [ 25%]
........................................................................ [ 51%]
........................................................................ [ 77%]
...............................................................          [100%]
279 passed in 16.65s
```

### evaluate.py

```
Field accuracy: 98.3% (344/350 fields, 4 deals, 25 tranches)
Grounded: 55.5% (186/335 extracted fields)
Not-in-source: 0.0% (0/335 extracted fields)
Unmatched extracted tranches: 2
```

### score_test_set.py

```
| Deal | Bonds (key / extracted / search count) | Currency | Size | Coupon | Price | Yield | Benchmark | Spread | Maturity | CUSIP |
|---|---|---|---|---|---|---|---|---|---|---|
| IBM_FWP_TermSheet_EUR_2025-02-05 | 4 / 4 / 4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 0/4 | 0/4 | 4/4 | 4/4 |
| IBM_FWP_TermSheet_EUR_2026-01-29 | 4 / 4 / 4 | 4/4 | 4/4 | 3/3 | 4/4 | 3/3 | 3/3 | 3/3 | 4/4 | 4/4 |
| IBM_FWP_TermSheet_GBP_2015-07-29 | 1 / 1 / 1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| KO_FWP_TermSheet_EUR_2024-05-07 | 2 / 2 / 2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 0/2 | 2/2 | 2/2 |
| KO_FWP_TermSheet_EUR_2024-08-09 | 2 / 2 / 2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 0/2 | 2/2 | 2/2 |
| PG_FWP_TermSheet_EUR_2024-04-22 | 2 / 2 / 2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| PG_FWP_TermSheet_EUR_2025-10-27 | 2 / 2 / 2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| PG_FWP_TermSheet_GBP_2017-04-27 | 2 / 2 / 2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| T_FWP_TermSheet_EUR_2025-03-24 | 3 / 3 / 3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| T_FWP_TermSheet_EUR_GBP_2026-07-27 | 5 / 5 / 5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| **All 10 deals** | | 27/27 | 27/27 | 26/26 | 27/27 | 26/26 | 22/26 | 18/26 | 27/27 | 27/27 |

Extracted spread on fixed-rate bonds: {'missing': 4, 'benchmark': 18, 'mid-swaps': 4}
```

### streamlit run

```
Collecting usage statistics. To deactivate, set browser.gatherUsageStats to false.

2026-10-13 13:07:24.569 Uvicorn server started on :::8501

  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://172.27.178.62:8501
  External URL: http://150.210.231.127:8501

  Detected WSL. Using poll-based file watching for better compatibility. To force watchdog, set server.fileWatcherType = "watchdog".
  Stopping...
```

### git log --oneline master..non-usd-display

```
b509da0 feat: rename size column in non-usd excel export
09f3704 feat: name currency in deal line and picker
419d0f1 feat: format benchmark and size in table
f58a381 feat: filter search currencies and fix bond count
068db68 feat: extract currency per bond from principal
c145d53 docs: record v2b prompt trial and keep old prompt
861ee80 chore: restore prompt v2 for trial run
03fe382 docs: hand off non-dollar milestone to agy
fa17dfd chore: log benchmark runs from prompt trials
9bb508d docs: record prompt trial results on both deal sets
53c291a fix: forbid joining benchmark text from two places
47cde46 feat: ask for the spread over the government bond
82f6908 docs: plan prompt change for government spreads
2bbbdb4 fix: keep spread decimals and skip Common Codes
1673aae test: score baseline extraction on non-dollar set
b4d60b4 docs: plan non-dollar display milestone
```

### git diff --stat master

```
 .claude/plans/non-usd-display.plan.md              | 112 ++++++++++++++++
 .claude/plans/non-usd-prompt.plan.md               |  82 ++++++++++++
 .claude/prds/non-usd-deals.prd.md                  |   2 +-
 app.py                                             | 133 ++++++++++++++----
 data/fixtures/attempts.jsonl                       |  13 ++
 data/test_set/README.md                            |  49 +++++++
 ..._FWP_TermSheet_EUR_2025-02-05_extractions.jsonl |   1 +
 ..._FWP_TermSheet_EUR_2026-01-29_extractions.jsonl |   1 +
 ..._FWP_TermSheet_GBP_2015-07-29_extractions.jsonl |   1 +
 ..._FWP_TermSheet_EUR_2024-05-07_extractions.jsonl |   1 +
 ..._FWP_TermSheet_EUR_2024-08-09_extractions.jsonl |   1 +
 ..._FWP_TermSheet_EUR_2024-04-22_extractions.jsonl |   1 +
 ..._FWP_TermSheet_EUR_2025-10-27_extractions.jsonl |   1 +
 ..._FWP_TermSheet_GBP_2017-04-27_extractions.jsonl |   1 +
 ..._FWP_TermSheet_EUR_2025-03-24_extractions.jsonl |   1 +
 ..._TermSheet_EUR_GBP_2026-07-27_extractions.jsonl |   1 +
 docs/plans/08-non-usd-handoff.md                   | 106 +++++++++++++++
 evaluate.py                                        |   8 +-
 lookup.py                                          | 119 ++++++++++++++++-
 output/accuracy_benchmark_report.md                |   4 +
 score_test_set.py                                  | 148 +++++++++++++++++++++
 structure.py                                       |  61 +++++++--
 tests/test_app_ui.py                               | 109 +++++++++++++++
 tests/test_evaluate.py                             |  23 ++++
 tests/test_lookup.py                               |  77 +++++++++--
 tests/test_score_test_set.py                       |  97 ++++++++++++++
 tests/test_structure.py                            | 106 +++++++++++++++
 tests/test_test_set.py                             |  51 ++++++-
 tests/test_ui.py                                   |  81 ++++++++++-
 ui.py                                              | 106 ++++++++++++---
 30 files changed, 1422 insertions(+), 75 deletions(-)
```
