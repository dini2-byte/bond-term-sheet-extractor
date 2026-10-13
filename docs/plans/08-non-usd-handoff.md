# Slice 8 handoff: finish non-dollar deals on your own

**Implementer**: agy, working alone from start to finish
**Reviewer**: Claude Code, after you finish (high-level review, then merge and push)
**Branch**: `non-usd-display` (already exists, 8 commits ahead of `master`). Stay on it.
**Hard deadline context**: the AINA writeup is due 2026-10-24. Finish well before that.

## Read first, in this order

1. `CONTEXT.md`: project terms. Use them in code, tests and docs.
2. `.claude/prds/non-usd-deals.prd.md`: the problem, the MVP and the metrics.
3. `.claude/plans/non-usd-display.plan.md`: milestone 2, Tasks 2 to 6 are yours.
4. `.claude/plans/non-usd-prompt.plan.md`: the prompt change and its acceptance rules.
5. `data/test_set/README.md`: how the test set was built, the baseline and the prompt trial results.
6. `docs/plans/06-friendly-page.md`: the plain-words table and the "never show" list for page text.

## Where things stand

- The test set is done: 11 hand-keyed deals in `data/test_set/` (8 euro, 2 sterling, 1 yen; one AT&T deal mixes euro and sterling). The key is confirmed by Aidin. Never edit `data/test_set/answer_key.json` or `data/test_set/raw/`.
- `score_test_set.py` scores saved extractor output against that key. It makes no Gemini calls.
- Fixed on this branch: `clean_spread` keeps decimals, `clean_cusip` skips Common Codes. Benchmark still 344/350.
- `evaluate.run_evaluation(fixtures_dir=..., report_path=...)` scores a candidate folder without touching `output/accuracy_benchmark_report.md`.
- The prompt is undecided. Two trials, one run each:

| | Old prompt (`master`) | v2 (`47cde46`) | v3 (`53c291a`, current branch) |
|---|---|---|---|
| Benchmark field accuracy | 344/350 | 349/350 | 344/350 |
| Not in the filing | 0 | 1 (GOOGL 2066 benchmark year) | 0 |
| Euro spread and benchmark pair right | 14/22 | 22/22 | 19/22 |
| Found word for word | 55.5% | 50.1% | 48.4% |

## Rules

- Write each test before its code change. Show it failing, then passing.
- Commit on `non-usd-display` after each step below. Do not push. Do not merge to `master`. Claude does both after review.
- Commit messages: imperative subject of 50 characters or fewer with a Conventional Commits prefix (`feat:`, `fix:`, `test:`, `docs:`, `chore:`), no em or en dashes, no Oxford commas, no AI attribution or co-author lines of any kind. A hook rejects commits that break these rules; fix the message and retry, never bypass it.
- Never print, log or copy the Gemini API key. It is read from `.env`.
- Gemini budget for the whole handoff: **14 calls** (Step 1). No other extraction runs. Tests make no network calls.
- Never edit `data/answer_key.json`, `data/test_set/answer_key.json`, `data/raw_filings/` or `data/test_set/raw/`.
- Only replace `data/fixtures/*_extractions.jsonl` as Step 1 allows, and log it in `data/fixtures/scoring_changes.jsonl`.
- Page text: no "not supported", "coming soon", "not implemented" or "unavailable" wording anywhere. Follow the plain-words table and never-show list from slice 6.
- All existing tests must keep passing. If a test must change, say which and why in the report.
- If something in this document turns out to be wrong or impossible, stop that step, write what you found in the report and move to the next step that does not depend on it.

## Step 1: Settle the prompt (14 Gemini calls)

1. Put the v2 prompt back: `git show 47cde46:fields.py > fields.py`, and delete `test_prompt_forbids_joining_text_from_different_places` from `tests/test_fields.py`. Run `pytest tests/test_fields.py -q`. Commit.
2. Run v2 once more, exactly as the earlier trials did: the 4 benchmark deals (`data/raw_filings/<deal>.txt` for each deal in `data/answer_key.json`) into `output/prompt-v2b/` with `log_attempt=True`, and the 10 test set filings except the JPY one into `output/prompt-v2b-testset/` with `log_attempt=False`. Use `extract_terms(path, log_attempt=..., output_dir=...)`.
3. Score both:
   - `run_evaluation(fixtures_dir=Path("output/prompt-v2b"), report_path=Path("output/prompt-v2b/report.md"))`
   - the test set with the functions in `score_test_set.py` over `output/prompt-v2b-testset/`; count euro fixed-rate bonds where both Spread and Benchmark score True.
