# Slice 10: The page as a tool

> **For agentic workers:** work task by task, in order. Steps use checkbox (`- [ ]`) syntax for tracking.

**Implementer**: agy, working alone from start to finish
**Reviewer**: Claude Code (review, browser check in light and dark, merge and push)
**Branch**: `slice-10-ui`, cut from current `master` (after the commit that adds this plan)
**Target**: 2026-10-20
**Spec**: `docs/superpowers/specs/2026-10-13-ui-overhaul-design.md`, Parts 1 and 3

**Goal:** The page opens on a ticker search, works like a tool (no saved-deal picker, no password, no accuracy text), looks like the spec's Ramp-style design in both light and dark mode, and shares one results view between the Search and Upload tabs.

**Architecture:** `app.py` keeps only the top bar, the two tabs and the cached store, budget and cache objects. Each tab lives in `views/`, and both tabs call `views/results.py` to draw the deal line, comps table, source panel and Excel button. Colors live in `.streamlit/config.toml` as Streamlit's own `[theme.light]` and `[theme.dark]`; `theme.py` holds the same tokens plus CSS that uses only colors that work in both modes.

**Tech Stack:** Python 3.12, Streamlit 1.64, pandas Styler, pytest with `streamlit.testing.v1.AppTest`.

## Decisions made before this plan (from a browser spike on 2026-10-13)

- **Dark mode is Plan B from the spec, with native theming.** With `[theme.light]` and `[theme.dark]` in `config.toml`, Streamlit follows the browser setting and redraws everything in the right colors, including the `st.dataframe` canvas. A pandas Styler tint with transparency (`rgba(245, 165, 36, 0.22)`) reads well in both modes. But `st.context.theme.type` does not update when the visitor switches theme in Streamlit's settings menu until the next rerun, so any color picked in Python goes stale. Therefore: **no custom light/dark toggle**, and **custom CSS never picks a color per mode**. It uses the accent, the warning color, `currentColor`, `opacity` and gray with transparency only. Visitors switch theme from Streamlit's own menu (top right, then Settings).
- The spec's per-mode dot-grid colors become one gray with transparency that works on both backgrounds.
- The primary button text must be set to `#111111` in CSS; Streamlit draws it white on the lime accent otherwise.
- When the store is local disk (no R2 secrets), the app seeds the 4 benchmark extractions into it at startup, so those deals show `SAVED` and open without a run even before R2 is set up.
- A saved filing opens as soon as it is picked. An unsaved one needs a button press ("Extract · uses 1 run") so a stray click never spends a run.
- An upload costs one run and is never written to the cache. `demo.save_uploaded_filing` is removed because the runner writes the filing itself.

## Read first, in this order

1. `CONTEXT.md`: project terms.
2. The spec, Parts 1 and 3. Part 2 is done (slice 9).
3. `app.py` as it is now, `ui.py` (`table_frame`, `not_exact_mask`, `cell_source`, `load_document_text`, `TABLE_COLUMNS`, `size_label`, `size_help`), `runner.py`, `cache.py`, `seed_cache.py`, `tests/test_app_ui.py`.

## Global Constraints

- Write each test before its code change. Run it and show it failing, then passing.
- Branch `slice-10-ui` from current `master`. Commit after each task. Do not push. Do not merge.
- Commit messages: imperative subject of 50 characters or fewer with a Conventional Commits prefix (`feat:`, `fix:`, `test:`, `docs:`, `chore:`, `refactor:`), no em or en dashes, no Oxford commas, no AI attribution or co-author lines of any kind. A hook rejects commits that break these rules; fix the message and retry, never bypass it.
- **No Gemini calls.** Budget for this slice: 0. Tests make no network calls of any kind (no R2, no EDGAR, no Gemini).
- **Never touch real R2.** Do not read R2 credentials from `.env`, do not run `seed_cache.py` and do not create buckets.
- Never print, log or copy any secret. Log exception type names only.
- Never edit `fields.py`, `extract.py`, `evaluate.py`, `structure.py`, `validate.py`, `data/answer_key.json`, `data/test_set/`, `data/raw_filings/` or any `data/fixtures/*_extractions.jsonl`.
- **Module attributes, not imported names, in `views/`.** Write `lookup.find_term_sheets(...)`, `lookup.get_edgar_identity(...)`, `demo.get_gemini_api_key(...)` and `demo.check_upload_size(...)`, never `from lookup import find_term_sheets`. AppTest reruns `app.py` but keeps `views.*` imported, so a name imported at module level would ignore the tests' monkeypatches.
- Page text (anything a visitor can read) has no emoji, no em or en dashes, none of the never-show words in `tests/test_app_ui.py` and none of: example, sample, demo, accuracy, or the two headline percentages in `output/accuracy_benchmark_report.md`. Module and file names do not count as page text.
- `font-family` may appear only in `theme.py`.
- CSS in `theme.py` uses no hex color except `ACCENT`, `ACCENT_TEXT` and `WARNING`, and no `prefers-color-scheme` media query.
- Existing tests keep passing except the ones this plan says to delete or rewrite. List every deleted or rewritten test in the report with one line saying why.
- If something in this plan turns out wrong or impossible, stop that task, write what you found in the report and continue with the next task that does not depend on it.

## Files

| File | Change | Responsibility |
|---|---|---|
| `tests/conftest.py` | create | every test gets its own disk store and fresh Streamlit caches |
| `cache.py` | modify | `CACHE_DIR_ENV`, `default_disk_root()`; `make_store` uses it |
| `theme.py` | create | tokens, config key map, `theme_css()` |
| `.streamlit/config.toml` | replace | fonts, `[theme.light]`, `[theme.dark]`, toolbar mode |
| `runner.py` | modify | `run_upload`; shared `_run_live` |
| `views/__init__.py` | create | empty |
| `views/results.py` | create | `build_deal_line` (moved from `app.py`), `status_tag`, `source_panel_html`, `column_config_for`, `excel_bytes`, `render_results` |
| `views/search.py` | create | `sheet_label`, `runs_hint`, `cached_find_term_sheets`, `render_search` |
| `views/upload.py` | create | `render_upload` |
| `views/about.py` | create | `GITHUB_URL`, `HOW_IT_WORKS` for the top bar dialog |
| `app.py` | replace | top bar, How it works dialog, tabs, cached store with startup seeding |
| `demo.py` | modify | keep only `MAX_UPLOAD_SIZE_BYTES`, `check_upload_size`, `get_gemini_api_key` |
| `.streamlit/secrets.toml.example` | modify | drop `APP_PASSWORD` |
| `.env.example` | modify | add `EDGAR_IDENTITY=` |
| `README.md` | modify | live app line, file list, run locally, limits |
| `tests/test_theme.py`, `tests/test_views.py` | create | tests |
| `tests/test_cache.py`, `tests/test_runner.py` | modify | new tests |
| `tests/test_app_ui.py` | replace | page tests for the new layout |
| `tests/test_demo.py` | modify | drop tests of removed functions |

---

### Task 1: Tests use their own store

Today the page tests write the daily run count into the repo's real `.cache/` folder; after 20 test runs in a day the extract tests start failing. Fix that first.

**Files:**
- Create: `tests/conftest.py`
- Modify: `cache.py`, `tests/test_cache.py`

**Interfaces:**
- Produces:
  - `cache.CACHE_DIR_ENV: str = "TERM_SHEET_CACHE_DIR"`
  - `cache.default_disk_root() -> Path`: the folder named by `TERM_SHEET_CACHE_DIR`, else `Path(".cache")`
  - `cache.make_store(secrets: Mapping[str, Any] | None, disk_root: Path | None = None) -> ObjectStore` (when `disk_root` is None it uses `default_disk_root()`)
  - pytest fixture `isolated_store` (autouse) returning the `Path` of the test's store folder

- [ ] **Step 1: Write the failing tests** (append to `tests/test_cache.py`)

