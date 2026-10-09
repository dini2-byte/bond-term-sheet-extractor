# Plan: Non-Dollar Test Set

**Source PRD**: `.claude/prds/non-usd-deals.prd.md`
**Selected Milestone**: 1. Test set
**Complexity**: Small
**Implementer**: Claude Code drafts the key from the filing text, as with the MSFT/ORCL/GOOGL keys. Aidin checks it against the SEC filings.

## Summary
Pick about 10 euro and sterling bond term sheets from SEC EDGAR, using a rule fixed before any values are read. Save their text and hand-key currency, sizes, bond count, identifiers and benchmark for each. Pin the key with tests that tie it to the filing text, and add strict-xfail tests that show today's bond-count bug, so milestone 2 starts from failing tests. Reading the set also answers PRD open questions 1 (mid-swaps) and 3 (euro conventions) and checks the 37% estimate.

No Gemini calls. No extraction runs. EDGAR calls only to scan and fetch.

## Patterns to Mirror
| Category | Source | Pattern |
|---|---|---|
| Naming | `fetch.py:22` | Pinned deals as dicts with `ticker`, `form`, `label`, `accession`; files saved as `{label}_{filing_date}.txt` |
| Data access | `fetch.py:58` | `get_by_accession_number(accession)` then `filing.text()`; errors printed per deal, loop continues |
| Answer key | `data/answer_key.json` | Dict keyed by file stem, one dict per tranche, display-style column names, `null` for not stated |
| Key drafting | `docs/plans/answer-keys-draft.md:1` | Claude drafts before any run, cites the filing line for every value, Aidin confirms |
| Glossary | `CONTEXT.md` | "Answer key" is written before the extractor runs; "Benchmark" is the scored deal set |
| Tests | `tests/test_fetch.py:38` | `patch("fetch.get_by_accession_number")` so tests make no network calls |
| Tests | `tests/test_lookup.py:28` | Class per function under test, short inline filing text |

## Files to Change
| File | Action | Why |
|---|---|---|
| `fetch.py` | UPDATE | Add `TEST_SET_DEALS` and a `deals` parameter to `fetch_filings` (default `DEALS_TO_FETCH`, so the benchmark fetch is unchanged) |
| `data/test_set/raw/*.txt` | CREATE | Saved filing text for each picked deal |
| `data/test_set/answer_key.json` | CREATE | Hand-keyed values, apart from the benchmark key so `evaluate.py` and the 98.3% are untouched |
| `data/test_set/README.md` | CREATE | Selection rule, picked accessions, line citations, currency hand check, answers to open questions 1 and 3 |
| `tests/test_test_set.py` | CREATE | Key schema and verbatim checks, plus strict-xfail tests for the bond-count bug |
| `tests/test_fetch.py` | UPDATE | Test for `TEST_SET_DEALS` and the `deals` parameter |
| `CONTEXT.md` | UPDATE | Add "Test set": hand-keyed deals that check one feature and are not in reported numbers |
| `.claude/prds/non-usd-deals.prd.md` | UPDATE | Milestone 1 status and plan path; tick answered open questions |

## Tasks

### Task 1: Fix the selection rule before reading any values
- **Action**: Write the rule into `data/test_set/README.md` first. Scan the latest 25 FWP filings for KO, PG, IBM, T, AAPL, CAT and MCD with `lookup.find_term_sheets`. Tag each result's currency from the first page by regex. Pick the 2 newest EUR term sheets each from KO, PG, IBM and T (8), every GBP term sheet up to 3, and 1 JPY term sheet as the "leave out of search" case. If fewer than 2 GBP exist, widen the scan to 50 filings for the same tickers and record that.
- **Mirror**: The 2026-10-09 scan that found 44 of 118.
- **Validate**: README lists the rule, scan date and every candidate accession before any key value is written.

### Task 2: Check the 37% estimate
- **Action**: Open the first page of 10 regex-tagged non-dollar results and 10 regex-tagged dollar results, picked by a fixed rule (every 4th result in scan order). Record the true currency of each and the regex error rate.
- **Validate**: README has a 20-row table: accession, regex currency, hand-checked currency.

