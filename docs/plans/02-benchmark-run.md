# Slice 2: Four-deal benchmark run

**Implementer**: agy (Tasks A-B), Claude (Tasks C-E)
**Reviewer**: Claude Code
**Branch**: `slice-02-benchmark`, cut from `master` after slice 1 merges
**Due**: 2026-10-17
**Status**: ready once slice 1 merges

Read `CONTEXT.md` first and use its terms.

## Goal

Produce the reported numbers: field accuracy, grounded % and not-in-source % across the four benchmark deals (AAPL, MSFT, ORCL, GOOGL). The answer keys for MSFT, ORCL and GOOGL are written and verified before the extractor runs on those deals. Each deal runs once. The first result is the reported result, whatever it is.

## Rules agreed on 2026-10-07

- One extraction run per deal. Re-run only when the API returned no extraction (for example 503 or 429). Never re-run because the output looks wrong.
- Log every attempt, failed or not, and show the log in the benchmark report.
- No change to `fields.py`, `extract.py` prompt logic, `structure.py` or `evaluate.py` scoring after the first run. Fixes found by the run are listed as future work.

## Decisions (settled 2026-10-07)

- **AMZN swapped for ORCL.** The AMZN filing is a sterling deal priced off UK gilts. It is replaced by Oracle's 2025-09-24 USD deal (accession 0001193125-25-215807, 6 fixed-rate tranches, rated Baa2 / BBB / BBB), which also widens the credit range of the benchmark. The AMZN raw filing stays in `data/raw_filings/` but is not part of the benchmark.
- **GOOGL floating-rate tranches are not scored.** The key covers the 8 fixed-rate tranches. If the extractor returns the 2 floating-rate tranches, they show as unmatched extracted tranches.
- **Grounded % and not-in-source % divide by fields with an extracted value** (slice 1, Task G7).

- **Draft keys verified.** Aidin checked them against the SEC filings on 2026-10-07 and confirmed them with no corrections.

## Task A (agy): Attempt log

1. `extract.py` gets a `--fixture` flag. With it, the JSONL is written to `data/fixtures/<deal>_extractions.jsonl` as well as `output/`.
2. Every run of `extract_terms` appends one line to `data/fixtures/attempts.jsonl`: deal, UTC timestamp, model id, outcome (`ok` or `api_error`) and the error message on failure. Never write the API key.
3. With `--fixture`, refuse to run if the deal's fixture already exists and the last logged attempt for that deal is `ok`. Print why. This enforces the one-run rule.

## Task A2 (agy): Pin the benchmark filings in `fetch.py`

`fetch.py` downloads the latest filing per ticker, so re-running it silently changes the benchmark. Replace `DEALS_TO_FETCH` with pinned accession numbers and add ORCL:

| Label | Ticker | Form | Accession |
|---|---|---|---|
| AAPL_FWP_TermSheet | AAPL | FWP | look up from the saved file's filing date 2025-05-06 |
| MSFT_FWP_TermSheet | MSFT | FWP | look up from filing date 2017-01-31 |
| ORCL_FWP_TermSheet | ORCL | FWP | 0001193125-25-215807 |
| GOOGL_FWP_TermSheet | GOOGL | FWP | look up from filing date 2026-08-07 |

Fetch by accession number. Re-fetching must produce byte-identical files to the ones in `data/raw_filings/`; check this with `cmp` and report it. Drop the AMZN and 424B2 entries from the list.

## Task B (agy): Report shows the attempt log

`evaluate.py` adds an "Extraction attempts" section to the report: one row per attempt from `attempts.jsonl`. The AAPL fixture predates the log; show it as "AAPL: produced 2026-09-24 before the attempt log existed".

## Task C (Claude): Merge the verified keys

Copy the verified deals from `data/answer_key_draft.json` into `data/answer_key.json`. Delete the draft JSON.

## Task D (Claude): Run each deal once

```bash
python3 extract.py data/raw_filings/MSFT_FWP_TermSheet_2017-01-31.txt --fixture
python3 extract.py data/raw_filings/ORCL_FWP_TermSheet_2025-09-24.txt --fixture
python3 extract.py data/raw_filings/GOOGL_FWP_TermSheet_2026-08-07.txt --fixture
python3 evaluate.py
```

## Task E (Claude): Record the result

Commit the fixtures, the attempt log and the regenerated report. Put the headline line in the wiki and the Google Doc writeup.

## Task A3 (agy): An empty result is not a successful run

If `lx.extract` returns without raising but with zero extractions, the API returned nothing usable. In that case `extract_terms` must log the attempt with outcome `api_error` and error `"no extractions returned"`, must not write the fixture (or the `output/` JSONL), and must raise `RuntimeError` with that message. A later `--fixture` run for that deal is then allowed. Test it with a mocked `lx.extract` that returns a document with an empty `extractions` list.

## Result of the first run (2026-10-08)

Field accuracy 88.0% (308/350), grounded 55.8% (183/328), not-in-source 0.0%. Of the 42 misses, 36 came from a scorer bug: the comps-table CUSIP cell kept the ISIN (`594918 BV5 / US594918BV54`), so every CUSIP scored wrong, and in GOOGL the broken CUSIP pairing fell back to maturity date and paired the fixed 2028 and 2029 notes with the floating-rate notes of the same maturity. The other 6 are real extraction misses: the extractor returned no par call date for any ORCL tranche.

Aidin decided on 2026-10-08 to fix the CUSIP cell (no new extraction, fixtures unchanged) and to report both numbers.

## Task E2 (agy): CUSIP cell holds only the CUSIP

1. In `structure.py`, the comps-table `CUSIP` value is the first 9-character CUSIP in the extracted text: 6 alphanumerics, optional whitespace, 3 alphanumerics, returned uppercase with whitespace removed. `594918 BV5 / US594918BV54` gives `594918BV5`. `68389XDH5 / US68389XDH52` gives `68389XDH5`. `02079K CL9 / US02079KCL98` gives `02079KCL9`. Text with no CUSIP gives `None`. The raw text stays in the audit record.
2. Do not change the CUSIP scoring rule or anything else in `evaluate.py` scoring.
3. Add `data/fixtures/scoring_changes.jsonl` with one line: `{"date": "2026-10-08", "change": "CUSIP cell keeps only the 9-character CUSIP; it had kept the ISIN too, which failed every CUSIP and broke tranche pairing in GOOGL", "headline_before": "Field accuracy: 88.0% (308/350 fields, 4 deals, 25 tranches)"}`.
4. `evaluate.py` adds a section "Scoring changes after the first run" to the console output and the report, one row per line of that file, placed right after the headline lines. If the file is missing, omit the section.
5. Do not touch any file in `data/fixtures/` other than creating `scoring_changes.jsonl`. Make no Gemini API call.
6. Regenerate the report with `python3 evaluate.py`.