```python
from cache import CACHE_DIR_ENV, default_disk_root


def test_default_disk_root_reads_the_env(monkeypatch, tmp_path):
    monkeypatch.setenv(CACHE_DIR_ENV, str(tmp_path / "x"))
    assert default_disk_root() == tmp_path / "x"


def test_default_disk_root_falls_back_to_dot_cache(monkeypatch):
    monkeypatch.delenv(CACHE_DIR_ENV, raising=False)
    assert default_disk_root() == Path(".cache")


def test_tests_never_use_the_repo_cache(isolated_store):
    store = make_store({})
    assert isinstance(store, DiskStore)
    assert store.root == isolated_store.resolve()
```

(Add any missing imports, such as `Path`, `make_store` and `DiskStore`, at the top of the file.)

- [ ] **Step 2: Run them and see them fail**

Run: `.venv/bin/python -m pytest tests/test_cache.py -q`
Expected: FAIL with `ImportError: cannot import name 'CACHE_DIR_ENV'`.

- [ ] **Step 3: Implement**

In `cache.py`, add `import os` with the other imports, then above `make_store`:

```python
CACHE_DIR_ENV = "TERM_SHEET_CACHE_DIR"


def default_disk_root() -> Path:
    """Local store folder: TERM_SHEET_CACHE_DIR when set (tests set it), else .cache."""
    return Path(os.environ.get(CACHE_DIR_ENV) or ".cache")
```

Change `make_store` to:

```python
def make_store(secrets: Mapping[str, Any] | None, disk_root: Path | None = None) -> ObjectStore:
    """R2Store when all four R2 secrets are set and non-blank, otherwise DiskStore."""
    values = {name: str((secrets or {}).get(name) or "").strip() for name in R2_SECRET_NAMES}
    if not all(values.values()):
        return DiskStore(disk_root if disk_root is not None else default_disk_root())
    ...  # rest unchanged
```

Create `tests/conftest.py`:

```python
"""Every test gets its own empty disk store and fresh Streamlit caches, and never sees R2 settings."""

from pathlib import Path

import pytest
import streamlit as st

from cache import CACHE_DIR_ENV, R2_SECRET_NAMES


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch) -> Path:
    root = tmp_path / "store"
    monkeypatch.setenv(CACHE_DIR_ENV, str(root))
    for name in R2_SECRET_NAMES:
        monkeypatch.delenv(name, raising=False)
    st.cache_data.clear()
    st.cache_resource.clear()
    return root
```

In `app.py`, `get_store()` already calls `make_store(_secrets())`; it now lands in the test folder with no further change.

- [ ] **Step 4: Run the whole suite**

Run: `.venv/bin/python -m pytest -q`
Expected: all pass (314 plus 3 new).

- [ ] **Step 5: Commit**

```bash
git add cache.py tests/conftest.py tests/test_cache.py
git commit -m "test: give each test its own disk store"
```

---

### Task 2: Theme tokens, config and CSS

**Files:**
- Create: `theme.py`, `tests/test_theme.py`
- Replace: `.streamlit/config.toml`

**Interfaces:**
- Produces:
  - `ACCENT = "#E4F222"`, `ACCENT_TEXT = "#111111"`, `WARNING = "#F5A524"`
  - `NOT_EXACT_TINT = "rgba(245, 165, 36, 0.22)"` (used by the table Styler in Task 4)
  - `TOKENS: dict[str, dict[str, str]]` with keys `"light"` and `"dark"`, each holding `background`, `text`, `muted`, `card`, `line`, `chip`
  - `CONFIG_KEYS: dict[str, str]` mapping a Streamlit theme option to a token name
  - `theme_css() -> str` (plain CSS, no `<style>` tag)

- [ ] **Step 1: Write the failing tests** (`tests/test_theme.py`)

```python
import re
import tomllib
from pathlib import Path

import pytest

from theme import ACCENT, ACCENT_TEXT, CONFIG_KEYS, NOT_EXACT_TINT, TOKENS, WARNING, theme_css

CONFIG = tomllib.loads((Path(__file__).resolve().parent.parent / ".streamlit" / "config.toml").read_text(encoding="utf-8"))


@pytest.mark.parametrize("mode", ["light", "dark"])
def test_config_section_matches_tokens(mode):
    section = CONFIG["theme"][mode]
    assert section["base"] == mode
    assert section["primaryColor"] == ACCENT
    for option, token in CONFIG_KEYS.items():
        assert section[option] == TOKENS[mode][token], option


def test_tokens_match_the_spec():
    assert TOKENS["light"] == {
        "background": "#FAFAF7", "text": "#111111", "muted": "#7A7972",
        "card": "#FFFFFF", "line": "#E7E5DF", "chip": "#F1F0EB",
    }
    assert TOKENS["dark"] == {
        "background": "#0C0C0B", "text": "#F3F2EE", "muted": "#8F8E87",
        "card": "#141413", "line": "#2A2A26", "chip": "#22221F",
    }


def test_fonts_are_inter_tight_and_jetbrains_mono():
    assert CONFIG["theme"]["font"].startswith("'Inter Tight':")
    assert CONFIG["theme"]["codeFont"].startswith("'JetBrains Mono':")


def test_css_uses_only_mode_neutral_colors():
    css = theme_css()
    assert "prefers-color-scheme" not in css
    hexes = {h.upper() for h in re.findall(r"#[0-9A-Fa-f]{6}\b", css)}
    assert hexes <= {ACCENT, ACCENT_TEXT, WARNING}


def test_css_has_the_pieces_the_page_uses():
    css = theme_css()
    for needle in (ACCENT, ACCENT_TEXT, NOT_EXACT_TINT, "JetBrains Mono", "stBaseButton-primary",
                   ".tse-brand", ".tse-hint", ".tse-deal", ".tse-label", ".tse-value", ".tse-tag",
                   ".tse-quote", ".tse-legend", ".tse-muted", "source_panel"):
        assert needle in css, needle
```

- [ ] **Step 2: Run them and see them fail**

Run: `.venv/bin/python -m pytest tests/test_theme.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'theme'`.

- [ ] **Step 3: Implement**

Replace `.streamlit/config.toml` with:

```toml
[theme]
font = "'Inter Tight':https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600;700&display=swap"
codeFont = "'JetBrains Mono':https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap"
baseRadius = "8px"

[theme.light]
base = "light"
primaryColor = "#E4F222"
backgroundColor = "#FAFAF7"
secondaryBackgroundColor = "#FFFFFF"
textColor = "#111111"
borderColor = "#E7E5DF"
dataframeBorderColor = "#E7E5DF"
dataframeHeaderBackgroundColor = "#F1F0EB"
codeBackgroundColor = "#F1F0EB"
codeTextColor = "#7A7972"
linkColor = "#111111"

[theme.dark]
base = "dark"
primaryColor = "#E4F222"
backgroundColor = "#0C0C0B"
secondaryBackgroundColor = "#141413"
textColor = "#F3F2EE"
borderColor = "#2A2A26"
dataframeBorderColor = "#2A2A26"
dataframeHeaderBackgroundColor = "#22221F"
codeBackgroundColor = "#22221F"
codeTextColor = "#8F8E87"
linkColor = "#F3F2EE"

[client]
toolbarMode = "viewer"

[server]
headless = true
enableXsrfProtection = true
```

Create `theme.py`:

