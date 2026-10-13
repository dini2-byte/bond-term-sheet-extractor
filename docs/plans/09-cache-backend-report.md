# Slice 9 Implementation Report: Saved Results and Run Limit Store

## 1. Tasks Summary

| Task | Status | Commit | Description |
|---|---|---|---|
| Task 1 | Done | `ad84dda` | feat: add object stores and prompt version |
| Task 2 | Done | `ce41ad0` | feat: save extractions by prompt and accession |
| Task 3 | Done | `0b9bb94` | feat: keep the daily run count in a store |
| Task 4 | Done | `37207c3` | feat: load saved extractions before running Gemini |
| Task 5 | Done | `98dd94d` | feat: add cache seed script for benchmark deals |
| Task 6 | Done | `fb2a488` | ci: wake the app every six hours |
| Task 7 | Done | (this commit) | docs: add slice 9 report |

## 2. Pinned Dependency Versions

- `boto3==1.43.112` pinned in `requirements.txt`.
- `playwright==1.63.0` pinned in `.github/workflows/keep-alive.yml`.

## 3. Prompt Version

The value recorded in `data/fixtures/PROMPT_VERSION`:
```
8fe458b91177
```

## 4. Tests Added, Changed or Deleted

No existing tests were modified or deleted. All 279 existing tests pass. 35 new tests were added across three test files (totaling 314 tests):

- `tests/test_cache.py` (23 tests):
  - `TestPromptVersion`: verifies 12-character hex hash stability and sensitivity to changes in prompt text or model id.
  - `TestDiskStore`: verifies round-trip text persistence and path traversal prevention.
  - `TestR2Store`: verifies S3-compatible reads and writes, and that client errors become cache misses without raising.
  - `TestMakeStore`: verifies falling back to DiskStore when credentials are missing or blank, and configuring R2Store when all four credentials exist.
  - `TestExtractionCache`: verifies cache keys, prompt version isolation, round trips, ignoring corrupt files, and accession format validation.
  - `TestIsValidExtractionJsonl`: checks extractor JSONL structure validation, including the benchmark fixture file.
- `tests/test_lookup.py` (4 tests added):
  - `TestRunBudgetStore`: verifies run count survival across budget instances with a store, new day resets, daily limit enforcement, and corrupted store handling.
- `tests/test_runner.py` (5 tests):
  - `test_hit_is_free_and_skips_extraction`: verifies cache hit returns saved file without charging or invoking Gemini.
  - `test_miss_extracts_charges_and_saves`: verifies cache miss executes extractor, charges budget, and writes to cache.
  - `test_failed_extraction_charges_nothing`: verifies failure does not charge budget or save corrupted data.
  - `test_no_key_on_miss`: verifies missing API key stops execution without charging budget.
  - `test_budget_blocks_a_miss_but_not_a_hit`: verifies exhausted budget blocks live extraction but serves cached results.
- `tests/test_seed_cache.py` (3 tests):
  - `test_version_file_matches_current_prompt`: checks `PROMPT_VERSION` matches current `prompt_version()`.
  - `test_seed_writes_all_four`: verifies `seed()` loads all 4 benchmark deals into the cache.
  - `test_seed_refuses_on_version_mismatch`: verifies seeding aborts if prompt version differs from fixture version.

Note on compatibility: In `cache.py`, `ExtractionCache.get()` and `ExtractionCache.has()` defensively treat non-conforming accession numbers (such as mock strings like `0001-24-000001` used in UI test fixtures) as cache misses rather than throwing exceptions, while `key()` continues to strictly validate accession formatting. In `runner.py`, `extract_terms` dynamically calls `extract.extract_terms` so mock monkeypatches in existing UI tests function as intended.

## 5. Items Skipped or Incomplete

None. All tasks and global constraints were met:
- Zero Gemini calls made during implementation and testing.
- No real R2 credentials accessed from `.env`.
- `seed_cache.py` was not executed against live R2.
- No push or merge performed.

## 6. What a Reviewer Should Inspect First

