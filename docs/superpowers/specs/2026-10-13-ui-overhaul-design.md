# UI overhaul: a tool, not a demo

**Date**: 2026-10-13
**Status**: approved in brainstorming, waiting for spec review
**Starts after**: slice 8 (`non-usd-display`) is merged to `master`
**Delivered as**: slice 9 (backend) and slice 10 (UI), both implemented by agy and reviewed by Claude

## Why

The AINA form has one field for the project: "Project link or screen recording". Its guidance says "If a practitioner could pick it up and use it tomorrow, you're on the right track." The current page reads as a demo: saved example deals, numbered steps, an accuracy section and a password-locked upload. Aidin's two complaints: it looks generic and it is hard to follow.

The new page behaves like a working tool in the way Hunter does: you land on the input and use it. No examples, no accuracy claims, no walkthrough text on the page. Accuracy numbers move to the README and the writeup. The 4-question video carries the walkthrough.

## Decisions

| Topic | Decision |
|---|---|
| Platform | Stay on Streamlit with a custom theme and CSS |
| Structure | Top bar plus two tabs: Search filings, Upload term sheet |
| Look | Modeled on ramp.com: warm off-white, faint dot grid, near-black text, lime accent, mono labels |
| Dark mode | Yes. Follows the browser by default; a toggle in the top bar overrides it for the visit |
| Examples | None on the page |
| Accuracy | Not on the page. README and writeup only |
| Upload | Open, no password. Shares the run budget. 500 KB limit stays. Never cached |
| Cache | Cloudflare R2, keyed by prompt version and SEC accession number |
| Run budget | Stored in R2 so it survives sleeps and restarts |
| Seeding | The 4 benchmark deals go into the cache under the current prompt version |
| Sleep | Keep-alive GitHub Action every 6 hours |

## Part 1: The page

### Top bar

Left: "Term Sheet Extractor". Right: "How it works" (opens a short `st.dialog`), a GitHub link and the light or dark toggle.

"How it works" holds at most five plain sentences: what a term sheet is, where the filings come from (SEC EDGAR), that each number links to the sentence it came from, that an amber underline means the match is not word for word, and a link to the GitHub README. No accuracy numbers.

### Tab 1: Search filings (default)

Open state:
- Heading "Find a bond deal on SEC EDGAR".
- One line: "Enter a ticker. Get a comps table with every number linked to the filing."
- Ticker input and a lime "Find term sheets" button.
- A mono hint: "N of 20 runs left today · saved results are free".

After a search: a list of matching term sheets, one row each, with filing date, bond count and currency ("Senior notes · 4 bonds in dollars", as built in slice 8). Rows already in the cache carry a small "SAVED" tag.

After a pick: the results view (below).

### Tab 2: Upload term sheet

A file input with the 500 KB check and an "Extract" button. No password. Each upload costs one run from the same budget. The result shows in the same results view. Uploaded files and their extractions are never written to the cache.

### Results view (shared by both tabs)

1. Deal line: issuer, size in the deal's currency, bond count, pricing date.
2. Two columns, about 2:1.
   - Left: the comps table (`st.dataframe`, single-cell selection, same columns and formats as after slice 8, including the Check column). Cells that were extracted but not found word for word get an amber underline or tint. A one-line legend under the table: "Match not exact. Click to check." Then "Download Excel".
   - Right: the source panel for the selected cell. Field and bond in a mono label, the value large, a status tag ("WORD FOR WORD", "NOT EXACT", "NOT IN THE FILING") and the quote from the filing with the value highlighted in lime. Coupon of the first bond is selected on first render.

### Look

Tokens (light / dark):

| Token | Light | Dark |
|---|---|---|
| background | `#FAFAF7` with a `#DCDAD3` dot grid | `#0C0C0B` with a `#1F1F1C` dot grid |
| text | `#111111` | `#F3F2EE` |
| muted text | `#7A7972` | `#8F8E87` |
| card | `#FFFFFF` | `#141413` |
| line | `#E7E5DF` | `#2A2A26` |
| chip | `#F1F0EB` | `#22221F` |
| accent | `#E4F222` (text on it `#111111`) | same |
| warning | `#F5A524` | same |

Fonts: Inter Tight for text, JetBrains Mono for labels, table headers, dates and tags. Lime appears only on the primary button, the selected cell and the source highlight.

### Removed from the page

Saved-deal picker and `list_benchmark_deals`, the password gate and `check_password`, accuracy-report parsing and its sentences, numbered step headings, the "Full filing with highlights" and "Validation details" expanders, and the old serif theme in `.streamlit/config.toml`. The benchmark fixtures stay in `data/fixtures/` for `evaluate.py` and tests.

Page text keeps the slice 6 plain-words table and never-show list, and adds "example", "sample", "demo", "accuracy" and the two headline percentages in `output/accuracy_benchmark_report.md` (field accuracy and found word for word, read from the file at test time) to the never-show list. Page text means visible copy, not module names.