```python
"""
Colors and CSS for the page. The light and dark colors live in .streamlit/config.toml as
[theme.light] and [theme.dark]; TOKENS mirrors them so a test keeps the two in step.
The CSS never picks a color per mode: Streamlit can switch theme without a rerun, so it uses
the accent, the warning color, currentColor, opacity and gray with transparency only.
No Streamlit import.
"""

ACCENT = "#E4F222"
ACCENT_TEXT = "#111111"
WARNING = "#F5A524"
NOT_EXACT_TINT = "rgba(245, 165, 36, 0.22)"

TOKENS: dict[str, dict[str, str]] = {
    "light": {
        "background": "#FAFAF7", "text": "#111111", "muted": "#7A7972",
        "card": "#FFFFFF", "line": "#E7E5DF", "chip": "#F1F0EB",
    },
    "dark": {
        "background": "#0C0C0B", "text": "#F3F2EE", "muted": "#8F8E87",
        "card": "#141413", "line": "#2A2A26", "chip": "#22221F",
    },
}

# Streamlit theme option -> token name, for both [theme.light] and [theme.dark].
CONFIG_KEYS: dict[str, str] = {
    "backgroundColor": "background",
    "secondaryBackgroundColor": "card",
    "textColor": "text",
    "borderColor": "line",
    "dataframeBorderColor": "line",
    "dataframeHeaderBackgroundColor": "chip",
    "codeBackgroundColor": "chip",
    "codeTextColor": "muted",
    "linkColor": "text",
}

MONO = "'JetBrains Mono', ui-monospace, monospace"
DOT = "rgba(128, 128, 128, 0.22)"
CHIP = "rgba(128, 128, 128, 0.16)"
LINE = "rgba(128, 128, 128, 0.28)"


def theme_css() -> str:
    return f"""
.block-container {{ max-width: 1180px; padding-top: 1.25rem; padding-bottom: 3rem; }}
.stApp {{ background-image: radial-gradient({DOT} 1px, transparent 1px); background-size: 14px 14px; }}
[data-testid="stDecoration"] {{ display: none; }}
.tse-brand {{ font-weight: 700; font-size: 1.05rem; letter-spacing: -0.03em; }}
.tse-muted {{ opacity: 0.62; }}
.tse-hint, .tse-label, .tse-tag, .tse-legend {{ font-family: {MONO}; }}
.tse-hint {{ font-size: 0.72rem; opacity: 0.62; }}
.tse-deal {{ font-weight: 600; font-size: 1rem; margin: 0.75rem 0 0.25rem 0; }}
.tse-label {{ font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.07em; opacity: 0.62; }}
.tse-value {{ font-size: 1.75rem; font-weight: 700; letter-spacing: -0.02em; margin: 0.15rem 0 0.4rem 0; font-variant-numeric: tabular-nums; }}
.tse-tag {{ display: inline-block; font-size: 0.68rem; letter-spacing: 0.06em; padding: 2px 6px; border-radius: 4px; background: {CHIP}; }}
.tse-quote {{ font-size: 0.9rem; line-height: 1.55; margin-top: 0.9rem; padding-left: 0.6rem; border-left: 2px solid currentColor; }}
mark {{ background: {ACCENT}; color: {ACCENT_TEXT}; padding: 0 2px; border-radius: 2px; }}
.tse-legend {{ font-size: 0.72rem; opacity: 0.75; margin: 0.25rem 0 0.5rem 0; }}
.tse-legend i {{ display: inline-block; width: 14px; height: 10px; background: {NOT_EXACT_TINT}; border-bottom: 2px solid {WARNING}; vertical-align: middle; margin-right: 6px; }}
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primary"] p {{ color: {ACCENT_TEXT} !important; font-weight: 600; }}
[data-baseweb="tab-highlight"] {{ background-color: currentColor !important; }}
[data-testid="stRadio"] [role="radiogroup"] > label {{ width: 100%; padding: 0.5rem 0.75rem; border: 1px solid {LINE}; border-radius: 8px; margin-bottom: 0.25rem; }}
[class*="st-key-source_panel"] {{ backdrop-filter: blur(8px); }}
"""
```

- [ ] **Step 4: Run the tests**

Run: `.venv/bin/python -m pytest tests/test_theme.py -q` then `.venv/bin/python -m pytest -q`
Expected: all pass. `tests/test_app_ui.py::test_css_does_not_override_theme_fonts` still passes because `app.py` is unchanged.

- [ ] **Step 5: Commit**

```bash
git add theme.py tests/test_theme.py .streamlit/config.toml
git commit -m "feat: add light and dark theme tokens"
```

---

### Task 3: Uploads run through the runner

**Files:**
- Modify: `runner.py`, `tests/test_runner.py`

**Interfaces:**
- Consumes: `RunOutcome`, `NO_KEY_MESSAGE`, `FAILED_MESSAGE`, `RunBudget`
- Produces:
  - `run_upload(filing_text: str, stem: str, budget: RunBudget, session_runs: int, api_key: str | None, work_dir: Path, extract_fn: Callable[..., Any] = extract_terms) -> RunOutcome`
  - `get_or_extract` keeps its signature and behavior

- [ ] **Step 1: Write the failing tests** (append to `tests/test_runner.py`)

```python
from runner import run_upload


def test_upload_charges_one_run_and_never_touches_the_cache(tmp_path):
    _, budget, work = setup(tmp_path)
    calls: list = []
    out = run_upload("filing text", "uploaded_term_sheet", budget, 0, "key", work, extract_fn=fake_extractor(calls))
    assert out.charged is True and out.from_cache is False and out.error is None
    assert out.jsonl_path.read_text(encoding="utf-8") == GOOD_JSONL
    assert budget.remaining() == 4
    assert not (tmp_path / "store" / "extractions").exists()
    assert (work / "uploaded_term_sheet.txt").read_text(encoding="utf-8") == "filing text"


def test_failed_upload_charges_nothing(tmp_path):
    _, budget, work = setup(tmp_path)
    out = run_upload("filing text", "uploaded_term_sheet", budget, 0, "key", work, extract_fn=failing_extractor)
    assert out.error == FAILED_MESSAGE and out.charged is False
    assert budget.remaining() == 5


def test_upload_without_key_or_budget_is_blocked(tmp_path):
    _, budget, work = setup(tmp_path)
    assert run_upload("t", "u", budget, 0, None, work, extract_fn=failing_extractor).error == NO_KEY_MESSAGE
    assert "runs for this visit" in run_upload("t", "u", budget, 3, "key", work, extract_fn=failing_extractor).error


def test_extractor_that_writes_nothing_is_a_failure(tmp_path):
    cache, budget, work = setup(tmp_path)
    out = get_or_extract(ACC, "filing", "AAPL_x", cache, budget, 0, "key", work, extract_fn=lambda *a, **k: None)
    assert out.error == FAILED_MESSAGE and out.charged is False
    assert budget.remaining() == 5
```

- [ ] **Step 2: Run them and see them fail**

Run: `.venv/bin/python -m pytest tests/test_runner.py -q`
Expected: FAIL with `ImportError: cannot import name 'run_upload'`.

- [ ] **Step 3: Implement**

Replace everything in `runner.py` from `def get_or_extract(` to the end of the file with:

```python
def _run_live(
    filing_text: str,
    stem: str,
    budget: RunBudget,
    session_runs: int,
    api_key: str | None,
    work_dir: Path,
    extract_fn: Callable[..., Any],
) -> RunOutcome:
    """One real Gemini run. Charges the budget only when the extractor wrote its JSONL."""
    can_run, reason = budget.can_run(session_runs)
    if not can_run:
        return RunOutcome(None, from_cache=False, charged=False, error=reason)
    if not api_key:
        return RunOutcome(None, from_cache=False, charged=False, error=NO_KEY_MESSAGE)

    os.environ["GEMINI_API_KEY"] = api_key
    os.environ["GOOGLE_API_KEY"] = api_key
    work = Path(work_dir)
    filing_path = work / f"{stem}.txt"
    filing_path.write_text(filing_text, encoding="utf-8")
    jsonl_path = work / f"{stem}_extractions.jsonl"
    try:
        extract_fn(filing_path, model_id=MODEL_ID, log_attempt=False, output_dir=work)
    except Exception as e:
        logger.warning("Extraction failed for %s (%s)", stem, type(e).__name__)
        return RunOutcome(None, from_cache=False, charged=False, error=FAILED_MESSAGE)
    if not jsonl_path.is_file():
        logger.warning("Extraction for %s wrote no output", stem)
        return RunOutcome(None, from_cache=False, charged=False, error=FAILED_MESSAGE)

    budget.record_run()
    return RunOutcome(jsonl_path, from_cache=False, charged=True, error=None)


def get_or_extract(
    accession: str,
    filing_text: str,
    stem: str,
    cache: ExtractionCache,
    budget: RunBudget,
    session_runs: int,
    api_key: str | None,
    work_dir: Path,
    extract_fn: Callable[..., Any] = extract_terms,
) -> RunOutcome:
    """A saved extraction when there is one (free), else a live run that is then saved."""
    saved = cache.get(accession)
    if saved is not None:
        jsonl_path = Path(work_dir) / f"{stem}_extractions.jsonl"
        jsonl_path.write_text(saved, encoding="utf-8")
        return RunOutcome(jsonl_path, from_cache=True, charged=False, error=None)

    outcome = _run_live(filing_text, stem, budget, session_runs, api_key, work_dir, extract_fn)
    if outcome.charged and outcome.jsonl_path is not None:
        try:
            cache.put(accession, outcome.jsonl_path.read_text(encoding="utf-8"))
        except ValueError:
            logger.warning("Extractor output for %s was not saved: not valid JSONL", accession)
    return outcome


def run_upload(
    filing_text: str,
    stem: str,
    budget: RunBudget,
    session_runs: int,
    api_key: str | None,
    work_dir: Path,
    extract_fn: Callable[..., Any] = extract_terms,
) -> RunOutcome:
    """A live run on an uploaded term sheet. Never read from or written to the cache."""
    return _run_live(filing_text, stem, budget, session_runs, api_key, work_dir, extract_fn)
```