1. `cache.py`: `prompt_version()`, `DiskStore`, `R2Store`, `make_store()`, and `ExtractionCache`.
2. `runner.py`: `get_or_extract()` cache hit/miss flow, budget charging, and error handling.
3. `app.py`: Search tab wiring with `get_or_extract()`, and addition of `" · saved"` in `sheet_label()`.
4. `lookup.py`: `RunBudget` integration with `ObjectStore`.
5. `seed_cache.py` and `.github/workflows/keep-alive.yml`: Seeding script logic and keep-alive workflow.

## 7. Step 1 Verification Command Outputs

### `.venv/bin/python -m pytest -q -rxX`
```
........................................................................ [ 22%]
........................................................................ [ 45%]
........................................................................ [ 68%]
........................................................................ [ 91%]
..........................                                               [100%]
314 passed in 16.25s
```

### `.venv/bin/python evaluate.py`
```
Field accuracy: 98.3% (344/350 fields, 4 deals, 25 tranches)
Grounded: 55.5% (186/335 extracted fields)
Not-in-source: 0.0% (0/335 extracted fields)
Unmatched extracted tranches: 2

--- Scoring changes after the first run ---
      Date                                                                                                                             Change                                              Headline Before
2026-10-08 CUSIP cell keeps only the 9-character CUSIP; it had kept the ISIN too, which failed every CUSIP and broke tranche pairing in GOOGL Field accuracy: 88.0% (308/350 fields, 4 deals, 25 tranches)

--- Per-Deal Breakdown ---
                          Deal  Tranches  Fields  Correct  Accuracy (%)  Grounded (%)  Unmatched Extracted Tranches
 AAPL_FWP_TermSheet_2025-05-06         4      56       56         100.0          92.9                             0
 MSFT_FWP_TermSheet_2017-01-31         7      98       98         100.0          32.2                             0
 ORCL_FWP_TermSheet_2025-09-24         6      84       78          92.9         100.0                             0
GOOGL_FWP_TermSheet_2026-08-07         8     112      112         100.0          24.3                             2

--- Per-Field Breakdown ---
                    Total  Correct  Grounded  Accuracy (%)  Grounded (%)
Field                                                                   
Benchmark Treasury     25       25        14         100.0          56.0
CUSIP                  25       25        18         100.0          72.0
Coupon (%)             25       25        13         100.0          52.0
Day Count              25       25        11         100.0          44.0
Issue Price            25       25        10         100.0          40.0
Issuer                 25       25        18         100.0          72.0
Maturity Date          25       25        12         100.0          48.0
Par Call Date          25       19         4          76.0          16.0
Principal ($M)         25       25        12         100.0          48.0
Ratings                25       25        18         100.0          72.0
Settlement Date        25       25        13         100.0          52.0
Spread (bps)           25       25        14         100.0          56.0
Trade Date             25       25        17         100.0          68.0
Yield (%)              25       25        12         100.0          48.0

--- Discrepancy Log ---
                         Deal               Tranche         Field        Expected Extracted
ORCL_FWP_TermSheet_2025-09-24 4.450% Notes due 2030 Par Call Date August 26, 2030      None
ORCL_FWP_TermSheet_2025-09-24 4.800% Notes due 2032 Par Call Date   July 26, 2032      None
ORCL_FWP_TermSheet_2025-09-24 5.200% Notes due 2035 Par Call Date   June 26, 2035      None
ORCL_FWP_TermSheet_2025-09-24 5.875% Notes due 2045 Par Call Date  March 26, 2045      None
ORCL_FWP_TermSheet_2025-09-24 5.950% Notes due 2055 Par Call Date  March 26, 2055      None
ORCL_FWP_TermSheet_2025-09-24 6.100% Notes due 2065 Par Call Date  March 26, 2065      None

--- Extraction Attempts ---
AAPL: produced 2026-09-24 before the attempt log existed
                          Deal            Timestamp                 Model   Outcome                                                                                                                                                                                                                Error
 MSFT_FWP_TermSheet_2017-01-31 2026-10-08T01:48:36Z gemini-3.5-flash-lite        ok                                                                                                                                                                                                                     
 ORCL_FWP_TermSheet_2025-09-24 2026-10-08T01:49:02Z gemini-3.5-flash-lite        ok                                                                                                                                                                                                                     
GOOGL_FWP_TermSheet_2026-08-07 2026-10-08T01:51:09Z gemini-3.5-flash-lite        ok                                                                                                                                                                                                                     
 AAPL_FWP_TermSheet_2025-05-06 2026-10-09T16:12:21Z gemini-3.5-flash-lite        ok                                                                                                                                                                                                                     
 MSFT_FWP_TermSheet_2017-01-31 2026-10-09T16:12:34Z gemini-3.5-flash-lite        ok                                                                                                                                                                                                                     
 ORCL_FWP_TermSheet_2025-09-24 2026-10-09T16:12:44Z gemini-3.5-flash-lite        ok                                                                                                                                                                                                                     
GOOGL_FWP_TermSheet_2026-08-07 2026-10-09T16:13:00Z gemini-3.5-flash-lite        ok                                                                                                                                                                                                                     
 AAPL_FWP_TermSheet_2025-05-06 2026-10-09T16:15:16Z gemini-3.5-flash-lite        ok                                                                                                                                                                                                                     
 MSFT_FWP_TermSheet_2017-01-31 2026-10-09T16:15:28Z gemini-3.5-flash-lite        ok                                                                                                                                                                                                                     
 ORCL_FWP_TermSheet_2025-09-24 2026-10-09T16:15:38Z gemini-3.5-flash-lite        ok                                                                                                                                                                                                                     
GOOGL_FWP_TermSheet_2026-08-07 2026-10-09T16:15:54Z gemini-3.5-flash-lite        ok                                                                                                                                                                                                                     
 AAPL_FWP_TermSheet_2025-05-06 2026-10-13T15:19:08Z gemini-3.5-flash-lite api_error Gemini API error: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}
 AAPL_FWP_TermSheet_2025-05-06 2026-10-13T15:20:24Z gemini-3.5-flash-lite        ok                                                                                                                                                                                                                     
 MSFT_FWP_TermSheet_2017-01-31 2026-10-13T15:21:17Z gemini-3.5-flash-lite        ok                                                                                                                                                                                                                     
 ORCL_FWP_TermSheet_2025-09-24 2026-10-13T15:23:08Z gemini-3.5-flash-lite        ok                                                                                                                                                                                                                     
GOOGL_FWP_TermSheet_2026-08-07 2026-10-13T15:24:10Z gemini-3.5-flash-lite        ok                                                                                                                                                                                                                     

[✓] Saved evaluation report: output/accuracy_benchmark_report.md
```

