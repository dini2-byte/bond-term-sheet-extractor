# Plan: Correct Non-Dollar Display

**Source PRD**: `.claude/prds/non-usd-deals.prd.md`
**Selected Milestone**: 2. Correct non-dollar display
**Complexity**: Medium
**Implementers**: Claude runs Gemini and scores (Tasks 1 and 7). agy writes the code (Tasks 2 to 6) on branch `non-usd-display`; Claude reviews, merges and pushes.

## Summary
Search results in euros and sterling show the right currency, sizes, bond count and benchmark, and other currencies drop out of search. The key choice: **no change to the extraction prompt**. Currency is read from the principal amount text the extractor already returns ("€500,000,000"), so the saved USD deals cannot move off 98.3%. Task 1 runs the extractor on the test set first to confirm that the extracted spread and benchmark are a matching pair; if they are not, the plan stops and a prompt change gets its own plan with a benchmark re-run.

## Decisions (Claude's recommendation; Aidin to confirm)
1. **Column name**: "Treasury" becomes **"Benchmark"** for every deal, as the PRD says. It is the term term sheets use ("Benchmark Security", "Benchmark Bund"). The clash is only with `CONTEXT.md`, which already tells code and docs apart from page text; add a note there instead of a different page label.
2. **Spread column**: one "Spread (bps)" column, always the spread over the bond in the Benchmark column, in every currency. Euro mid-swap spreads are not shown in this milestone (added to the PRD as a deferred item). This keeps each row's spread and benchmark a true pair and keeps comps comparable with US deals.
3. **Size column**: a single-currency deal keeps a numeric column labelled "Size ($M)", "Size (€M)" or "Size (£M)". A mixed deal (AT&T 2026-07-27) gets "Size (M)" with the symbol in each cell.

## Patterns to Mirror
| Category | Source | Pattern |
|---|---|---|
| Naming | `structure.py:14` | `clean_*` functions turn raw extracted text into a normalised value, return `None` when unparsable |
| Table build | `structure.py:383` | One row dict per tranche with display-style column names |
| UI helpers | `ui.py:36` | `TABLE_COLUMNS` holds `(label, source_column, field_class, help_text)`; helpers in `ui.py` stay free of Streamlit |
| Formats | `app.py:391` | `st.column_config.NumberColumn` with a per-column `format` string |
| Lookup | `lookup.py:65` | Pure text functions (`count_bonds`, `is_bond_term_sheet`) used by `find_term_sheets` |
| Errors | `lookup.py:97` | Plain user-facing `LookupError`/`ValueError` text; unknowns return `None`, never guess |
| Tests | `tests/test_test_set.py` | Parametrize over the test set key; `tests/test_lookup.py` class per function; `tests/test_app_ui.py` AppTest with mocked `find_term_sheets` and `extract_terms` |

## Files to Change
| File | Action | Why |
|---|---|---|
| `data/test_set/extractions/*.jsonl` | CREATE | Saved extractor output for the 10 EUR/GBP deals (Task 1) |
| `score_test_set.py` | CREATE | Offline scorer: extractor output vs test set key on currency, size, bond count, benchmark, spread |
| `tests/test_score_test_set.py` | CREATE | Scorer tests |
| `structure.py` | UPDATE | `clean_currency(raw_principal)` and a `Currency` column; internal "Principal ($M)" name kept so `evaluate.py` and the answer key are untouched; export names the size column by currency |
| `lookup.py` | UPDATE | `count_bonds` ignores Common Codes; new `deal_currencies(text)`; `find_term_sheets` adds `currencies` and drops deals outside USD/EUR/GBP |
| `ui.py` | UPDATE | Currency-aware size label, help text and cell display; "Treasury" becomes "Benchmark" |
| `app.py` | UPDATE | Size column format per currency; deal line and picker label name the currency |
| `tests/test_test_set.py` | UPDATE | Drop the strict xfail on bond count once it passes; add currency detection tests |
| `tests/test_structure.py`, `tests/test_lookup.py`, `tests/test_ui.py`, `tests/test_app_ui.py` | UPDATE | New tests per task |
| `CONTEXT.md` | UPDATE | "Currency" term; note that the page's "Benchmark" column means the reference bond |
| `.claude/prds/non-usd-deals.prd.md` | UPDATE | Milestone 2 status; mid-swap spreads added to deferred items |

## Tasks

### Task 1: Baseline run on the test set (Claude, before any code)
- **Action**: With Aidin's OK, run `extract_terms` on the 10 EUR/GBP test set filings (10 Gemini calls, `log_attempt=False`), saving output to `data/test_set/extractions/`. Write `score_test_set.py` and its tests first, then score the baseline. Read which spread and which benchmark the extractor picked for each euro bond.
- **Gate**: If the extracted spread matches `Spread to benchmark (bps)` and the benchmark text matches `Benchmark text` on at least 18 of the 22 fixed-rate euro bonds, continue. Otherwise stop and report; a prompt change gets its own plan and a 4-call benchmark re-run.
- **Validate**: `pytest tests/test_score_test_set.py -q`; baseline table in `data/test_set/README.md`.
- **Outcome, 2026-10-09**: gate failed. After fixing two parser bugs (`clean_spread` decimals, `clean_cusip` Common Codes) the pair is right on 14 of 22. The prompt change is planned in `.claude/plans/non-usd-prompt.plan.md`; Task 2 waits for it. Task 4 must also change the table's spread format `+%d bps`, which truncates decimals.