## Part 2: Cache and run budget

### `cache.py`

```python
class ExtractionCache(Protocol):
    def get(self, accession: str) -> str | None: ...   # JSONL text or None
    def put(self, accession: str, jsonl: str) -> None: ...
```

- `R2Cache`: boto3 S3 client pointed at `https://<R2_ACCOUNT_ID>.r2.cloudflarestorage.com`.
- `DiskCache`: a local folder. Used in tests, local runs and whenever the R2 secrets are missing.
- `make_cache(secrets)` picks the backend.
- Object key: `extractions/<prompt_version>/<accession>.jsonl`.
- `prompt_version()`: first 12 hex characters of a SHA-256 over the prompt text, the few-shot examples and the model id. A prompt change therefore starts a fresh cache and old output never shows under a new prompt.
- The value is the same JSONL the extractor writes today, so the results view reads it unchanged.

### Flow on a pick

1. `cache.get(accession)` returns text: render it. No Gemini call, no run charged.
2. It returns None: check the budget, run `extract_terms`, `cache.put`, render.
3. R2 error or an object that does not parse: log it, treat it as a miss. The page never fails because of the cache.

### Run budget

Limits stay: 20 runs per day across the site, 3 per visit. Only real Gemini calls count. `RunBudget` takes a store; the R2 store keeps the day's count in `budget/<YYYY-MM-DD>.json`. Two visitors at the same instant may get one run over the limit. Accepted.

### Secrets

`R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET` in Streamlit secrets and `.env`, listed in `.streamlit/secrets.toml.example` with empty values. Never printed or logged. Aidin creates the bucket and an API token scoped to that bucket only.

### Seeding

A script `seed_cache.py` writes the 4 benchmark fixtures into the cache under the current `prompt_version()`, only if the fixtures were produced by the current prompt (checked against `data/fixtures/attempts.jsonl`). The page does not mention them; they simply load instantly.

### Keep-alive

`.github/workflows/keep-alive.yml`, cron every 6 hours plus manual trigger. It opens the app in headless Chromium, clicks "Yes, get this app back up!" if shown, waits for the "Find term sheets" button and fails the job if it never appears.

## Part 3: Code, tests and rollout

### Code layout

| File | Role |
|---|---|
| `theme.py` (new) | Token dicts for light and dark, `theme_css(mode) -> str`. No Streamlit import |
| `views/search.py` (new) | Tab 1 |
| `views/upload.py` (new) | Tab 2 |
| `views/results.py` (new) | Deal line, table, source panel, Excel button |
| `app.py` | Top bar, tabs, wiring only |
| `cache.py` (new) | Part 2 |
| `lookup.py` | `RunBudget` gains a store |
| `demo.py` | Loses demo-only functions; keeps `check_upload_size`, `get_gemini_api_key`, `save_uploaded_filing` |
| `ui.py` | Unchanged except removals of dead helpers |

### Dark mode risk

`st.dataframe` draws on a canvas, so CSS cannot restyle it, and Streamlit has no public call to switch its theme from a button.

- Plan A: `[theme.light]` and `[theme.dark]` in `config.toml`; the top-bar toggle drives the CSS tokens; table cell colors come from a pandas `Styler` built per mode.
- Plan B, if A looks broken in a real browser: drop the custom toggle and let the theme follow the browser and Streamlit's own settings menu.

Slice 10 starts with a time-boxed spike that checks both plans in a real browser and records which one is used.

### Tests

Written before the code. No network calls.

- `DiskCache` round trip; `get` on a missing key returns None.
- `R2Cache` against a fake client: correct key, correct body, client error becomes a miss.
- `prompt_version` is stable for the same inputs and changes when the prompt changes.
- A cache hit charges no run; a miss charges one; a failed extraction charges none.
- An upload never calls `put`.
- The daily count survives a new `RunBudget` built on the same store.
- `theme_css` contains every token in both modes.
- AppTest: the page opens on the ticker input, both tabs exist, no page text contains a never-show word, no `st.selectbox` of saved deals exists, no password input exists.
- Existing tests keep passing except those that test removed features; each removal is listed in the slice report.

Claude also checks the deployed app in a browser in both modes before merging.

### Rollout

| Slice | Content | Owner | Target |
|---|---|---|---|
| 9 | `cache.py`, budget store, `seed_cache.py`, keep-alive workflow, secrets example | agy; Aidin creates the R2 bucket and token | 2026-10-16 |
| 10 | Theme spike, new layout and tabs, dark mode, removals, README gets the accuracy section | agy | 2026-10-20 |

Each slice gets a plan in `docs/plans/` and a GitHub issue. Claude reviews, browser-checks, merges and pushes. Video stays on 2026-10-27, submission on 2026-10-29.

## Out of scope

Leaving Streamlit, user accounts, a bring-your-own Gemini key, caching uploads, showing accuracy anywhere on the page, new extraction fields.