- [ ] **Step 4: Run the tests**

Run: `.venv/bin/python -m pytest tests/test_runner.py -q` then `.venv/bin/python -m pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add runner.py tests/test_runner.py
git commit -m "feat: run uploads through the run budget"
```

---

### Task 4: Results view

**Files:**
- Create: `views/__init__.py` (empty), `views/results.py`, `tests/test_views.py`
- Modify: `tests/test_app_ui.py` (move one class out)

**Interfaces:**
- Consumes: `NOT_EXACT_TINT` from `theme`; `TABLE_COLUMNS`, `cell_source`, `load_document_text`, `not_exact_mask`, `size_help`, `size_label`, `table_frame` from `ui`; `structure_filing_extractions`; `validate_comps_table`
- Produces:
  - `build_deal_line(df: pd.DataFrame) -> str` (moved unchanged from `app.py`)
  - `STATUS_TAGS: dict[str, str]`, `status_tag(status: str) -> str`
  - `source_panel_html(cs: dict[str, Any]) -> str`
  - `column_config_for(validated_df: pd.DataFrame) -> dict[str, Any]`
  - `excel_bytes(validated_df: pd.DataFrame) -> bytes`
  - `render_results(jsonl_path: Path, key: str, file_stem: str) -> None` (draws into the current container; `key` is `"search"` or `"upload"`)
  - `EMPTY_PANEL_TEXT`, `LEGEND_TEXT`, `DOWNLOAD_LABEL = "Download Excel"`

- [ ] **Step 1: Write the failing tests** (`tests/test_views.py`)

Move the whole `TestBuildDealLine` class out of `tests/test_app_ui.py` into this file, changing each `from app import build_deal_line` to `from views.results import build_deal_line`. Then add:

```python
import pandas as pd

from views.results import (
    STATUS_TAGS, column_config_for, excel_bytes, source_panel_html, status_tag,
)


def test_status_tags():
    assert status_tag("Found word for word") == "WORD FOR WORD"
    assert status_tag("Found, but the match is not exact") == "NOT EXACT"
    assert status_tag("Not in the filing") == "NOT IN THE FILING"
    assert set(STATUS_TAGS.values()) == {"WORD FOR WORD", "NOT EXACT", "NOT IN THE FILING"}


def test_source_panel_escapes_text_and_keeps_the_quote_html():
    cs = {"field": "Coupon", "tranche": "4.000% Notes <2028>", "value": "4.000%",
          "status": "Found word for word", "quote_html": "Coupon: <mark>4.000%</mark>"}
    out = source_panel_html(cs)
    assert "Coupon · 4.000% Notes &lt;2028&gt;" in out
    assert '<div class="tse-value">4.000%</div>' in out
    assert '<span class="tse-tag">WORD FOR WORD</span>' in out
    assert '<div class="tse-quote">Coupon: <mark>4.000%</mark></div>' in out


def test_source_panel_without_quote_has_no_quote_block():
    cs = {"field": "Par call", "tranche": "2030", "value": "Not in the filing",
          "status": "Not in the filing", "quote_html": ""}
    assert "tse-quote" not in source_panel_html(cs)


def test_column_config_uses_the_deal_currency():
    eur = pd.DataFrame({"Currency": ["EUR"]})
    assert "Size (€M)" in column_config_for(eur)
    usd = pd.DataFrame({"Currency": ["USD"]})
    assert "Size ($M)" in column_config_for(usd)


def test_excel_bytes_is_an_xlsx_file():
    data = excel_bytes(pd.DataFrame({"Tranche": ["2028"]}))
    assert data[:2] == b"PK"
```

- [ ] **Step 2: Run them and see them fail**

Run: `.venv/bin/python -m pytest tests/test_views.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'views'`.

- [ ] **Step 3: Implement**

Create empty `views/__init__.py`. Create `views/results.py`:

```python
"""
Results view shared by the Search and Upload tabs: deal line, comps table,
source panel for the selected cell and the Excel download.
"""

from __future__ import annotations

import html
import io
import re
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from structure import structure_filing_extractions
from theme import NOT_EXACT_TINT
from ui import (
    TABLE_COLUMNS,
    cell_source,
    load_document_text,
    not_exact_mask,
    size_help,
    size_label,
    table_frame,
)
from validate import validate_comps_table

STATUS_TAGS = {
    "Found word for word": "WORD FOR WORD",
    "Found, but the match is not exact": "NOT EXACT",
    "Not in the filing": "NOT IN THE FILING",
}
EMPTY_PANEL_TEXT = "Click a number in the table to see where it came from."
LEGEND_TEXT = "Match not exact. Click to check."
DOWNLOAD_LABEL = "Download Excel"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
SIZE_FORMATS = {
    "Size ($M)": "$%,.1fM",
    "Size (€M)": "€%,.1fM",
    "Size (£M)": "£%,.1fM",
    "Size (¥M)": "¥%,.1fM",
}
```

Then paste `build_deal_line` from `app.py` (lines 151-230 today) unchanged, followed by:

```python
def status_tag(status: str) -> str:
    return STATUS_TAGS.get(status, status.upper())


def source_panel_html(cs: dict[str, Any]) -> str:
    """Card for one clicked cell. quote_html is already escaped by ui.source_quote."""
    parts = [
        f'<div class="tse-label">{html.escape(cs["field"])} · {html.escape(cs["tranche"])}</div>',
        f'<div class="tse-value">{html.escape(cs["value"])}</div>',
        f'<span class="tse-tag">{status_tag(cs["status"])}</span>',
    ]
    if cs["quote_html"]:
        parts.append(f'<div class="tse-quote">{cs["quote_html"]}</div>')
    return "".join(parts)


def _currencies(validated_df: pd.DataFrame) -> list[str]:
    if "Currency" not in validated_df.columns:
        return []
    return [c for c in validated_df["Currency"].dropna().unique() if c]


def column_config_for(validated_df: pd.DataFrame) -> dict[str, Any]:
    """Same columns, formats and help text as the old page."""
    curs = _currencies(validated_df)
    current_size_label = size_label(curs)
    config: dict[str, Any] = {}
    for col_label, _, _, col_help in TABLE_COLUMNS:
        if col_label == "Size ($M)":
            fmt = SIZE_FORMATS.get(current_size_label)
            if fmt is None:
                config[current_size_label] = st.column_config.Column(current_size_label, help=size_help(curs))
            else:
                config[current_size_label] = st.column_config.NumberColumn(current_size_label, help=size_help(curs), format=fmt)
        elif col_label in ("Coupon", "Yield"):
            config[col_label] = st.column_config.NumberColumn(col_label, help=col_help, format="%.3f%%")
        elif col_label == "Price":
            config[col_label] = st.column_config.NumberColumn(col_label, help=col_help, format="%.3f")
        else:
            config[col_label] = st.column_config.Column(
                col_label, help=col_help, width="large" if col_label == "Check" else None
            )
    return config


def excel_bytes(validated_df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        validated_df.to_excel(writer, sheet_name="Comps Table", index=False)
    return buffer.getvalue()


def _render_table(validated_df: pd.DataFrame, audit_records: list[dict[str, Any]], key: str) -> tuple[int, str] | None:
    """Draws the comps table and returns the selected (row, column label), if any."""
    tf = table_frame(validated_df)
    mask = not_exact_mask(validated_df, audit_records)

    def tint(data: pd.DataFrame) -> pd.DataFrame:
        styles = pd.DataFrame("", index=data.index, columns=data.columns)
        for col in data.columns:
            if col in mask.columns:
                styles[col] = [f"background-color: {NOT_EXACT_TINT}" if flag else "" for flag in mask[col]]
        return styles

    table_key = f"comps_{key}"
    st.dataframe(
        tf.style.apply(tint, axis=None),
        hide_index=True,
        on_select="rerun",
        selection_mode="single-cell",
        key=table_key,
        column_config=column_config_for(validated_df),
        selection_default={"selection": {"cells": [(0, "Coupon")] if len(tf) > 0 else []}},
    )
    state = st.session_state.get(table_key)
    cells = state.get("selection", {}).get("cells", []) if isinstance(state, dict) else []
    if not cells:
        return None
    row, col = cells[0]
    return int(row), str(col)


def render_results(jsonl_path: Path, key: str, file_stem: str) -> None:
    df, audit_records = structure_filing_extractions(jsonl_path)
    validated_df = validate_comps_table(df, audit_records)
    st.html(f'<div class="tse-deal">{html.escape(build_deal_line(validated_df))}</div>')

    left, right = st.columns([2, 1], gap="medium")
    with left:
        selected = _render_table(validated_df, audit_records, key)
        st.html(f'<div class="tse-legend"><i></i>{html.escape(LEGEND_TEXT)}</div>')
        st.download_button(
            DOWNLOAD_LABEL,
            data=excel_bytes(validated_df),
            file_name=f"{file_stem}_comps_table.xlsx",
            mime=XLSX_MIME,
            key=f"download_{key}",
        )
    with right:
        with st.container(border=True, key=f"source_panel_{key}"):
            cs = None
            if selected is not None:
                cs = cell_source(audit_records, selected[0], selected[1], validated_df, load_document_text(jsonl_path))
            if cs is None:
                st.html(f'<div class="tse-muted">{html.escape(EMPTY_PANEL_TEXT)}</div>')
            else:
                st.html(source_panel_html(cs))
```