### Task 2: Currency per bond (agy)
- **Action**: Test first. `structure.clean_currency(raw)` returns "USD" for `$`, "EUR" for `€` or `EUR`, "GBP" for `£` or `GBP`, "JPY" for `¥` or `JPY`, else `None`. `structure_filing_extractions` adds a `Currency` column after `Principal ($M)`. Test on the 4 USD fixtures (all "USD") and on Task 1's saved extractions against the key's `Currency` per bond.
- **Mirror**: `clean_coupon` style at `structure.py:14`.
- **Validate**: `pytest tests/test_structure.py tests/test_test_set.py -q`; `python evaluate.py` still prints 344/350 (98.3%).

### Task 3: Bond count and deal currency in search (agy)
- **Action**: Test first.
  - `count_bonds(text)` counts distinct 9-character tokens that pass the CUSIP check digit and are not the 9 middle characters of an `XS` ISIN in the same text (that is how Common Codes appear). The 11 test set xfails must pass, so remove the marker; the 4 benchmark filings in `data/raw_filings/` must still count their keyed tranche numbers.
  - `deal_currencies(text) -> list[str]`: currencies of principal amounts of 1,000,000 or more, ignoring lines that mention a concurrent offering, use of proceeds, expenses or a credit agreement. Must return the key's `currencies` for all 11 test set deals and `["USD"]` for the 4 benchmark filings and for PG `0001193125-25-251711` (dollar deal that mentions a euro deal; add its text as a test fixture).
  - `find_term_sheets` adds `currencies` to each result and drops results with any currency outside USD, EUR and GBP, or with no currency found. Nothing is shown about dropped deals.
- **Mirror**: `count_bonds` at `lookup.py:65`; fake company class in `tests/test_lookup.py:129`.
- **Validate**: `pytest tests/test_lookup.py tests/test_test_set.py -q -rxX` with no xfail and no XPASS.

### Task 4: Table labels and formats (agy)
- **Action**: Test first.
  - `TABLE_COLUMNS`: "Treasury" becomes "Benchmark", help "The government bond the spread is measured against, such as a US Treasury, German Bund or UK Gilt." Spread help: "Extra yield over the benchmark bond, in basis points (1 bp = 0.01%)." Size help names the deal's currency.
  - New `ui.size_label(currencies)`: "Size ($M)", "Size (€M)", "Size (£M)", or "Size (M)" for more than one currency. `table_frame` uses it; for a mixed deal the size cells become text like "€1,000.0M" and "£550.0M".
  - `_format_cell_display_value` uses the row's currency symbol.
  - `TEXT_COLUMNS` follows the rename.
- **Mirror**: `ui.py:36`, `ui.py:230`.
- **Validate**: `pytest tests/test_ui.py -q`. USD fixtures render exactly as today apart from the "Benchmark" label.

### Task 5: Page text (agy)
- **Action**: Test first.
  - `build_deal_line` uses the currency symbol: "€1bn", "£750m"; a mixed deal reads "€4.1bn and £550m".
  - The search picker label adds the currency for non-USD deals: "Filed 2024-08-09 · 2 bonds in euros". USD labels stay as they are.
  - `app.py` size column format follows `size_label`: NumberColumn with `€%,.1fM` etc. for one currency, text column for mixed.
  - No "not supported", "coming soon" or "not implemented" text anywhere; the app test's banned words list gains these phrases.
- **Mirror**: `app.py:131`, `app.py:279`, `app.py:391`; AppTest flow at `tests/test_app_ui.py:143`.
- **Validate**: `pytest tests/test_app_ui.py -q`.

### Task 6: Excel export (agy)
- **Action**: Test first. `export_comps_to_excel` keeps `Currency` and renames "Principal ($M)" to "Principal (M)" when any row is not USD. USD export unchanged.
- **Validate**: `pytest tests/test_structure.py -q`.

### Task 7: Score, review and ship (Claude)
- **Action**: Review agy's diff. Re-score the saved test set extractions through the new code (no new Gemini calls). Check the PRD metrics: currency 10 of 10 deals, bond count 100%, benchmark label 100%, JPY deal absent from KO/PG/IBM/T search, USD 98.3%. Browser check at 1440px and 390px on the deployed app with one live euro search (1 Gemini call, Aidin's OK). Update `CONTEXT.md`, the PRD and the README results table. Merge `--no-ff`, push.
- **Validate**: Commands below.

## Validation
```bash
.venv/bin/python -m pytest -q -rxX
.venv/bin/python evaluate.py            # 344/350 (98.3%), unchanged
.venv/bin/python score_test_set.py      # every PRD metric at target
```

## Risks
| Risk | Likelihood | Mitigation |
|---|---|---|
| Extractor picks the mid-swap spread for euro bonds | Medium | Task 1 gate stops the plan before any code; prompt change planned separately with a benchmark re-run |
| Extractor drops the € sign from principal text | Low | Task 1 shows it; fall back to `deal_currencies` on the filing text |
| CUSIP check digit rejects a real CUSIP | Low | Tests on all 4 benchmark filings and all 11 test set filings |
| Mixed-currency size column as text sorts by string | Low | Only one deal in the set; numeric column kept for single-currency deals |
| Gemini quota | Low | 10 calls in Task 1, 1 in Task 7; outputs saved so re-scoring needs no calls |
| "Benchmark" label clashes with the glossary | Low | Page text and glossary already differ by design; note it in `CONTEXT.md` |

## Acceptance
- [ ] Task 1 gate passed and recorded
- [ ] Currency, size, bond count and benchmark right for all 10 EUR/GBP test deals
- [ ] JPY deal never appears in search
- [ ] USD deals unchanged apart from the "Benchmark" label; `evaluate.py` still 98.3%
- [ ] No "not supported" wording on the page
- [ ] All tests pass with no xfail left in `tests/test_test_set.py`