4. **Accept v2** only if all of these hold for v2b:
   - benchmark field accuracy at least 344/350;
   - not-in-source exactly 0;
   - euro spread and benchmark pair right on at least 20 of 22;
   - size, coupon, price, yield, maturity and CUSIP on the test set no worse than the old prompt (all right).
5. If accepted: copy the 4 v2b benchmark outputs over `data/fixtures/`, copy the 10 test set outputs over `data/test_set/extractions/`, add a line to `data/fixtures/scoring_changes.jsonl` in the existing format saying the prompt now takes the spread over the government bond (dated the day of the run), run `python evaluate.py` to regenerate `output/accuracy_benchmark_report.md`, and update the headline numbers in `README.md` to match the new report.
6. If not accepted: restore the old prompt with `git show master:fields.py > fields.py` and `git show master:tests/test_fields.py > tests/test_fields.py`, keep every fixture as it is and continue with Step 2. The KO mid-swap problem then stays open; say so in the report.
7. Either way, add the v2b row to the trial table in `data/test_set/README.md` and commit (`data/fixtures/attempts.jsonl` included). Do not commit anything under `output/prompt-*`.

## Step 2: Currency per bond

Task 2 of `.claude/plans/non-usd-display.plan.md`. `structure.clean_currency(raw)` and a `Currency` column after `Principal ($M)`. Keep the internal column name `Principal ($M)` so `evaluate.py` and the answer key do not change. Afterwards `python score_test_set.py` must show Currency 27/27, and `python evaluate.py` must print the same field accuracy as before this step.

## Step 3: Bond count and currency in search

Task 3 of the same plan.
- `count_bonds` counts 9-character tokens that pass the CUSIP check digit and are not the 9 middle characters of an `XS` ISIN. Remove the strict `xfail` from `test_count_bonds_matches_key` in `tests/test_test_set.py`; all 11 must pass. Add a test that the 4 benchmark filings in `data/raw_filings/` still count their keyed tranche numbers.
- `deal_currencies(text)`: currencies of principal amounts of 1,000,000 or more, ignoring lines about a concurrent offering, use of proceeds, expenses or a credit agreement. Must match the key's `currencies` on all 11 test set filings and return `["USD"]` for the 4 benchmark filings. The PG dollar deal that mentions a euro deal (`0001193125-25-251711`) is not saved locally; build a short inline test text from the same pattern ("Concurrent Offering: €500,000,000 of ... Notes") instead of fetching it.
- `find_term_sheets` adds `currencies` to each result and silently drops results with a currency outside USD, EUR and GBP or with no currency found.

## Step 4: Table labels and formats

Task 4 of the same plan, plus one fix found during the trials: the table's spread column uses `format="+%d bps"` in `app.py`, which cuts "+108.2" to "+108". Show decimals when a spread has them and keep whole numbers looking exactly as today ("+25 bps"). If a single NumberColumn format cannot do both, make the spread a text column built by the same rule as `ui._format_cell_display_value`, and test it.

## Step 5: Page text

Task 5 of the same plan: currency in the deal line ("€1bn", "€4.1bn and £550m") and in the search picker ("Filed 2024-08-09 · 2 bonds in euros"), size column format per currency, and the new banned phrases in `tests/test_app_ui.py`. Dollar deals must read exactly as they do today apart from the "Benchmark" column label.

## Step 6: Excel export

Task 6 of the same plan.

## Step 7: Final checks and report

Run all of these and paste the output into the report:

```bash
.venv/bin/python -m pytest -q -rxX
.venv/bin/python evaluate.py
.venv/bin/python score_test_set.py
timeout 15 .venv/bin/streamlit run app.py --server.headless true
git log --oneline master..non-usd-display
git diff --stat master
```

Then write `docs/plans/08-non-usd-report.md` (commit it) with:

1. Step 1 outcome: the v2b numbers, whether v2 was accepted and which fixtures changed.
2. PRD metrics against targets: currency right on the 10 EUR and GBP deals, bond count right on all 11, benchmark right, JPY deal absent from search, benchmark field accuracy.
3. Every headline number that changed (field accuracy, found word for word, not in the filing) with old and new values. Aidin's writeup quotes these.
4. Every test you added, changed or deleted, and why.
5. Anything you were unsure about, skipped or could not do, and any rule in this document you could not follow.
6. What a reviewer should look at first.

Then stop. Claude reviews the branch, checks the deployed app in a browser, merges and pushes.