The old page read the selection from `st.session_state["comps"]` the same way; if Streamlit 1.64 stores it as an object rather than a dict, read it with `getattr` the way the old code would need to, and say so in the report.

- [ ] **Step 4: Run the tests**

Run: `.venv/bin/python -m pytest tests/test_views.py -q` then `.venv/bin/python -m pytest -q`
Expected: all pass. (`app.py` still has its own `build_deal_line` until Task 6; that is fine for now.)

- [ ] **Step 5: Commit**

```bash
git add views/__init__.py views/results.py tests/test_views.py tests/test_app_ui.py
git commit -m "feat: add shared results view"
```

---

### Task 5: Search and Upload views

**Files:**
- Create: `views/search.py`, `views/upload.py`
- Modify: `tests/test_views.py`, `tests/test_app_ui.py` (delete one class)

**Interfaces:**
- Consumes: `get_or_extract`, `run_upload`, `RunOutcome` from `runner`; `render_results` from `views.results`; `ExtractionCache`; `RunBudget`; module attributes `lookup.find_term_sheets`, `lookup.normalize_ticker`, `lookup.get_edgar_identity`, `lookup.edgar_filing_url`, `demo.get_gemini_api_key`, `demo.check_upload_size`
- Produces:
  - `views.search.sheet_label(item: dict[str, Any], saved: bool) -> str`
  - `views.search.runs_hint(remaining: int, daily_limit: int) -> str`
  - `views.search.SAVED_TAG` equal to the 7 characters `` `SAVED` `` (markdown inline code, drawn as a chip)
  - `views.search.EXTRACT_LABEL = "Extract · uses 1 run"`
  - `views.search.render_search(budget: RunBudget, cache: ExtractionCache, secrets: dict[str, Any] | None) -> None`
  - `views.upload.render_upload(budget: RunBudget, secrets: dict[str, Any] | None) -> None`
  - Session state keys: `session_runs` (int, shared by both tabs), `search_ticker`, `search_pick`, `search_result`, `search_saved_<TICKER>`, `upload_result`

- [ ] **Step 1: Write the failing tests** (append to `tests/test_views.py`)

These replace `TestSearchPickerCurrencyLabel` in `tests/test_app_ui.py`; delete that class there.

```python
from views.search import SAVED_TAG, runs_hint, sheet_label


def _sheet(bond_count, currencies):
    return {"accession": "0001-24-000001", "filing_date": "2024-08-09", "chars": 1, "bond_count": bond_count,
            "currencies": currencies, "text": ""}


def test_sheet_labels_name_the_currency():
    assert sheet_label(_sheet(2, ["EUR"]), saved=False) == "Filed 2024-08-09 · 2 bonds in euros"
    assert sheet_label(_sheet(1, ["GBP"]), saved=False) == "Filed 2024-08-09 · 1 bond in pounds"
    assert sheet_label(_sheet(5, ["EUR", "GBP"]), saved=False) == "Filed 2024-08-09 · 5 bonds in euros and pounds"
    assert sheet_label(_sheet(4, ["USD"]), saved=False) == "Filed 2024-08-09 · 4 bonds"


def test_saved_sheets_carry_the_tag():
    assert sheet_label(_sheet(4, ["USD"]), saved=True) == f"Filed 2024-08-09 · 4 bonds  {SAVED_TAG}"


def test_runs_hint():
    assert runs_hint(18, 20) == "18 of 20 runs left today · saved results are free"
```

- [ ] **Step 2: Run them and see them fail**

Run: `.venv/bin/python -m pytest tests/test_views.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'views.search'`.

- [ ] **Step 3: Implement**

Create `views/search.py`:

