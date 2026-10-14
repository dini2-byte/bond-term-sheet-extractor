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

NEVER_SHOW = [
    "grounded",
    "not-in-source",
    "flagged",
    "passed",
    "engine",
    "hallucination",
    "ground truth",
    "proprietary",
    "ai-native",
    "trustworthiness",
    "gate",
    "not supported",
    "coming soon",
    "not implemented",
    "unavailable",
]

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
    from views.results import LEGEND_TEXT
    at, calls = search(monkeypatch, [SAVED_SHEET])
    assert at.radio[0].options[0].endswith("`SAVED`")
    at.radio[0].set_value(0).run()
    assert not at.exception
    assert calls == []
    text = all_text(at)
    assert "Apple Inc. · $4.5bn senior notes · 4 bonds" in text
    assert "4.000%" in text and "WORD FOR WORD" in text
    assert "20 of 20 runs left today" in text
    assert LEGEND_TEXT not in text
    assert len(at.dataframe) == 1
    from streamlit.proto.Dataframe_pb2 import Dataframe
    assert Dataframe.SelectionMode.SINGLE_CELL in at.dataframe[0].proto.selection_mode
    assert any(b.label == "Download Excel" for b in at.download_button)


def test_legend_shows_when_a_cell_is_not_exact(monkeypatch, isolated_store):
    from views.results import LEGEND_TEXT
    import json

    fixture_data = json.loads(AAPL_JSONL.strip().split("\n")[0])
    for item in fixture_data.get("extractions", []):
        if item.get("extraction_class") == "coupon":
            item["extraction_text"] = "9.999%"
            item["alignment_status"] = "match_lesser"
            break
    edited_jsonl = json.dumps(fixture_data) + "\n"

    calls: list = []

    def fake_extract(path, **kw):
        calls.append(path)
        out = Path(kw["output_dir"]) / f"{Path(path).stem}_extractions.jsonl"
        out.write_text(edited_jsonl, encoding="utf-8")
        return out

    monkeypatch.setenv("EDGAR_IDENTITY", "Test User test@example.com")
    monkeypatch.setattr(lookup, "find_term_sheets", lambda ticker, **kw: [NEW_SHEET])
    monkeypatch.setattr(demo, "get_gemini_api_key", lambda secrets=None: "fake-key")
    monkeypatch.setattr(extract, "extract_terms", fake_extract)

    at = open_app()
    at.text_input[0].input("AAPL")
    [b for b in at.button if b.label == "Find term sheets"][0].click().run()
    assert not at.exception
    at.radio[0].set_value(0).run()
    [b for b in at.button if b.label == "Extract · uses 1 run"][0].click().run()
    assert not at.exception
    assert len(calls) == 1
    assert LEGEND_TEXT in all_text(at)


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


def test_headings_have_no_link_anchor():
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()
    headings = list(at.header) + list(at.subheader)
    assert headings
    assert all(h.proto.hide_anchor for h in headings)
