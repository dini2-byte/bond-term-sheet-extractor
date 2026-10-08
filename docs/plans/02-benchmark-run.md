# Slice 2: Four-deal benchmark run

**Implementer**: agy (Tasks A-B), Claude (Tasks C-E)
**Reviewer**: Claude Code
**Branch**: `slice-02-benchmark`, cut from `master` after slice 1 merges
**Due**: 2026-10-17
**Status**: blocked on Aidin (see Open decisions)

Read `CONTEXT.md` first and use its terms.

## Goal

Produce the reported numbers: field accuracy, grounded % and not-in-source % across the four benchmark deals (AAPL, MSFT, AMZN, GOOGL). The answer keys for MSFT, AMZN and GOOGL are written and verified before the extractor runs on those deals. Each deal runs once. The first result is the reported result, whatever it is.

## Rules agreed on 2026-10-07

- One extraction run per deal. Re-run only when the API returned no extraction (for example 503 or 429). Never re-run because the output looks wrong.
- Log every attempt, failed or not, and show the log in the benchmark report.
- No change to `fields.py`, `extract.py` prompt logic, `structure.py` or `evaluate.py` scoring after the first run. Fixes found by the run are listed as future work.

## Open decisions (Aidin)

1. **Draft keys verified?** `docs/plans/answer-keys-draft.md` lists every value with its filing line. Aidin checks each one. Pay special attention to the MSFT par call dates: the MSFT filing's table layout is scrambled, so the par call lines were mapped to tranches by date order.
2. **AMZN is a sterling deal.** Sizes are in GBP and the spread is to UK gilts, not Treasuries. Keep it (and add a currency column), or swap it for a USD deal?
3. **GOOGL has two floating-rate tranches.** Floating-rate notes are out of scope. The draft key covers only the 8 fixed-rate tranches. If the extractor returns the floating-rate tranches, they show as unmatched extracted tranches and are not scored. Confirm.

## Task A (agy): Attempt log

1. `extract.py` gets a `--fixture` flag. With it, the JSONL is written to `data/fixtures/<deal>_extractions.jsonl` as well as `output/`.
2. Every run of `extract_terms` appends one line to `data/fixtures/attempts.jsonl`: deal, UTC timestamp, model id, outcome (`ok` or `api_error`) and the error message on failure. Never write the API key.
3. With `--fixture`, refuse to run if the deal's fixture already exists and the last logged attempt for that deal is `ok`. Print why. This enforces the one-run rule.

## Task B (agy): Report shows the attempt log

`evaluate.py` adds an "Extraction attempts" section to the report: one row per attempt from `attempts.jsonl`. The AAPL fixture predates the log; show it as "AAPL: produced 2026-09-24 before the attempt log existed".

## Task C (Claude): Merge the verified keys

Copy the verified deals from `data/answer_key_draft.json` into `data/answer_key.json`. Delete the draft JSON.

## Task D (Claude): Run each deal once

```bash
python3 extract.py data/raw_filings/MSFT_FWP_TermSheet_2017-01-31.txt --fixture
python3 extract.py data/raw_filings/AMZN_FWP_TermSheet_2026-09-09.txt --fixture
python3 extract.py data/raw_filings/GOOGL_FWP_TermSheet_2026-08-07.txt --fixture
python3 evaluate.py
```

## Task E (Claude): Record the result

Commit the fixtures, the attempt log and the regenerated report. Put the headline line in the wiki and the Google Doc writeup.