```python
"""Search filings tab: find a company's recent bond term sheets on SEC EDGAR, then load or extract one."""

from __future__ import annotations

import html
import logging
import tempfile
from pathlib import Path
from typing import Any

import streamlit as st

import demo
import lookup
from cache import ExtractionCache
from lookup import RunBudget
from runner import RunOutcome, get_or_extract
from views.results import render_results

logger = logging.getLogger(__name__)

HEADING = "Find a bond deal on SEC EDGAR"
SUBLINE = "Enter a ticker. Get a comps table with every number linked to the filing."
PLACEHOLDER = "Ticker, e.g. AAPL"
FIND_LABEL = "Find term sheets"
EXTRACT_LABEL = "Extract · uses 1 run"
SAVED_TAG = "`SAVED`"
PICK_TEXT = "Pick a term sheet to build the comps table."
NOT_SET_UP = "Search is not set up on this deployment."
EDGAR_DOWN = "SEC EDGAR did not respond. Try again in a minute."
CURRENCY_WORDS = {"USD": "dollars", "EUR": "euros", "GBP": "pounds", "JPY": "yen"}


def runs_hint(remaining: int, daily_limit: int) -> str:
    return f"{remaining} of {daily_limit} runs left today · saved results are free"


def sheet_label(item: dict[str, Any], saved: bool) -> str:
    bc = item.get("bond_count", 0)
    bonds = "1 bond" if bc == 1 else f"{bc} bonds"
    unique: list[str] = []
    for c in item.get("currencies", []):
        if c and c not in unique:
            unique.append(c)
    suffix = ""
    if unique and unique != ["USD"]:
        words = [CURRENCY_WORDS.get(c, c.lower()) for c in unique]
        suffix = " in " + (words[0] if len(words) == 1 else f"{', '.join(words[:-1])} and {words[-1]}")
    label = f"Filed {item['filing_date']} · {bonds}{suffix}"
    return f"{label}  {SAVED_TAG}" if saved else label


@st.cache_data(ttl=86400, show_spinner=False)
def cached_find_term_sheets(ticker: str) -> list[dict[str, Any]]:
    return lookup.find_term_sheets(ticker)


def _set_edgar_identity(identity: str) -> None:
    try:
        import edgar
        edgar.set_identity(identity)
    except Exception as e:
        logger.warning("Could not set the EDGAR identity (%s)", type(e).__name__)


def _search_box(budget: RunBudget) -> None:
    box, button = st.columns([4, 1], vertical_alignment="bottom")
    ticker = box.text_input("Ticker", placeholder=PLACEHOLDER, label_visibility="collapsed", key="search_input")
    if button.button(FIND_LABEL, type="primary", key="search_find"):
        st.session_state["search_ticker"] = ticker
        for k in ("search_pick", "search_result"):
            st.session_state.pop(k, None)
    st.html(f'<div class="tse-hint">{html.escape(runs_hint(budget.remaining(), budget.daily_limit))}</div>')


def _find(ticker_raw: str) -> tuple[str, list[dict[str, Any]]] | None:
    try:
        ticker = lookup.normalize_ticker(ticker_raw)
        with st.spinner("Searching SEC EDGAR..."):
            return ticker, cached_find_term_sheets(ticker)
    except (ValueError, LookupError) as e:
        st.error(str(e))
    except Exception as e:
        logger.warning("SEC EDGAR lookup failed (%s)", type(e).__name__)
        st.error(EDGAR_DOWN)
    return None


def _load(sheet: dict[str, Any], ticker: str, saved: bool, budget: RunBudget,
          cache: ExtractionCache, secrets: dict[str, Any] | None) -> RunOutcome:
    message = "Loading the saved result..." if saved else "Extracting with Gemini. This takes about 20 seconds."
    with st.spinner(message):
        return get_or_extract(
            accession=sheet["accession"],
            filing_text=sheet["text"],
            stem=f"{ticker}_{sheet['accession']}",
            cache=cache,
            budget=budget,
            session_runs=st.session_state.get("session_runs", 0),
            api_key=demo.get_gemini_api_key(secrets),
            work_dir=Path(tempfile.mkdtemp()),
        )


def render_search(budget: RunBudget, cache: ExtractionCache, secrets: dict[str, Any] | None) -> None:
    st.header(HEADING, anchor=False)
    st.html(f'<div class="tse-muted">{html.escape(SUBLINE)}</div>')
    identity = lookup.get_edgar_identity(secrets)
    if not identity:
        st.info(NOT_SET_UP)
        return
    _set_edgar_identity(identity)
    _search_box(budget)

    active = st.session_state.get("search_ticker")
    if not active:
        return
    found = _find(active)
    if found is None:
        return
    ticker, sheets = found
    if not sheets:
        st.info(
            f"No bond term sheets in {ticker}'s latest 25 SEC filings. "
            "Banks and brokers file many structured-note filings, which this tool skips."
        )
        st.markdown(f"[View {ticker}'s filings on SEC EDGAR](https://www.sec.gov/edgar/browse/?CIK={ticker})")
        return

    saved_key = f"search_saved_{ticker}"
    if saved_key not in st.session_state:
        st.session_state[saved_key] = {s["accession"] for s in sheets if cache.has(s["accession"])}
    saved: set[str] = st.session_state[saved_key]

    pick = st.radio(
        "Term sheets",
        list(range(len(sheets))),
        format_func=lambda i: sheet_label(sheets[i], sheets[i]["accession"] in saved),
        index=None,
        key="search_pick",
        label_visibility="collapsed",
    )
    if pick is None:
        st.html(f'<div class="tse-muted">{html.escape(PICK_TEXT)}</div>')
        return
    sheet = sheets[pick]
    st.markdown(f"[View on SEC EDGAR]({lookup.edgar_filing_url(sheet['accession'])})")

    result = st.session_state.get("search_result")
    if result is None or result["accession"] != sheet["accession"]:
        is_saved = sheet["accession"] in saved
        if not is_saved and not st.button(EXTRACT_LABEL, type="primary", key="search_extract"):
            return
        outcome = _load(sheet, ticker, is_saved, budget, cache, secrets)
        if outcome.error:
            st.error(outcome.error)
            return
        result = {
            "accession": sheet["accession"],
            "jsonl_path": str(outcome.jsonl_path),
            "stem": f"{ticker}_{sheet['accession']}",
        }
        st.session_state["search_result"] = result
        if outcome.charged:
            st.session_state["session_runs"] = st.session_state.get("session_runs", 0) + 1
            if cache.has(sheet["accession"]):
                saved.add(sheet["accession"])
            st.rerun()

    path = Path(result["jsonl_path"])
    if not path.is_file():
        st.session_state.pop("search_result", None)
        st.rerun()
    render_results(path, key="search", file_stem=result["stem"])
```

Create `views/upload.py`:

```python
"""Upload term sheet tab: one live run on a .txt term sheet. Uploads are never saved."""

from __future__ import annotations

import hashlib
import html
import tempfile
from pathlib import Path
from typing import Any

import streamlit as st

import demo
from lookup import RunBudget
from runner import run_upload
from views.results import render_results
from views.search import EXTRACT_LABEL, runs_hint

HEADING = "Extract terms from your own term sheet"
SUBLINE = "Upload a pricing term sheet saved as a .txt file, up to 500 KB. Uploads are not saved."
NOT_TEXT = "The file is not plain text. Save it as .txt and try again."
STEM = "uploaded_term_sheet"


def render_upload(budget: RunBudget, secrets: dict[str, Any] | None) -> None:
    st.header(HEADING, anchor=False)
    st.html(f'<div class="tse-muted">{html.escape(SUBLINE)}</div>')
    uploaded = st.file_uploader("Term sheet (.txt)", type=["txt"], label_visibility="collapsed", key="upload_file")
    st.html(f'<div class="tse-hint">{html.escape(runs_hint(budget.remaining(), budget.daily_limit))}</div>')
    if uploaded is None:
        st.session_state.pop("upload_result", None)
        return

    content = uploaded.getvalue()
    ok, size_error = demo.check_upload_size(len(content))
    if not ok:
        st.error(size_error)
        return
    digest = hashlib.sha256(content).hexdigest()

    result = st.session_state.get("upload_result")
    if result is None or result["digest"] != digest:
        if not st.button(EXTRACT_LABEL, type="primary", key="upload_extract"):
            return
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            st.error(NOT_TEXT)
            return
        with st.spinner("Extracting with Gemini. This takes about 20 seconds."):
            outcome = run_upload(
                filing_text=text,
                stem=STEM,
                budget=budget,
                session_runs=st.session_state.get("session_runs", 0),
                api_key=demo.get_gemini_api_key(secrets),
                work_dir=Path(tempfile.mkdtemp()),
            )
        if outcome.error:
            st.error(outcome.error)
            return
        st.session_state["session_runs"] = st.session_state.get("session_runs", 0) + 1
        st.session_state["upload_result"] = {"digest": digest, "jsonl_path": str(outcome.jsonl_path)}
        st.rerun()

    path = Path(result["jsonl_path"])
    if not path.is_file():
        st.session_state.pop("upload_result", None)
        return
    render_results(path, key="upload", file_stem=STEM)
```

- [ ] **Step 4: Run the tests**

Run: `.venv/bin/python -m pytest tests/test_views.py -q` then `.venv/bin/python -m pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add views/search.py views/upload.py tests/test_views.py tests/test_app_ui.py
git commit -m "feat: add search and upload tabs"
```

---

### Task 6: New page and removals

**Files:**
- Replace: `app.py`, `tests/test_app_ui.py`
- Modify: `demo.py`, `tests/test_demo.py`, `.streamlit/secrets.toml.example`

**Interfaces:**
- Consumes: everything above; `seed_cache.seed(store) -> list[str]`; `DiskStore`; `prompt_version`
- Produces: `app.HOW_IT_WORKS: list[str]`, `app.GITHUB_URL: str`

- [ ] **Step 1: Write the failing page tests**

Replace `tests/test_app_ui.py` with the file below. Keep the old `NEVER_SHOW` list exactly as it is today and put it where the comment says.

