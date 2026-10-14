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