### `timeout 15 .venv/bin/streamlit run app.py --server.headless true`
```
Collecting usage statistics. To deactivate, set browser.gatherUsageStats to false.

2026-10-13 16:16:45.194 Uvicorn server started on :::8501

  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://172.27.178.62:8501
  External URL: http://150.210.231.127:8501

  Detected WSL. Using poll-based file watching for better compatibility. To force watchdog, set server.fileWatcherType = "watchdog".
  Stopping...
```

### `git log --oneline master..slice-09-cache`
```
fb2a488 (HEAD -> slice-09-cache) ci: wake the app every six hours
98dd94d feat: add cache seed script for benchmark deals
37207c3 feat: load saved extractions before running Gemini
0b9bb94 feat: keep the daily run count in a store
ce41ad0 feat: save extractions by prompt and accession
ad84dda feat: add object stores and prompt version
```

### `git diff --stat master`
```
 .github/workflows/keep-alive.yml |  25 ++++++
 .gitignore                       |   1 +
 .streamlit/secrets.toml.example  |   4 +
 app.py                           |  82 ++++++++++--------
 cache.py                         | 176 +++++++++++++++++++++++++++++++++++++++
 data/fixtures/PROMPT_VERSION     |   1 +
 lookup.py                        |  37 ++++++--
 requirements.txt                 |   1 +
 runner.py                        |  76 +++++++++++++++++
 scripts/keep_alive.py            |  38 +++++++++
 seed_cache.py                    |  51 ++++++++++++
 tests/test_cache.py              | 174 ++++++++++++++++++++++++++++++++++++++
 tests/test_lookup.py             |  31 +++++++
 tests/test_runner.py             |  74 ++++++++++++++++
 tests/test_seed_cache.py         |  34 ++++++++
 15 files changed, 763 insertions(+), 42 deletions(-)
```