```python
import re
from pathlib import Path

from streamlit.testing.v1 import AppTest

import demo
import extract
import lookup
from cache import prompt_version

ROOT = Path(__file__).resolve().parent.parent
APP_PATH = str(ROOT / "app.py")
AAPL_JSONL = (ROOT / "data/fixtures/AAPL_FWP_TermSheet_2025-05-06_extractions.jsonl").read_text(encoding="utf-8")
SAVED_ACC = "0001140361-25-017410"   # AAPL benchmark, seeded at startup
NEW_ACC = "0000320193-26-000001"     # valid format, never saved

SAVED_SHEET = {"accession": SAVED_ACC, "filing_date": "2025-05-06", "chars": 100, "bond_count": 4,
               "currencies": ["USD"], "text": "Pricing Term Sheet"}
NEW_SHEET = {"accession": NEW_ACC, "filing_date": "2026-08-10", "chars": 100, "bond_count": 1,
             "currencies": ["USD"], "text": "Pricing Term Sheet\n3.000% Notes due 2030"}

# NEVER_SHOW: paste the existing list from the old file here, unchanged.

NEVER_SHOW_NEW = ["example", "sample", "demo", "accuracy"]


def headline_percentages() -> list[str]:
    report = (ROOT / "output/accuracy_benchmark_report.md").read_text(encoding="utf-8")
    field = re.search(r"Field accuracy:\s*([0-9.]+%)", report).group(1)
    grounded = re.search(r"Grounded:\s*([0-9.]+%)", report).group(1)
    return [field, grounded]


def is_emoji(char: str) -> bool:
    cp = ord(char)
    return (0x1F300 <= cp <= 0x1FAFF) or (0x2600 <= cp <= 0x27BF)


def page_texts(at: AppTest) -> list[str]:
    texts: list[str] = []
    for group in (at.title, at.header, at.subheader, at.markdown, at.caption, at.info, at.error):
        texts.extend(e.value for e in group)
    texts.extend(h.value for h in at.get("html"))
    texts.extend(t.label for t in at.tabs)
    texts.extend(b.label for b in at.button)
    texts.extend(b.label for b in at.download_button)
    for r in at.radio:
        texts.extend(str(o) for o in r.options)
    for t in at.text_input:
        texts.append(t.label)
        texts.append(t.placeholder or "")
    return texts


def all_text(at: AppTest) -> str:
    return " ".join(page_texts(at))


def open_app() -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()
    assert not at.exception
    return at


def search(monkeypatch, sheets, api_key="fake-key"):
    monkeypatch.setenv("EDGAR_IDENTITY", "Test User test@example.com")
    monkeypatch.setattr(lookup, "find_term_sheets", lambda ticker, **kw: sheets)
    monkeypatch.setattr(demo, "get_gemini_api_key", lambda secrets=None: api_key)
    calls: list = []

    def fake_extract(path, **kw):
        calls.append(path)
        out = Path(kw["output_dir"]) / f"{Path(path).stem}_extractions.jsonl"
        out.write_text(AAPL_JSONL, encoding="utf-8")
        return out

    monkeypatch.setattr(extract, "extract_terms", fake_extract)
    at = open_app()
    at.text_input[0].input("AAPL")
    [b for b in at.button if b.label == "Find term sheets"][0].click().run()
    assert not at.exception
    return at, calls


def test_opens_on_the_search_tab(monkeypatch):
    monkeypatch.setenv("EDGAR_IDENTITY", "Test User test@example.com")
    at = open_app()
    assert [t.label for t in at.tabs] == ["Search filings", "Upload term sheet"]
    assert "Term Sheet Extractor" in all_text(at)
    assert any(h.value == "Find a bond deal on SEC EDGAR" for h in at.header)
    assert at.text_input[0].placeholder == "Ticker, e.g. AAPL"
    assert any(b.label == "Find term sheets" for b in at.button)
    assert any(b.label == "How it works" for b in at.button)
    assert "20 of 20 runs left today · saved results are free" in all_text(at)
    assert len(at.dataframe) == 0


def test_no_saved_deal_picker_password_or_sidebar():
    at = open_app()
    assert len(at.selectbox) == 0
    assert not any(t.label == "Password" for t in at.text_input)
    assert len(at.sidebar) == 0
    assert len(at.expander) == 0


def test_upload_tab_has_an_uploader():
    at = open_app()
    assert len(at.get("file_uploader")) == 1
    assert any(h.value == "Extract terms from your own term sheet" for h in at.header)


def test_search_not_set_up_without_identity(monkeypatch):
    monkeypatch.delenv("EDGAR_IDENTITY", raising=False)
    at = open_app()
    assert any("Search is not set up on this deployment." in i.value for i in at.info)


def test_saved_filing_opens_free(monkeypatch, isolated_store):
    at, calls = search(monkeypatch, [SAVED_SHEET])
    assert at.radio[0].options[0].endswith("`SAVED`")
    at.radio[0].set_value(0).run()
    assert not at.exception
    assert calls == []
    text = all_text(at)
    assert "Apple Inc. · $4.5bn senior notes · 4 bonds" in text
    assert "4.000%" in text and "WORD FOR WORD" in text
    assert "20 of 20 runs left today" in text
    assert len(at.dataframe) == 1
    from streamlit.proto.Dataframe_pb2 import Dataframe
    assert Dataframe.SelectionMode.SINGLE_CELL in at.dataframe[0].proto.selection_mode
    assert any(b.label == "Download Excel" for b in at.download_button)


def test_unsaved_filing_extracts_charges_and_saves(monkeypatch, isolated_store):
    at, calls = search(monkeypatch, [NEW_SHEET])
    assert not at.radio[0].options[0].endswith("`SAVED`")
    at.radio[0].set_value(0).run()
    assert len(at.dataframe) == 0
    [b for b in at.button if b.label == "Extract · uses 1 run"][0].click().run()
    assert not at.exception
    assert len(calls) == 1
    assert "19 of 20 runs left today" in all_text(at)
    assert len(at.dataframe) == 1
    assert (isolated_store / "extractions" / prompt_version() / f"{NEW_ACC}.jsonl").is_file()


def test_budget_exhausted_blocks_extract(monkeypatch):
    exhausted = lookup.RunBudget(daily_limit=20)
    for _ in range(20):
        exhausted.record_run()
    monkeypatch.setattr(lookup, "RunBudget", lambda *a, **kw: exhausted)
    at, calls = search(monkeypatch, [NEW_SHEET])
    at.radio[0].set_value(0).run()
    [b for b in at.button if b.label == "Extract · uses 1 run"][0].click().run()
    assert not at.exception
    assert calls == []
    assert any("Today's 20 free runs are used up. Try again tomorrow." in e.value for e in at.error)


def test_no_gemini_key_shows_message(monkeypatch):
    at, calls = search(monkeypatch, [NEW_SHEET], api_key=None)
    at.radio[0].set_value(0).run()
    [b for b in at.button if b.label == "Extract · uses 1 run"][0].click().run()
    assert not at.exception
    assert calls == []
    assert any("Live extraction is not set up on this deployment." in e.value for e in at.error)


def test_page_text_rules(monkeypatch):
    at, _ = search(monkeypatch, [SAVED_SHEET, NEW_SHEET])
    at.radio[0].set_value(0).run()
    from views.about import HOW_IT_WORKS
    banned = NEVER_SHOW + NEVER_SHOW_NEW
    for text in page_texts(at) + HOW_IT_WORKS:
        for ch in text:
            assert not is_emoji(ch), text[:100]
            assert ch not in "\u2014\u2013", text[:100]
        lower = text.lower()
        for word in banned:
            assert not re.search(rf"\b{re.escape(word)}\b", lower), f"{word!r} in {text[:100]}"
        for pct in headline_percentages():
            assert pct not in text, f"{pct} in {text[:100]}"


def test_how_it_works_is_short():
    from views.about import HOW_IT_WORKS
    assert 1 <= len(HOW_IT_WORKS) <= 5


def test_font_family_only_in_theme():
    for path in [ROOT / "app.py", *sorted((ROOT / "views").glob("*.py"))]:
        assert "font-family" not in path.read_text(encoding="utf-8"), path.name
```

Also keep the old `test_headings_have_no_link_anchor` test, unchanged except that it checks `at.header` and `at.subheader` instead of `at.title` and `at.subheader`.

- [ ] **Step 2: Run them and see them fail**

Run: `.venv/bin/python -m pytest tests/test_app_ui.py -q`
Expected: most tests FAIL (no tabs, old title, saved-deal selectbox, no `views.about`).

