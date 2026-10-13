# Plan: Spread Over the Government Benchmark

**Source PRD**: `.claude/prds/non-usd-deals.prd.md`
**Selected Milestone**: 2. Correct non-dollar display (blocking sub-plan: the Task 1 gate in `.claude/plans/non-usd-display.plan.md` failed)
**Complexity**: Small to Medium
**Implementer**: Claude (prompt edits, tests, Gemini runs). Small enough that agy is not needed.

## Summary
After the parser fixes, the extracted spread and benchmark pair correctly on 14 of 22 fixed-rate euro bonds. The 8 misses are prompt problems: in both KO deals Gemini takes the mid-swap spread (listed first), and in IBM 2025-02-05, where four bonds sit side by side in one table, it extracts no spread or benchmark. This plan changes the prompt to always take the spread over the government benchmark and adds one synthetic euro example in a side-by-side table. The new prompt replaces the old one only if the 4 benchmark deals still score at least 344/350 and the test set clears the gate.

## Patterns to Mirror
| Category | Source | Pattern |
|---|---|---|
| Prompt | `fields.py:31` | `PROMPT_DESCRIPTION` numbered instructions, one line per field |
| Few-shot | `fields.py:101` | `lx.data.ExampleData(text=..., extractions=[...])`, synthetic issuer "Acme Corp.", `tranche` attribute on every extraction |
| Example grounding | `tests/test_fields.py:86` | Every `extraction_text` appears verbatim in its example text |
| Leakage | `tests/test_fields.py:120` | No answer-key value appears in prompt or example text |
| Runs | `extract.py:70` | `extract_terms(..., output_dir=...)`; attempts logged to `data/fixtures/attempts.jsonl` |
| Scoring log | `evaluate.py:279` | `data/fixtures/scoring_changes.jsonl` records why reported numbers changed |

## Files to Change
| File | Action | Why |
|---|---|---|
| `fields.py` | UPDATE | `spread_bps` and `benchmark_treasury` lines name the government benchmark and rule out mid-swaps; one line on side-by-side tables; a second few-shot example (`EURO_SAMPLE_TERM_SHEET`) |
| `tests/test_fields.py` | UPDATE | Example grounding for the new example; leakage check also covers the test set key; prompt rule present |
| `evaluate.py` | UPDATE | `run_evaluation(fixtures_dir=FIXTURES_DIR)` so candidate outputs can be scored without touching the saved fixtures |
| `tests/test_evaluate.py` | UPDATE | Test for the `fixtures_dir` parameter |
| `output/prompt-v2/` | CREATE (not committed) | Candidate outputs for the 4 benchmark deals |
| `data/test_set/extractions/` | UPDATE | Replaced with new-prompt outputs if accepted |
| `data/fixtures/*_extractions.jsonl`, `scoring_changes.jsonl` | UPDATE | Only if accepted: new outputs become the fixtures, and the change is logged |
| `data/test_set/README.md`, `README.md` | UPDATE | Results; headline numbers if they move |

## Tasks

### Task 1: Prompt and example, test first
- **Action**:
  - Tests first in `tests/test_fields.py`: the prompt states that `spread_bps` is the spread over the government benchmark and never the spread to mid-swaps; the new example's `spread_bps` text is the benchmark spread line, not the mid-swap line; every example extraction is verbatim in its own text; no test set key value (ISIN, CUSIP, Common Code, benchmark text, size) appears in the prompt or examples.
  - `fields.py`: reword `spread_bps` to "Spread over the benchmark government bond named in benchmark_treasury, in basis points. If the term sheet also gives a spread to mid-swaps, ignore it." Reword `benchmark_treasury` to "Government bond the spread is measured against (for example a US Treasury, German Bund or OBL, or UK Gilt)". Add instruction: "When tranches are laid out side by side in columns, take each value from its own tranche's column."
  - New synthetic example: "Acme Corp." euro deal, two tranches side by side in a table, with rows for size, coupon, mid-swap spread, benchmark Bund, spread to Bund, yield, price, ISIN / Common Code / CUSIP. Values invented and checked against both keys by the leakage test.
- **Validate**: `pytest tests/test_fields.py -q`.

### Task 2: Score candidates without overwriting fixtures
- **Action**: Test first: `run_evaluation(fixtures_dir=tmp_dir)` reads deals from that directory. Add the parameter with the current default.
- **Validate**: `pytest tests/test_evaluate.py -q`; `python evaluate.py` still prints 344/350.

### Task 3: Run the new prompt (14 Gemini calls, Aidin approved in advance)
- **Action**: Run the 4 benchmark deals into `output/prompt-v2/` (attempts logged) and the 10 test set deals into a scratch copy. Score with `run_evaluation(fixtures_dir=Path("output/prompt-v2"))` and `score_test_set.py`.
- **Accept when all hold**:
  - Benchmark field accuracy at least 344/350 and not-in-source still 0.
  - Test set: spread and benchmark pair correctly on at least 20 of 22 fixed-rate euro bonds; the 4 sterling bonds stay right; size, coupon, price, yield, maturity and CUSIP stay 27/27 (26/26 where scored).
- **If not accepted**: one more prompt revision is allowed (another 14 calls). If that also fails, keep the old prompt, report, and milestone 2 continues with the 14/22 result shown to Aidin for a decision.
- **Validate**: Both score tables recorded in `data/test_set/README.md`.

### Task 4: Swap in the accepted outputs
- **Action**: If accepted, move the 4 new outputs into `data/fixtures/`, replace `data/test_set/extractions/`, add a `scoring_changes.jsonl` entry ("prompt now takes the spread over the government benchmark"), regenerate the accuracy report and update `README.md` if the headline numbers moved. The live app's accuracy line reads the report, so it follows on its own.
- **Validate**: `pytest -q`; `python evaluate.py`; `python score_test_set.py`; the app's caption shows the new numbers.

### Task 5: Commit, merge, continue milestone 2
- **Action**: Commit on `non-usd-display`, then resume `.claude/plans/non-usd-display.plan.md` from Task 2 (currency column). Note in that plan that the table's spread format `+%d bps` truncates decimals and must change in its Task 4.

## Validation
```bash
.venv/bin/python -m pytest -q -rxX
.venv/bin/python evaluate.py
.venv/bin/python score_test_set.py
```

## Risks
| Risk | Likelihood | Mitigation |
|---|---|---|
| New prompt lowers the 98.3% headline | Medium | Accept only at 344/350 or better; old fixtures untouched until accepted |
| Gemini output varies run to run even at temperature 0 | Medium | A drop of 1 or 2 fields gets one re-run of the old prompt on the same deal to tell noise from a real change, before deciding |
| Grounded % moves, changing a number in the writeup | Medium | Record both runs; update README and tell Aidin before the Oct 24 writeup |
| Euro example teaches a pattern that leaks test set values | Low | Leakage test now checks the test set key too |
| Second example raises prompt cost per call | Low | One short example; flash-lite calls stay small |

## Acceptance
- [ ] Prompt tests pass, no leakage into either key
- [ ] Benchmark at least 344/350, not-in-source 0
- [ ] Euro spread and benchmark pair right on at least 20 of 22 bonds
- [ ] Fixtures swapped only after acceptance, with a scoring change logged
- [ ] Milestone 2 resumes at its Task 2
