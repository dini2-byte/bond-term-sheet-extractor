# Slice 9: Saved results and a run limit that survives restarts

> **For agentic workers:** work task by task, in order. Steps use checkbox (`- [ ]`) syntax for tracking.

**Implementer**: agy, working alone from start to finish
**Reviewer**: Claude Code (review, seed the real cache, merge and push)
**Branch**: `slice-09-cache`, cut from current `master` (after the commit that adds this plan)
**Target**: 2026-10-16
**Spec**: `docs/superpowers/specs/2026-10-13-ui-overhaul-design.md`, Part 2

**Goal:** Every SEC filing is extracted at most once per prompt version; later lookups load the saved result for free, and the daily run limit no longer resets when the app sleeps.

**Architecture:** A small object store (`DiskStore` locally, `R2Store` on Cloudflare R2) sits under two users: `ExtractionCache` (saved extractions keyed by prompt version and SEC accession number) and `RunBudget` (the day's run count). A new `runner.get_or_extract` holds the hit, miss and error flow so it can be tested without Streamlit; `app.py` only calls it.

**Tech Stack:** Python 3.12, boto3 (S3 API against R2), Streamlit 1.64, pytest, GitHub Actions with Playwright for the keep-alive job.

## Read first, in this order

1. `CONTEXT.md`: project terms. Use them in code, tests and docs.
2. The spec above, Part 2 only. Part 1 and Part 3's UI are slice 10, not this slice.
3. `lookup.py` (`RunBudget`, `find_term_sheets`), `extract.py` (`extract_terms`), `app.py` lines 340-400 (the search tab's Extract button).

## Global Constraints

- Write each test before its code change. Run it and show it failing, then passing.
- Branch `slice-09-cache` from current `master`. Commit after each task. Do not push. Do not merge.
- Commit messages: imperative subject of 50 characters or fewer with a Conventional Commits prefix (`feat:`, `fix:`, `test:`, `docs:`, `chore:`, `ci:`), no em or en dashes, no Oxford commas, no AI attribution or co-author lines of any kind. A hook rejects commits that break these rules; fix the message and retry, never bypass it.
- **No Gemini calls.** Budget for this slice: 0. Tests make no network calls of any kind (no R2, no EDGAR, no Gemini).
- **Never touch real R2.** Do not read R2 credentials from `.env`, do not run `seed_cache.py` against R2 and do not create buckets. Claude does that after review.
- Never print, log or copy any secret (Gemini key, R2 keys). Log exception type names, not messages that could hold a URL with a signature.
- Never edit `fields.py`, `extract.py`, `evaluate.py`, `structure.py`, `data/answer_key.json`, `data/test_set/`, `data/raw_filings/` or any `data/fixtures/*_extractions.jsonl`.
- Do not change page layout, wording or styling beyond what Task 4 says. Slice 10 redoes the page.
- All 279 existing tests must keep passing. If one must change, say which and why in the report.
- If something in this plan turns out wrong or impossible, stop that task, write what you found in the report and continue with the next task that does not depend on it.

## Files

| File | Change | Responsibility |
|---|---|---|
| `cache.py` | create | `prompt_version`, `ObjectStore` protocol, `DiskStore`, `R2Store`, `make_store`, `ExtractionCache` |
| `runner.py` | create | `RunOutcome`, `get_or_extract`: the cache hit, miss and error flow |
| `lookup.py` | modify | `RunBudget` gains an optional `store` |
| `app.py` | modify | search tab uses `get_or_extract`; picker marks saved filings |
| `seed_cache.py` | create | writes the 4 benchmark fixtures into a store |
| `data/fixtures/PROMPT_VERSION` | create | prompt version the benchmark fixtures were made with |
| `scripts/keep_alive.py` | create | opens the app, wakes it if asleep |
| `.github/workflows/keep-alive.yml` | create | runs the script every 6 hours |
| `requirements.txt` | modify | add `boto3` |
| `.streamlit/secrets.toml.example` | modify | add the four R2 names |
| `.gitignore` | modify | add `.cache/` |
| `tests/test_cache.py`, `tests/test_runner.py`, `tests/test_seed_cache.py` | create | tests |
| `tests/test_lookup.py` | modify | budget store tests |

---

### Task 1: Object stores and the prompt version (`cache.py`)

**Files:**
- Create: `cache.py`, `tests/test_cache.py`
- Modify: `requirements.txt`, `.streamlit/secrets.toml.example`, `.gitignore`

**Interfaces:**
- Produces:
  - `MODEL_ID: str = "gemini-3.5-flash-lite"`
  - `prompt_version(prompt: str = PROMPT_DESCRIPTION, examples: list = FEW_SHOT_EXAMPLES, model_id: str = MODEL_ID) -> str` (12 lowercase hex characters)
  - `class ObjectStore(Protocol)`: `get_text(key: str) -> str | None`, `put_text(key: str, text: str) -> None`, `exists(key: str) -> bool`
  - `class DiskStore(root: Path)`
  - `class R2Store(client: Any, bucket: str)`
  - `R2_SECRET_NAMES: tuple[str, ...] = ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET")`
  - `make_store(secrets: Mapping[str, Any] | None, disk_root: Path = Path(".cache")) -> ObjectStore`

- [ ] **Step 1: Add the dependency and config lines**

Run `.venv/bin/pip install boto3`, then add `boto3==<the exact version pip installed>` to `requirements.txt` (run `.venv/bin/pip show boto3` to read it). Add `.cache/` on its own line to `.gitignore`. Replace `.streamlit/secrets.toml.example` with:

```toml
APP_PASSWORD = ""
GEMINI_API_KEY = ""
R2_ACCOUNT_ID = ""
R2_ACCESS_KEY_ID = ""
R2_SECRET_ACCESS_KEY = ""
R2_BUCKET = ""
```

- [ ] **Step 2: Write the failing tests** in `tests/test_cache.py`

```python
import io
from pathlib import Path

import pytest

import cache
from cache import DiskStore, R2Store, make_store, prompt_version


class FakeS3:
    """Stands in for a boto3 S3 client. Raises like botocore does on a missing key."""

    def __init__(self, fail: bool = False):
        self.objects: dict[tuple[str, str], bytes] = {}
        self.fail = fail
        self.put_calls: list[dict] = []

    def get_object(self, Bucket, Key):
        if self.fail:
            raise ConnectionError("network down")
        if (Bucket, Key) not in self.objects:
            raise KeyError(Key)
        return {"Body": io.BytesIO(self.objects[(Bucket, Key)])}

    def put_object(self, Bucket, Key, Body, ContentType):
        if self.fail:
            raise ConnectionError("network down")
        self.put_calls.append({"Bucket": Bucket, "Key": Key, "ContentType": ContentType})
        self.objects[(Bucket, Key)] = Body

    def head_object(self, Bucket, Key):
        if self.fail:
            raise ConnectionError("network down")
        if (Bucket, Key) not in self.objects:
            raise KeyError(Key)
        return {}


class TestPromptVersion:
    def test_is_12_hex_and_stable(self):
        v = prompt_version()
        assert len(v) == 12
        assert all(c in "0123456789abcdef" for c in v)
        assert prompt_version() == v

    def test_changes_with_prompt(self):
        assert prompt_version(prompt="something else") != prompt_version()

    def test_changes_with_model(self):
        assert prompt_version(model_id="another-model") != prompt_version()


class TestDiskStore:
    def test_round_trip(self, tmp_path: Path):
        store = DiskStore(tmp_path)
        assert store.get_text("a/b.json") is None
        assert store.exists("a/b.json") is False
        store.put_text("a/b.json", "€ text")
        assert store.get_text("a/b.json") == "€ text"
        assert store.exists("a/b.json") is True

    def test_rejects_key_outside_root(self, tmp_path: Path):
        store = DiskStore(tmp_path)
        with pytest.raises(ValueError):
            store.put_text("../escape.txt", "x")


class TestR2Store:
    def test_round_trip(self):
        client = FakeS3()
        store = R2Store(client, "bucket")
        assert store.get_text("k") is None
        assert store.exists("k") is False
        store.put_text("k", "€ text")
        assert store.get_text("k") == "€ text"
        assert store.exists("k") is True
        assert client.put_calls[0] == {"Bucket": "bucket", "Key": "k", "ContentType": "text/plain; charset=utf-8"}

    def test_errors_become_misses(self):
        store = R2Store(FakeS3(fail=True), "bucket")
        assert store.get_text("k") is None
        assert store.exists("k") is False
        store.put_text("k", "x")  # must not raise


class TestMakeStore:
    def test_disk_when_secrets_missing(self, tmp_path: Path):
        assert isinstance(make_store(None, disk_root=tmp_path), DiskStore)
        assert isinstance(make_store({"R2_BUCKET": "b"}, disk_root=tmp_path), DiskStore)

    def test_disk_when_a_secret_is_blank(self, tmp_path: Path):
        secrets = {name: "x" for name in cache.R2_SECRET_NAMES}
        secrets["R2_SECRET_ACCESS_KEY"] = "  "
        assert isinstance(make_store(secrets, disk_root=tmp_path), DiskStore)

    def test_r2_when_all_secrets_present(self, monkeypatch, tmp_path: Path):
        captured = {}

        def fake_client(service, **kwargs):
            captured["service"] = service
            captured.update(kwargs)
            return FakeS3()

        monkeypatch.setattr(cache.boto3, "client", fake_client)
        secrets = {
            "R2_ACCOUNT_ID": "acct123",
            "R2_ACCESS_KEY_ID": "id",
            "R2_SECRET_ACCESS_KEY": "secret",
            "R2_BUCKET": "bucket",
        }
        store = make_store(secrets, disk_root=tmp_path)
        assert isinstance(store, R2Store)
        assert captured["service"] == "s3"
        assert captured["endpoint_url"] == "https://acct123.r2.cloudflarestorage.com"
        assert captured["region_name"] == "auto"
```

- [ ] **Step 3: Run them to see them fail**

Run: `.venv/bin/python -m pytest tests/test_cache.py -q`
Expected: collection error, `ModuleNotFoundError: No module named 'cache'`.

- [ ] **Step 4: Write `cache.py`** (first part; Task 2 adds `ExtractionCache` to the same file)

```python
"""
Saved extractions and small shared state, kept in an object store.
DiskStore is used locally and in tests; R2Store is used on the deployed app.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

import boto3

from fields import FEW_SHOT_EXAMPLES, PROMPT_DESCRIPTION

logger = logging.getLogger(__name__)

MODEL_ID = "gemini-3.5-flash-lite"
R2_SECRET_NAMES = ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET")
PROMPT_VERSION_LENGTH = 12


def prompt_version(
    prompt: str = PROMPT_DESCRIPTION,
    examples: list = FEW_SHOT_EXAMPLES,
    model_id: str = MODEL_ID,
) -> str:
    """Short hash of everything that shapes an extraction. Changes when the prompt, examples or model change."""
    payload = json.dumps(
        {
            "prompt": prompt,
            "examples": [dataclasses.asdict(e) for e in examples],
            "model": model_id,
        },
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:PROMPT_VERSION_LENGTH]


class ObjectStore(Protocol):
    def get_text(self, key: str) -> str | None: ...
    def put_text(self, key: str, text: str) -> None: ...
    def exists(self, key: str) -> bool: ...


class DiskStore:
    """Keeps objects as files under root. Keys use forward slashes."""

    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError(f"Key escapes the store root: {key!r}")
        return path

    def get_text(self, key: str) -> str | None:
        path = self._path(key)
        return path.read_text(encoding="utf-8") if path.is_file() else None

    def put_text(self, key: str, text: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()


class R2Store:
    """Cloudflare R2 through the S3 API. Any error is logged and treated as a miss."""

    def __init__(self, client: Any, bucket: str):
        self.client = client
        self.bucket = bucket

    def get_text(self, key: str) -> str | None:
        try:
            obj = self.client.get_object(Bucket=self.bucket, Key=key)
            return obj["Body"].read().decode("utf-8")
        except Exception as e:
            logger.info("R2 read miss for %s (%s)", key, type(e).__name__)
            return None

    def put_text(self, key: str, text: str) -> None:
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=text.encode("utf-8"),
                ContentType="text/plain; charset=utf-8",
            )
        except Exception as e:
            logger.warning("R2 write failed for %s (%s)", key, type(e).__name__)

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False


def make_store(secrets: Mapping[str, Any] | None, disk_root: Path = Path(".cache")) -> ObjectStore:
    """R2Store when all four R2 secrets are set and non-blank, otherwise DiskStore."""
    values = {name: str((secrets or {}).get(name) or "").strip() for name in R2_SECRET_NAMES}
    if not all(values.values()):
        return DiskStore(disk_root)
    client = boto3.client(
        "s3",
        endpoint_url=f"https://{values['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=values["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=values["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )
    return R2Store(client, values["R2_BUCKET"])
```

- [ ] **Step 5: Run the tests**

Run: `.venv/bin/python -m pytest tests/test_cache.py -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add cache.py tests/test_cache.py requirements.txt .streamlit/secrets.toml.example .gitignore
git commit -m "feat: add object stores and prompt version"
```

---

### Task 2: Saved extractions (`ExtractionCache`)

**Files:**
- Modify: `cache.py`, `tests/test_cache.py`

**Interfaces:**
- Consumes: `ObjectStore`, `prompt_version` (Task 1)
- Produces:
  - `is_valid_extraction_jsonl(text: str | None) -> bool`
  - `class ExtractionCache(store: ObjectStore, version: str | None = None)` with `key(accession: str) -> str`, `get(accession: str) -> str | None`, `put(accession: str, jsonl: str) -> None`, `has(accession: str) -> bool`

Accession numbers look like `0001140361-25-017410`. Anything else is rejected with `ValueError`, so a key can never be built from stray text.

- [ ] **Step 1: Add the failing tests** to `tests/test_cache.py`

```python
from cache import ExtractionCache, is_valid_extraction_jsonl

GOOD_JSONL = '{"extractions": [], "text": "Term sheet", "document_id": "d"}\n'


class TestExtractionCache:
    def test_key_uses_version_and_accession(self, tmp_path: Path):
        c = ExtractionCache(DiskStore(tmp_path), version="abc123abc123")
        assert c.key("0001140361-25-017410") == "extractions/abc123abc123/0001140361-25-017410.jsonl"

    def test_default_version_is_current_prompt(self, tmp_path: Path):
        assert ExtractionCache(DiskStore(tmp_path)).version == prompt_version()

    def test_round_trip(self, tmp_path: Path):
        c = ExtractionCache(DiskStore(tmp_path), version="v1v1v1v1v1v1")
        acc = "0001193125-17-024075"
        assert c.get(acc) is None
        assert c.has(acc) is False
        c.put(acc, GOOD_JSONL)
        assert c.get(acc) == GOOD_JSONL
        assert c.has(acc) is True

    def test_other_version_misses(self, tmp_path: Path):
        store = DiskStore(tmp_path)
        ExtractionCache(store, version="aaaaaaaaaaaa").put("0001193125-17-024075", GOOD_JSONL)
        assert ExtractionCache(store, version="bbbbbbbbbbbb").get("0001193125-17-024075") is None

    def test_broken_object_is_a_miss(self, tmp_path: Path):
        store = DiskStore(tmp_path)
        c = ExtractionCache(store, version="v1v1v1v1v1v1")
        store.put_text(c.key("0001193125-17-024075"), "not json")
        assert c.get("0001193125-17-024075") is None

    @pytest.mark.parametrize("bad", ["", "../x", "0001140361-25-01741", "AAPL", "0001140361/25/017410"])
    def test_rejects_bad_accession(self, tmp_path: Path, bad: str):
        c = ExtractionCache(DiskStore(tmp_path), version="v1v1v1v1v1v1")
        with pytest.raises(ValueError):
            c.key(bad)

    def test_put_refuses_invalid_jsonl(self, tmp_path: Path):
        c = ExtractionCache(DiskStore(tmp_path), version="v1v1v1v1v1v1")
        with pytest.raises(ValueError):
            c.put("0001193125-17-024075", "not json")


class TestIsValidExtractionJsonl:
    def test_cases(self):
        assert is_valid_extraction_jsonl(GOOD_JSONL) is True
        assert is_valid_extraction_jsonl(None) is False
        assert is_valid_extraction_jsonl("") is False
        assert is_valid_extraction_jsonl("{}") is False
        assert is_valid_extraction_jsonl('{"extractions": "x", "text": "t"}') is False

    def test_benchmark_fixture_is_valid(self):
        text = Path("data/fixtures/AAPL_FWP_TermSheet_2025-05-06_extractions.jsonl").read_text(encoding="utf-8")
        assert is_valid_extraction_jsonl(text) is True
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m pytest tests/test_cache.py -q`
Expected: `ImportError: cannot import name 'ExtractionCache'`.

- [ ] **Step 3: Append to `cache.py`**

Add `import re` to the imports, then:

```python
ACCESSION_PATTERN = re.compile(r"^\d{10}-\d{2}-\d{6}$")


def is_valid_extraction_jsonl(text: str | None) -> bool:
    """True when the first line is a JSON object with an extractions list and a text string."""
    if not text or not text.strip():
        return False
    try:
        doc = json.loads(text.strip().splitlines()[0])
    except (json.JSONDecodeError, IndexError):
        return False
    return isinstance(doc, dict) and isinstance(doc.get("extractions"), list) and isinstance(doc.get("text"), str)


class ExtractionCache:
    """Extractor output saved per SEC accession number, separated by prompt version."""

    def __init__(self, store: ObjectStore, version: str | None = None):
        self.store = store
        self.version = version or prompt_version()

    def key(self, accession: str) -> str:
        if not ACCESSION_PATTERN.match(accession or ""):
            raise ValueError(f"Not an SEC accession number: {accession!r}")
        return f"extractions/{self.version}/{accession}.jsonl"

    def get(self, accession: str) -> str | None:
        text = self.store.get_text(self.key(accession))
        if text is None:
            return None
        if not is_valid_extraction_jsonl(text):
            logger.warning("Ignoring a broken saved extraction for %s", accession)
            return None
        return text

    def put(self, accession: str, jsonl: str) -> None:
        if not is_valid_extraction_jsonl(jsonl):
            raise ValueError("Refusing to save output that is not extractor JSONL.")
        self.store.put_text(self.key(accession), jsonl)

    def has(self, accession: str) -> bool:
        return self.store.exists(self.key(accession))
```

- [ ] **Step 4: Run the tests**

Run: `.venv/bin/python -m pytest tests/test_cache.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add cache.py tests/test_cache.py
git commit -m "feat: save extractions by prompt and accession"
```

---

### Task 3: Run budget backed by a store (`lookup.py`)

**Files:**
- Modify: `lookup.py` (class `RunBudget`, currently lines 315-355), `tests/test_lookup.py`

**Interfaces:**
- Consumes: `ObjectStore`, `DiskStore` (Task 1)
- Produces: `RunBudget(daily_limit: int = 20, session_limit: int = 3, today: Callable[[], date] = date.today, store: ObjectStore | None = None)`. Public methods unchanged: `remaining() -> int`, `can_run(session_runs: int = 0) -> tuple[bool, str | None]`, `record_run() -> None`. With a store, the day's count lives at key `budget/<YYYY-MM-DD>.json` as `{"count": <int>}`. Without a store it behaves exactly as today.

- [ ] **Step 1: Add the failing tests** to `tests/test_lookup.py`

```python
from cache import DiskStore


class TestRunBudgetStore:
    def test_count_survives_a_new_budget(self, tmp_path):
        store = DiskStore(tmp_path)
        day = lambda: date(2026, 10, 14)
        RunBudget(daily_limit=5, store=store, today=day).record_run()
        RunBudget(daily_limit=5, store=store, today=day).record_run()
        assert RunBudget(daily_limit=5, store=store, today=day).remaining() == 3
        assert store.get_text("budget/2026-10-14.json") == '{"count": 2}'

    def test_new_day_starts_at_zero(self, tmp_path):
        store = DiskStore(tmp_path)
        RunBudget(daily_limit=5, store=store, today=lambda: date(2026, 10, 14)).record_run()
        assert RunBudget(daily_limit=5, store=store, today=lambda: date(2026, 10, 15)).remaining() == 5

    def test_daily_cap_uses_stored_count(self, tmp_path):
        store = DiskStore(tmp_path)
        store.put_text("budget/2026-10-14.json", '{"count": 20}')
        ok, msg = RunBudget(store=store, today=lambda: date(2026, 10, 14)).can_run(session_runs=0)
        assert ok is False
        assert msg == "Today's 20 free runs are used up. Try again tomorrow."

    def test_broken_count_reads_as_zero(self, tmp_path):
        store = DiskStore(tmp_path)
        store.put_text("budget/2026-10-14.json", "garbage")
        assert RunBudget(daily_limit=5, store=store, today=lambda: date(2026, 10, 14)).remaining() == 5
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m pytest tests/test_lookup.py -q -k RunBudgetStore`
Expected: `TypeError: RunBudget.__init__() got an unexpected keyword argument 'store'`.

- [ ] **Step 3: Replace the `RunBudget` class in `lookup.py`**

Add `import json` to the imports if missing, plus `from cache import ObjectStore`. Then:

```python
class RunBudget:
    """
    Tracks runs per calendar day across the whole site.
    With a store, the day's count is kept in it so it survives restarts.
    Without one, the count lives in memory and resets when today() changes.
    """

    def __init__(
        self,
        daily_limit: int = 20,
        session_limit: int = 3,
        today: Callable[[], date] = date.today,
        store: ObjectStore | None = None,
    ):
        self.daily_limit = daily_limit
        self.session_limit = session_limit
        self.today = today
        self.store = store
        self._current_date = self.today()
        self._daily_count = 0

    def _key(self) -> str:
        return f"budget/{self.today().isoformat()}.json"

    def _check_reset(self) -> None:
        current = self.today()
        if current != self._current_date:
            self._current_date = current
            self._daily_count = 0

    def _count(self) -> int:
        if self.store is None:
            self._check_reset()
            return self._daily_count
        text = self.store.get_text(self._key())
        if not text:
            return 0
        try:
            return int(json.loads(text)["count"])
        except (ValueError, KeyError, TypeError):
            return 0

    def remaining(self) -> int:
        return max(0, self.daily_limit - self._count())

    def can_run(self, session_runs: int = 0) -> tuple[bool, str | None]:
        if self._count() >= self.daily_limit:
            return False, f"Today's {self.daily_limit} free runs are used up. Try again tomorrow."
        if session_runs >= self.session_limit:
            return False, f"You've used your {self.session_limit} runs for this visit."
        return True, None

    def record_run(self) -> None:
        if self.store is None:
            self._check_reset()
            self._daily_count += 1
            return
        self.store.put_text(self._key(), json.dumps({"count": self._count() + 1}))
```

- [ ] **Step 4: Run all lookup tests**

Run: `.venv/bin/python -m pytest tests/test_lookup.py -q`
Expected: all pass, old `TestRunBudget` included.

- [ ] **Step 5: Commit**

```bash
git add lookup.py tests/test_lookup.py
git commit -m "feat: keep the daily run count in a store"
```

---

### Task 4: Use saved results in the search tab (`runner.py`, `app.py`)

**Files:**
- Create: `runner.py`, `tests/test_runner.py`
- Modify: `app.py` (`get_run_budget` near line 57; the picker label `sheet_label` near line 320; the Extract button block near lines 353-398)

**Interfaces:**
- Consumes: `ExtractionCache` (Task 2), `RunBudget` (Task 3), `extract_terms` from `extract.py`, `MODEL_ID` from `cache.py`
- Produces:
  - `@dataclass(frozen=True) class RunOutcome`: `jsonl_path: Path | None`, `from_cache: bool`, `charged: bool`, `error: str | None`
  - `get_or_extract(accession: str, filing_text: str, stem: str, cache: ExtractionCache, budget: RunBudget, session_runs: int, api_key: str | None, work_dir: Path, extract_fn: Callable[..., Any] = extract_terms) -> RunOutcome`
  - Messages (exact strings, used by slice 10): `NO_KEY_MESSAGE = "Live extraction is not set up on this deployment."`, `FAILED_MESSAGE = "The extraction did not finish. Your run was not counted."`

Flow: cache hit, write the saved JSONL to `work_dir/<stem>_extractions.jsonl` and return `from_cache=True, charged=False`. Miss: budget check, then key check, then extract, then charge, then save. A failed extraction charges nothing and saves nothing.

- [ ] **Step 1: Write the failing tests** in `tests/test_runner.py`

```python
from datetime import date
from pathlib import Path

from cache import DiskStore, ExtractionCache
from lookup import RunBudget
from runner import FAILED_MESSAGE, NO_KEY_MESSAGE, get_or_extract

ACC = "0001140361-25-017410"
GOOD_JSONL = '{"extractions": [], "text": "Term sheet", "document_id": "d"}\n'
DAY = lambda: date(2026, 10, 14)


def fake_extractor(calls: list):
    def extract(filing_path, model_id, log_attempt, output_dir):
        calls.append({"filing_path": Path(filing_path), "model_id": model_id, "log_attempt": log_attempt})
        (Path(output_dir) / f"{Path(filing_path).stem}_extractions.jsonl").write_text(GOOD_JSONL, encoding="utf-8")
    return extract


def failing_extractor(*args, **kwargs):
    raise RuntimeError("model said no")


def setup(tmp_path: Path):
    store = DiskStore(tmp_path / "store")
    work = tmp_path / "work"
    work.mkdir()
    return ExtractionCache(store, version="v1v1v1v1v1v1"), RunBudget(daily_limit=5, store=store, today=DAY), work


def test_hit_is_free_and_skips_extraction(tmp_path):
    cache, budget, work = setup(tmp_path)
    cache.put(ACC, GOOD_JSONL)
    calls: list = []
    out = get_or_extract(ACC, "filing", "AAPL_x", cache, budget, 0, None, work, extract_fn=fake_extractor(calls))
    assert out.from_cache is True and out.charged is False and out.error is None
    assert out.jsonl_path.read_text(encoding="utf-8") == GOOD_JSONL
    assert calls == []
    assert budget.remaining() == 5


def test_miss_extracts_charges_and_saves(tmp_path):
    cache, budget, work = setup(tmp_path)
    calls: list = []
    out = get_or_extract(ACC, "filing text", "AAPL_x", cache, budget, 0, "key", work, extract_fn=fake_extractor(calls))
    assert out.from_cache is False and out.charged is True and out.error is None
    assert calls[0]["model_id"] == "gemini-3.5-flash-lite"
    assert calls[0]["log_attempt"] is False
    assert calls[0]["filing_path"].read_text(encoding="utf-8") == "filing text"
    assert budget.remaining() == 4
    assert cache.get(ACC) == GOOD_JSONL


def test_failed_extraction_charges_nothing(tmp_path):
    cache, budget, work = setup(tmp_path)
    out = get_or_extract(ACC, "filing", "AAPL_x", cache, budget, 0, "key", work, extract_fn=failing_extractor)
    assert out.error == FAILED_MESSAGE and out.charged is False and out.jsonl_path is None
    assert budget.remaining() == 5
    assert cache.get(ACC) is None


def test_no_key_on_miss(tmp_path):
    cache, budget, work = setup(tmp_path)
    out = get_or_extract(ACC, "filing", "AAPL_x", cache, budget, 0, None, work, extract_fn=failing_extractor)
    assert out.error == NO_KEY_MESSAGE and out.charged is False


def test_budget_blocks_a_miss_but_not_a_hit(tmp_path):
    cache, budget, work = setup(tmp_path)
    out = get_or_extract(ACC, "filing", "AAPL_x", cache, budget, 3, "key", work, extract_fn=failing_extractor)
    assert out.error == "You've used your 3 runs for this visit."
    cache.put(ACC, GOOD_JSONL)
    out = get_or_extract(ACC, "filing", "AAPL_x", cache, budget, 3, "key", work, extract_fn=failing_extractor)
    assert out.from_cache is True and out.error is None
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m pytest tests/test_runner.py -q`
Expected: `ModuleNotFoundError: No module named 'runner'`.

- [ ] **Step 3: Write `runner.py`**

```python
"""
Loads a saved extraction or runs a new one, charging the run budget only for real Gemini calls.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cache import MODEL_ID, ExtractionCache
from extract import extract_terms
from lookup import RunBudget

logger = logging.getLogger(__name__)

NO_KEY_MESSAGE = "Live extraction is not set up on this deployment."
FAILED_MESSAGE = "The extraction did not finish. Your run was not counted."


@dataclass(frozen=True)
class RunOutcome:
    jsonl_path: Path | None
    from_cache: bool
    charged: bool
    error: str | None


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
    jsonl_path = Path(work_dir) / f"{stem}_extractions.jsonl"

    saved = cache.get(accession)
    if saved is not None:
        jsonl_path.write_text(saved, encoding="utf-8")
        return RunOutcome(jsonl_path, from_cache=True, charged=False, error=None)

    can_run, reason = budget.can_run(session_runs)
    if not can_run:
        return RunOutcome(None, from_cache=False, charged=False, error=reason)
    if not api_key:
        return RunOutcome(None, from_cache=False, charged=False, error=NO_KEY_MESSAGE)

    os.environ["GEMINI_API_KEY"] = api_key
    os.environ["GOOGLE_API_KEY"] = api_key
    filing_path = Path(work_dir) / f"{stem}.txt"
    filing_path.write_text(filing_text, encoding="utf-8")
    try:
        extract_fn(filing_path, model_id=MODEL_ID, log_attempt=False, output_dir=Path(work_dir))
    except Exception as e:
        logger.warning("Extraction failed for %s (%s)", accession, type(e).__name__)
        return RunOutcome(None, from_cache=False, charged=False, error=FAILED_MESSAGE)

    budget.record_run()
    jsonl = jsonl_path.read_text(encoding="utf-8")
    try:
        cache.put(accession, jsonl)
    except ValueError:
        logger.warning("Extractor output for %s was not saved: not valid JSONL", accession)
    return RunOutcome(jsonl_path, from_cache=False, charged=True, error=None)
```

- [ ] **Step 4: Run the tests**

Run: `.venv/bin/python -m pytest tests/test_runner.py -q`
Expected: all pass.

- [ ] **Step 5: Wire it into `app.py`**

Replace `get_run_budget` (near line 57) with:

```python
def _secrets() -> dict[str, Any] | None:
    try:
        return dict(st.secrets)
    except Exception:
        return None


@st.cache_resource
def get_store() -> ObjectStore:
    return make_store(_secrets())


@st.cache_resource
def get_run_budget() -> RunBudget:
    return lookup.RunBudget(store=get_store())


def get_extraction_cache() -> ExtractionCache:
    return ExtractionCache(get_store())
```

Add `from cache import ExtractionCache, ObjectStore, make_store` and `from runner import get_or_extract` to the imports.

In `sheet_label`, append `" · saved"` to the returned label when `get_extraction_cache().has(item["accession"])` is True. Keep everything else in the label as it is.

Replace the whole `if extract_btn:` block with:

```python
                if extract_btn:
                    session_runs = st.session_state.get("session_runs", 0)
                    temp_dir = Path(tempfile.mkdtemp())
                    with st.spinner("Extracting with Gemini. This takes about 20 seconds."):
                        outcome = get_or_extract(
                            accession=selected_sheet["accession"],
                            filing_text=selected_sheet["text"],
                            stem=f"{norm_ticker}_{selected_sheet['accession']}",
                            cache=get_extraction_cache(),
                            budget=budget,
                            session_runs=session_runs,
                            api_key=get_gemini_api_key(secrets_dict),
                            work_dir=temp_dir,
                        )
                    if outcome.error:
                        st.error(outcome.error)
                    else:
                        if outcome.charged:
                            st.session_state["session_runs"] = session_runs + 1
                        st.session_state["live_deal"] = {
                            "jsonl_path": str(outcome.jsonl_path),
                            "ticker": norm_ticker,
                            "filing_date": selected_sheet["filing_date"],
                            "accession": selected_sheet["accession"],
                        }
                        st.rerun()
```

Remove imports that are now unused (for example `os` or `extract_terms`) only if nothing else in `app.py` uses them.

- [ ] **Step 6: Run the full suite and a headless start**

Run: `.venv/bin/python -m pytest -q`
Expected: all pass.
Run: `timeout 15 .venv/bin/streamlit run app.py --server.headless true`
Expected: server starts, no traceback.

- [ ] **Step 7: Commit**

```bash
git add runner.py tests/test_runner.py app.py
git commit -m "feat: load saved extractions before running Gemini"
```

---

### Task 5: Seed script for the benchmark deals

**Files:**
- Create: `seed_cache.py`, `data/fixtures/PROMPT_VERSION`, `tests/test_seed_cache.py`

**Interfaces:**
- Consumes: `ExtractionCache`, `make_store`, `prompt_version`, `DiskStore` (Tasks 1-2); `DEALS_TO_FETCH` from `fetch.py` (each has `label` and `accession`)
- Produces: `seed(store: ObjectStore, fixtures_dir: Path = Path("data/fixtures"), version_file: Path = Path("data/fixtures/PROMPT_VERSION")) -> list[str]` (accessions written, in `DEALS_TO_FETCH` order)

Why the version file: `fields.py` last changed on 2026-09-24 (`acb9058`) and every benchmark fixture was made after that (2026-10-07 to 2026-10-09, see `data/fixtures/attempts.jsonl`), so the fixtures match today's prompt. The file records that. If the prompt changes later, `seed` refuses, and a test fails until fixtures are regenerated and the file updated.

- [ ] **Step 1: Write the version file**

Run: `.venv/bin/python -c "from cache import prompt_version; print(prompt_version())" > data/fixtures/PROMPT_VERSION`
Then `cat data/fixtures/PROMPT_VERSION`. Expected: `8fe458b91177`. If it differs, `prompt_version` was written differently from Task 1; stop and report.

- [ ] **Step 2: Write the failing tests** in `tests/test_seed_cache.py`

```python
from pathlib import Path

import pytest

from cache import DiskStore, ExtractionCache, prompt_version
from seed_cache import seed

EXPECTED = [
    "0001140361-25-017410",
    "0001193125-17-024075",
    "0001193125-25-215807",
    "0001193125-26-338750",
]


def test_version_file_matches_current_prompt():
    assert Path("data/fixtures/PROMPT_VERSION").read_text(encoding="utf-8").strip() == prompt_version()


def test_seed_writes_all_four(tmp_path):
    store = DiskStore(tmp_path)
    assert seed(store) == EXPECTED
    cache = ExtractionCache(store)
    for acc in EXPECTED:
        assert cache.get(acc) is not None


def test_seed_refuses_on_version_mismatch(tmp_path):
    version_file = tmp_path / "PROMPT_VERSION"
    version_file.write_text("000000000000\n", encoding="utf-8")
    store = DiskStore(tmp_path / "store")
    with pytest.raises(RuntimeError, match="prompt"):
        seed(store, version_file=version_file)
    assert not (tmp_path / "store").exists()
```

- [ ] **Step 3: Run them to see them fail**

Run: `.venv/bin/python -m pytest tests/test_seed_cache.py -q`
Expected: `ModuleNotFoundError: No module named 'seed_cache'`.

- [ ] **Step 4: Write `seed_cache.py`**

```python
"""
Saves the 4 benchmark fixtures into the extraction cache so those filings load without a Gemini call.
Refuses to run if the prompt changed since the fixtures were made.

Usage: python seed_cache.py   (uses R2 when the R2 secrets are in the environment, else .cache/)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from cache import ExtractionCache, ObjectStore, make_store, prompt_version
from fetch import DEALS_TO_FETCH


def seed(
    store: ObjectStore,
    fixtures_dir: Path = Path("data/fixtures"),
    version_file: Path = Path("data/fixtures/PROMPT_VERSION"),
) -> list[str]:
    expected = Path(version_file).read_text(encoding="utf-8").strip()
    current = prompt_version()
    if expected != current:
        raise RuntimeError(
            f"The prompt changed since the fixtures were made ({expected} vs {current}). "
            "Regenerate the fixtures and update PROMPT_VERSION first."
        )
    cache = ExtractionCache(store, version=current)
    written: list[str] = []
    for deal in DEALS_TO_FETCH:
        matches = sorted(Path(fixtures_dir).glob(f"{deal['label']}_*_extractions.jsonl"))
        if len(matches) != 1:
            raise RuntimeError(f"Expected one fixture for {deal['label']}, found {len(matches)}.")
        cache.put(deal["accession"], matches[0].read_text(encoding="utf-8"))
        written.append(deal["accession"])
    return written


if __name__ == "__main__":
    load_dotenv()
    store = make_store(os.environ)
    try:
        accessions = seed(store)
    except RuntimeError as e:
        print(f"Not seeded: {e}")
        sys.exit(1)
    print(f"Seeded {len(accessions)} filings into {type(store).__name__} under prompt version {prompt_version()}.")
```

- [ ] **Step 5: Run the tests**

Run: `.venv/bin/python -m pytest tests/test_seed_cache.py -q`
Expected: all pass. Do **not** run `python seed_cache.py` itself; with R2 secrets in `.env` it would write to real R2.

- [ ] **Step 6: Commit**

```bash
git add seed_cache.py data/fixtures/PROMPT_VERSION tests/test_seed_cache.py
git commit -m "feat: add cache seed script for benchmark deals"
```

---

### Task 6: Keep-alive job

**Files:**
- Create: `scripts/keep_alive.py`, `.github/workflows/keep-alive.yml`

**Interfaces:**
- Consumes: nothing from earlier tasks. Reads `APP_URL` from the environment.
- Produces: a workflow named `keep-alive` that Claude triggers by hand after merge.

The app runs inside an iframe on `*.streamlit.app`. A sleeping app shows a button "Yes, get this app back up!" on the outer page. The job passes when the Streamlit root (`[data-testid="stApp"]`) appears inside the app frame. This check survives the slice 10 page rewrite.

- [ ] **Step 1: Write `scripts/keep_alive.py`**

```python
"""
Opens the deployed app, wakes it if Streamlit Cloud put it to sleep, and exits non-zero if it never loads.
Run by .github/workflows/keep-alive.yml.
"""

import os
import sys

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

APP_URL = os.environ.get("APP_URL", "https://bond-term-sheet-extractor-diwsf7fvsovutxsajuanis.streamlit.app/")
WAKE_BUTTON = "Yes, get this app back up!"
LOAD_TIMEOUT_MS = 180_000


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(APP_URL, wait_until="domcontentloaded", timeout=60_000)
        wake = page.get_by_role("button", name=WAKE_BUTTON)
        if wake.count() > 0:
            print("App was asleep. Waking it.")
            wake.click()
        try:
            page.frame_locator("iframe").first.locator('[data-testid="stApp"]').wait_for(timeout=LOAD_TIMEOUT_MS)
        except PlaywrightTimeout:
            print("App did not load in time.")
            browser.close()
            return 1
        print("App is up.")
        browser.close()
        return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Write `.github/workflows/keep-alive.yml`**

Look up the newest `playwright` version with `.venv/bin/pip index versions playwright` and use it in place of `<VERSION>` below.

```yaml
name: keep-alive

on:
  schedule:
    - cron: "17 */6 * * *"
  workflow_dispatch:

permissions:
  contents: read

jobs:
  wake:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install Playwright
        run: |
          pip install playwright==<VERSION>
          python -m playwright install --with-deps chromium
      - name: Open the app
        run: python scripts/keep_alive.py
```

- [ ] **Step 3: Check the YAML parses**

Run: `.venv/bin/python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/keep-alive.yml')); print('ok')"`
Expected: `ok`. If `yaml` is not installed, run `.venv/bin/pip install pyyaml` first and do not add it to `requirements.txt`.

- [ ] **Step 4: Commit**

```bash
git add scripts/keep_alive.py .github/workflows/keep-alive.yml
git commit -m "ci: wake the app every six hours"
```

---

### Task 7: Final checks and report

- [ ] **Step 1: Run every check and keep the output**

```bash
.venv/bin/python -m pytest -q -rxX
.venv/bin/python evaluate.py
timeout 15 .venv/bin/streamlit run app.py --server.headless true
git log --oneline master..slice-09-cache
git diff --stat master
```

`evaluate.py` must still print `Field accuracy: 98.3% (344/350 fields, 4 deals, 25 tranches)`. Do not commit `output/accuracy_benchmark_report.md` if only its run log changed.

- [ ] **Step 2: Write `docs/plans/09-cache-backend-report.md`** with:
  1. Each task: done or not, commit hash.
  2. The boto3 and playwright versions pinned.
  3. The value in `data/fixtures/PROMPT_VERSION`.
  4. Every test added, changed or deleted, and why.
  5. Anything skipped, unsure or not done, and any rule you could not follow.
  6. What a reviewer should look at first.
  7. The pasted output from Step 1.

- [ ] **Step 3: Commit the report**

```bash
git add docs/plans/09-cache-backend-report.md
git commit -m "docs: add slice 9 report"
```

Then stop.

## After agy: Claude and Aidin

1. Claude reviews the branch and reruns Step 1.
2. Aidin creates the R2 bucket and an API token scoped to it (steps in the chat), and adds the four `R2_*` values to `.env` and to the app's Streamlit secrets.
3. Claude runs `python seed_cache.py` once and confirms it prints `Seeded 4 filings into R2Store`.
4. Claude merges and pushes, triggers `keep-alive` by hand with `gh workflow run keep-alive.yml`, checks it passes, and checks in a browser that an AAPL search shows "saved" and loads without spending a run.
