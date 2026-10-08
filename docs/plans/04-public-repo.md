# Slice 4: Ready the repo to go public

**Implementer**: agy
**Reviewer**: Claude Code
**Branch**: `slice-04-public-repo`, cut from `master` after slice 3 merged (`c34ee52`)
**Due**: 2026-10-20

Read `CONTEXT.md` first and use its terms.

## Goal

The repo goes public on 2026-10-29 and AINA reviewers will read it. Every number a reader sees must match `output/accuracy_benchmark_report.md`. No file may still claim the old 100% results. The highlighted-source view must not be able to run script with access to the app.

## Rules

- Write each test before its code change. Show it failing, then passing.
- Do not commit. Claude commits after review.
- Do not touch: `fields.py`, `extract.py`, `evaluate.py`, `structure.py`, `validate.py`, `fetch.py`, `data/`, `output/`, `CONTEXT.md`, `docs/adr/`, `docs/plans/`.
- No Gemini API calls. No extraction runs.

## Task A: Isolate the highlighted-source view

`lx.visualize` puts `extraction.extraction_text` and `extraction.extraction_class` into a `<script>` JSON literal without escaping `</script>` (see `langextract/visualization.py`, `_prepare_extraction_data`, keys `text` and `class`). `st.iframe` runs an HTML string with same-origin access to the app. A crafted upload can therefore run script in the app's origin.

Fix: load the view from a `data:` URL. A browser gives a `data:` iframe an opaque origin, so its script cannot reach the app.

1. Add `visualization_src(html: str) -> str` to `demo.py`. It returns `"data:text/html;charset=utf-8;base64,"` followed by the base64 of the UTF-8 encoded HTML.
2. In `app.py`, pass `visualization_src(html_content)` to `st.iframe`. Keep `height=600`, since Streamlit cannot measure a cross-origin frame.
3. Tests in `tests/test_demo.py`:
   - the result starts with the prefix above, and decoding the rest gives back the input exactly, including non-ASCII text such as `"€ 1.5bn"`;
   - for an HTML string that contains `</script><script>alert(1)</script>`, the substring `<script>` does not appear in the result.

## Task B: Remove stale handoff files

1. `git rm CLAUDE_REVIEW_HANDOFF.md NEXT_STEPS.md SUBMISSION.md`. The first two are old agent handoffs. `SUBMISSION.md` is replaced by the Google Doc writeup. All three claim 100% accuracy.
2. Move the untracked `FIX_BLOCKER_1_GROUNDING.md`, `FIX_BLOCKER_2_HARDCODED_METRICS.md` and `FIX_BLOCKER_3_PROMPT_LEAKAGE.md` to a new folder `docs/history/`, then `git add` them.
3. Put this line at the top of each moved file, above its first heading:
   `> Historical plan from 2026-09-24, kept as a record of the review. Its numbers come from the one-deal benchmark and are out of date. Current numbers: output/accuracy_benchmark_report.md.`
4. Do not edit anything else in those three files.

## Task C: Add `.env.example`

One line: `GEMINI_API_KEY=`. Check `.gitignore` does not ignore it.

## Task D: Rewrite `README.md`

Keep it under 900 words. Use these sections in this order.

1. **Title and one-paragraph summary.** What it does in plain words: pulls pricing terms for investment-grade corporate bond deals out of SEC term sheets and builds a comps table where every value points back to the exact text it came from.
2. **Results.** Copy the three headline lines from `output/accuracy_benchmark_report.md` exactly (field accuracy, grounded, not-in-source). Then one sentence on the scoring change: first scored at 88.0% (308/350); a CUSIP formatting bug in the comps table was fixed after the run, with no new extraction, which gave 98.3%. Then the per-deal table from the report (deal, tranches, fields, correct, accuracy, grounded). Then 2 to 4 sentences, taken from the report, on what the numbers mean:
   - the 6 misses are all ORCL par call dates the extractor did not return;
   - grounding is low on MSFT (32.2%) and GOOGL (24.3%), whose terms sit in wide tables, and 100% on ORCL; a value that is not grounded is flagged in the app, not hidden;
   - the 2 unmatched GOOGL tranches are floating-rate notes, which the answer key does not score.
3. **How the benchmark was built.** Four deals (AAPL 2025-05-06, MSFT 2017-01-31, ORCL 2025-09-24, GOOGL 2026-08-07). Filings pinned by accession in `fetch.py`. Answer keys written and checked before each deal was run. Each deal run once on Gemini, logged in `data/fixtures/attempts.jsonl`. Prompt collisions are listed in the leakage test (link `CONTEXT.md` for the term). Link `docs/adr/0001-exact-match-grounding.md` for what "grounded" means.
4. **How it works.** One short line per module: `fetch.py`, `fields.py`, `extract.py`, `structure.py`, `validate.py`, `evaluate.py`, `app.py`, `demo.py`. Describe what each does today. Read the code; do not copy the old README.
5. **Run it locally.** Clone URL `https://github.com/dini2-byte/bond-term-sheet-extractor.git`. venv, `pip install -r requirements.txt`, `cp .env.example .env`. Say that `streamlit run app.py` opens the four benchmark deals with no API key, and that a key is only needed for `extract.py` or live upload. List `python3 evaluate.py` to reproduce the report from the committed fixtures, and `python3 -m pytest -q`. Check both commands work on a clean checkout before you write them down.
6. **Limits.** Fixed-rate senior notes only; floating-rate notes are extracted but not scored. Term sheets (FWP) only; prospectus supplements are out of scope. Four deals is a small benchmark. Each deal was run once, so run-to-run variation is not measured. Live upload on the hosted app needs a password so visitors cannot spend the owner's API quota.
7. **Built on.** `google/langextract` (Apache-2.0) and `dgunning/edgartools` (MIT), one line each on what they provide.

Writing rules for the README (a hook enforces them when Claude pushes):
- Use the glossary words from `CONTEXT.md`: grounded, not-in-source, answer key, benchmark, field accuracy, tranche, deal, comps table. Never write "hallucination", "ground truth" or "proprietary".
- No badges. No em dashes or en dashes; use a period, comma, colon or " - ". No Oxford commas (write "a, b and c"). No emoji.
- Never use these words: delve, seamless, robust, leverage, comprehensive, utilize, enhance, streamline, ensures that, showcase, pivotal, crucial, tapestry, testament, meticulous, groundbreaking, cutting-edge, game-changer, empower, vibrant, intricate, embark.
- Plain, short sentences. State facts with numbers. No sales language ("analyst-ready", "production-grade", "non-negotiable").
- No live app link yet. Claude adds it after Aidin deploys.
- No license section and no license badge. Aidin has not picked a license.

## Task E: Check for leftovers

1. `rg -n -i '100\.0%|100%|hallucinat|aidin/bond|cryptographic' --glob '!data/**' --glob '!docs/**' --glob '!output/**' --glob '!.venv/**'` and report every hit. Fix any in files this slice may touch. List the rest.
2. `rg -n '\x{2014}|\x{2013}' README.md` must print nothing.

## Deliverable

Leave changes uncommitted on `slice-04-public-repo`. Report:
1. `git status --short` and `git diff --stat`
2. Failing then passing output for each new test
3. Full `python3 -m pytest -q`
4. Output of `streamlit run app.py --server.headless true` for 15 seconds, showing it starts with no errors or deprecation warnings
5. README word count (`wc -w README.md`) and the output of both Task E commands
6. Anything you were unsure about