### Task 3: Fetch the picked filings
- **Action**: Test first in `tests/test_fetch.py`: `fetch_filings(deals=fetch.TEST_SET_DEALS, output_dir=tmp_path)` calls `get_by_accession_number` once per test set deal and saves each file; the default call still fetches only the 4 benchmark deals. Then add `TEST_SET_DEALS` (labels like `KO_FWP_TermSheet_EUR`) and the `deals` parameter. Run once to save files to `data/test_set/raw/`.
- **Mirror**: `fetch.py:22` list shape, `tests/test_fetch.py:38` mocking.
- **Validate**: `pytest tests/test_fetch.py -q`; file count in `data/test_set/raw/` equals `len(TEST_SET_DEALS)`.

### Task 4: Draft the answer key
- **Action**: For each deal, read the filing and write one entry keyed by file stem: `currency` (ISO code), `bond_count` and one dict per bond with `Tranche`, `Size (M)` in the deal's own currency, `Coupon (%)`, `Benchmark kind` (`US Treasury`, `Bund`, `Gilt`, `Mid-swaps` or `None`), `Benchmark text` and `Spread text` copied verbatim, `Day Count`, `Coupon frequency`, `ISIN`, `Common Code` and `CUSIP` (`null` when the filing has none). Cite the filing line for each value in the README. Key from the filing only.
- **Mirror**: `data/answer_key.json` shape, `docs/plans/answer-keys-draft.md` citations.
- **Validate**: Task 5 tests pass. Aidin checks the key against the filings and confirms or corrects.

### Task 5: Pin the key with tests
- **Action**: `tests/test_test_set.py`:
  - Every key entry has a raw file and every raw file has a key entry.
  - `bond_count == len(bonds)` and every bond has every field.
  - Every non-null text value (`Benchmark text`, `Spread text`, `ISIN`, `Common Code`, `CUSIP`) appears verbatim in the raw file.
  - `currency` is one of `EUR`, `GBP`, `JPY`, with at least 6 EUR and 2 GBP deals.
  - Strict xfail, reason "milestone 2": `lookup.count_bonds(text) == bond_count` for each deal. Today Common Codes inflate the count (KO showed 4 for 2 bonds).
- **Mirror**: `tests/test_lookup.py` style; `pytest.mark.parametrize` over key entries.
- **Validate**: `pytest tests/test_test_set.py -q -rxX` shows passes plus expected xfails and no XPASS.

### Task 6: Answer open questions 1 and 3
- **Action**: From the keyed deals, write in the README how many quote a spread over mid-swaps, over a government bond or no spread; and which day counts and coupon frequencies appear. Run the `validate.py` checks on the key values (not on extractor output) to see whether euro conventions alone trip any rule.
- **Validate**: PRD open questions 1 and 3 ticked with a one-line answer each, pointing to the README.

### Task 7: Glossary, PRD and commit
- **Action**: Add "Test set" to `CONTEXT.md`. Set milestone 1 to `complete` in the PRD once Aidin confirms the key. Commit on branch `non-usd-test-set`, merge `--no-ff` to master, push.
- **Validate**: Full test run below.

## Validation
```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest tests/test_test_set.py -q -rxX
git diff --stat master
```

## Risks
| Risk | Likelihood | Mitigation |
|---|---|---|
| Fewer than 2 GBP term sheets in the 7 tickers | Medium | Rule widens the scan to 50 filings; record any shortfall instead of picking by hand |
| Euro term sheets state no benchmark | Medium | `Benchmark kind: None` is a valid answer and feeds the milestone 2 display question |
| "Benchmark" already means the scored deal set in `CONTEXT.md` | High for milestone 2 | Flag now; milestone 2 picks a page label that does not clash, or renames the glossary term |
| Filing over the 60,000-char search limit | Low | Such deals never reach search; the rule skips them and takes the next newest |
| Aidin's check takes time before Oct 24 writeup | Medium | Key is small (about 25 bonds); README cites lines so each check is one lookup |

## Acceptance
- [ ] Selection rule written before any key value
- [ ] About 10 EUR and GBP deals plus 1 JPY deal fetched and keyed
- [ ] 37% estimate checked on 20 filings
- [ ] Open questions 1 and 3 answered
- [ ] All tests pass; bond-count tests xfail strictly
- [ ] Benchmark answer key, `evaluate.py` and the 98.3% untouched
- [ ] Aidin confirmed the key