- [ ] **Step 3: Write `views/about.py` and replace `app.py`**

`HOW_IT_WORKS` lives in its own module so tests can import it without running the page.

`views/about.py`:

```python
"""Text for the top bar's How it works dialog."""

GITHUB_URL = "https://github.com/dini2-byte/bond-term-sheet-extractor"
HOW_IT_WORKS = [
    "A pricing term sheet is the short SEC filing a company publishes when it prices new bonds.",
    "Search a ticker to pull that company's recent term sheets from SEC EDGAR, then pick one to turn it into a comps table.",
    "Click any number in the table to see the sentence in the filing it came from.",
    "An amber cell means the number was found but the text does not match the filing word for word, so check it.",
    f"The code and the method are on [GitHub]({GITHUB_URL}).",
]
```

`app.py`:

```python
"""
app.py: Streamlit page for Term Sheet Extractor.
Top bar and the two tabs only; each tab lives in views/.
"""

import logging
from typing import Any

from dotenv import load_dotenv
import streamlit as st

from cache import DiskStore, ExtractionCache, ObjectStore, make_store
import lookup
from lookup import RunBudget
import seed_cache
from theme import theme_css
from views.about import GITHUB_URL, HOW_IT_WORKS
from views.search import render_search
from views.upload import render_upload

load_dotenv()
logger = logging.getLogger(__name__)


def _secrets() -> dict[str, Any] | None:
    try:
        return dict(st.secrets)
    except Exception:
        return None


@st.cache_resource
def get_store() -> ObjectStore:
    store = make_store(_secrets())
    if isinstance(store, DiskStore):
        try:
            seed_cache.seed(store)
        except (RuntimeError, OSError) as e:
            logger.warning("Saved results were not loaded (%s)", type(e).__name__)
    return store


@st.cache_resource
def get_run_budget() -> RunBudget:
    return lookup.RunBudget(store=get_store())


def get_extraction_cache() -> ExtractionCache:
    return ExtractionCache(get_store())


@st.dialog("How it works")
def how_it_works() -> None:
    for line in HOW_IT_WORKS:
        st.markdown(line)


st.set_page_config(page_title="Term Sheet Extractor", layout="wide", initial_sidebar_state="collapsed")
st.html(f"<style>{theme_css()}</style>")

brand, help_col, github_col = st.columns([6, 1.2, 0.8], vertical_alignment="center")
brand.html('<div class="tse-brand">Term Sheet Extractor</div>')
if help_col.button("How it works", type="tertiary", key="how_it_works"):
    how_it_works()
github_col.markdown(f"[GitHub]({GITHUB_URL})")

secrets = _secrets()
budget = get_run_budget()
cache = get_extraction_cache()

search_tab, upload_tab = st.tabs(["Search filings", "Upload term sheet"])
with search_tab:
    render_search(budget, cache, secrets)
with upload_tab:
    render_upload(budget, secrets)
```

- [ ] **Step 4: Remove what the page no longer uses**

1. `demo.py`: delete `format_deal_label`, `list_benchmark_deals`, `visualization_src`, `build_visualization_html`, `check_password`, `save_uploaded_filing`, `extract_headline_number`, `extract_deal_and_tranche_counts`, `format_scoring_change_line` and `parse_accuracy_report`, plus any import or constant only they used. Keep `MAX_UPLOAD_SIZE_BYTES`, `check_upload_size` and `get_gemini_api_key`. Change the module docstring to "Upload size check and Gemini key lookup for the page."
2. `tests/test_demo.py`: delete the classes `TestDealListing`, `TestSourceHighlighting`, `TestVisualizationSrc` and `TestAccuracyReport`, the tests `test_check_password_*` and `test_save_uploaded_filing_fixed_name`, and every other test that uses a removed function or `APP_PASSWORD` (read each one; list them all in the report). Fix the import block.
3. `.streamlit/secrets.toml.example`: delete the `APP_PASSWORD = ""` line.
4. Run `rg -n "list_benchmark_deals|check_password|parse_accuracy_report|visualization_src|build_visualization_html|save_uploaded_filing|APP_PASSWORD" --glob '!docs/**'` and confirm no hits remain.

- [ ] **Step 5: Run everything**

Run: `.venv/bin/python -m pytest -q`
Expected: all pass. Then run the page for 15 seconds and confirm it starts without errors:
`timeout 15 .venv/bin/streamlit run app.py --server.headless true`

- [ ] **Step 6: Commit**

```bash
git add app.py demo.py views tests .streamlit/secrets.toml.example
git commit -m "feat: rebuild the page as a search tool"
```

---

### Task 7: README, env example and report

**Files:**
- Modify: `README.md`, `.env.example`
- Create: `docs/plans/10-ui-overhaul-report.md`

- [ ] **Step 1: `.env.example`**

Add a line `EDGAR_IDENTITY=` under `GEMINI_API_KEY=`.

- [ ] **Step 2: README edits**

Make exactly these changes; leave the Results and benchmark sections as they are.

1. Replace the line starting `Live demo:` with:

   `Live app: https://bond-term-sheet-extractor-diwsf7fvsovutxsajuanis.streamlit.app/. Search a company's recent bond term sheets on SEC EDGAR or upload your own. The four benchmark deals are saved and open without a Gemini call; any other filing uses one of 20 shared runs a day, and its result is saved for the next visitor.`

2. In "How it works", replace the `app.py` and `demo.py` bullets with these, keeping the other bullets:

   - `` `app.py`: Streamlit page: top bar and the Search filings and Upload term sheet tabs. ``
   - `` `views/`: the two tabs, the shared results view (deal line, comps table, source panel and Excel download) and the How it works text. ``
   - `` `theme.py`: colors and styling for the light and dark themes. ``
   - `` `lookup.py`: finds a company's recent bond term sheets on SEC EDGAR and keeps the daily run limit. ``
   - `` `cache.py`: saves each extraction by prompt version and SEC accession number, on Cloudflare R2 or local disk. ``
   - `` `runner.py`: loads a saved extraction or runs a new one, and counts a run only for a real Gemini call. ``
   - `` `seed_cache.py`: saves the four benchmark extractions into the cache. ``
   - `` `demo.py`: upload size check and Gemini key lookup. ``

3. Replace the sentence starting `` `streamlit run app.py` opens the four benchmark deals `` with:

   `` `streamlit run app.py` opens the tool. Search needs `EDGAR_IDENTITY` (your name and email, as SEC asks) in `.env`. The four benchmark deals load from `data/fixtures/` without an API key; any other filing or an upload needs `GEMINI_API_KEY`. ``

4. In "Limits", replace the sentence starting `Live upload on the hosted app needs a password` with:

   `The hosted app allows 20 Gemini runs a day across all visitors and 3 per visit; saved results do not count.`

- [ ] **Step 3: Final checks**

Run each and paste the output into the report:
- `.venv/bin/python -m pytest -q -rxX`
- `.venv/bin/python evaluate.py | head -3` (must still read 344/350)
- `timeout 15 .venv/bin/streamlit run app.py --server.headless true`
- `git log --oneline master..slice-10-ui`
- `git diff --stat master`

- [ ] **Step 4: Write `docs/plans/10-ui-overhaul-report.md`**

Sections: tasks table with commit hashes; tests added; every test deleted or rewritten with one line why; anything skipped or changed from this plan and why; what a reviewer should look at first; the outputs from Step 3. Same text rules as commits: no em dashes, no Oxford commas.

- [ ] **Step 5: Commit**

```bash
git add README.md .env.example docs/plans/10-ui-overhaul-report.md
git commit -m "docs: add slice 10 report"
```

---

## After agy: Claude and Aidin

1. Claude reviews the branch, reruns the checks and opens the page locally in a browser in light and dark (browser color scheme and Streamlit's Settings menu), at desktop and phone width. Small visual fixes are made directly.
2. Merge to `master`, push, wait for Streamlit Cloud to redeploy, run `gh workflow run keep-alive.yml` (it waits for the Streamlit app root, so the new layout does not affect it) and check the live page in both modes.
3. Close the slice 10 issue.
