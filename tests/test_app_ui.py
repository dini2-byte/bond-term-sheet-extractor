import re
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest


def is_emoji(char: str) -> bool:
    cp = ord(char)
    return (0x1F300 <= cp <= 0x1FAFF) or (0x2600 <= cp <= 0x27BF)


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


APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")


class TestAppUi:
    def test_app_runs_no_exceptions_and_defaults_to_aapl(self):
        at = AppTest.from_file(APP_PATH, default_timeout=30).run()
        assert not at.exception
        assert any("Bond Term Sheet Extractor" in t.value for t in at.title)
        assert len(at.selectbox) > 0
        sb = at.selectbox[0]
        assert sb.label == "Saved deals"
        assert "AAPL" in sb.value or "Apple" in sb.value

    def test_one_dataframe_with_single_cell_selection_mode(self):
        at = AppTest.from_file(APP_PATH, default_timeout=30).run()
        assert not at.exception
        assert len(at.dataframe) == 1
        df_widget = at.dataframe[0]
        from streamlit.proto.Dataframe_pb2 import Dataframe
        assert Dataframe.SelectionMode.SINGLE_CELL in df_widget.proto.selection_mode

    def test_step_3_card_shows_4_000_pct_on_first_load(self):
        at = AppTest.from_file(APP_PATH, default_timeout=30).run()
        assert not at.exception
        # On first load, Coupon (4.000%) of first row is selected in step 3 card
        all_text = " ".join([h.value for h in at.get("html")] + [m.value for m in at.markdown])
        assert "4.000%" in all_text
        assert "Found word for word" in all_text

    def test_three_step_subheaders_in_order(self):
        at = AppTest.from_file(APP_PATH, default_timeout=30).run()
        assert not at.exception
        subheaders = [s.value for s in at.subheader]
        assert "1. Pick a deal" in subheaders
        assert "2. Read the table" in subheaders
        assert "3. Check any number" in subheaders
        idx1 = subheaders.index("1. Pick a deal")
        idx2 = subheaders.index("2. Read the table")
        idx3 = subheaders.index("3. Check any number")
        assert idx1 < idx2 < idx3

    def test_no_emoji_and_no_never_show_words(self):
        at = AppTest.from_file(APP_PATH, default_timeout=30).run()
        assert not at.exception

        collected_texts: list[str] = []
        for t in at.title:
            collected_texts.append(t.value)
        for h in at.header:
            collected_texts.append(h.value)
        for s in at.subheader:
            collected_texts.append(s.value)
        for m in at.markdown:
            collected_texts.append(m.value)
        for c in at.caption:
            collected_texts.append(c.value)
        for h in at.get("html"):
            collected_texts.append(h.value)
        for sb in at.selectbox:
            collected_texts.append(sb.label)
        for sc in at.segmented_control:
            collected_texts.append(sc.label)
            collected_texts.extend(str(opt) for opt in sc.options)
        for db in at.download_button:
            collected_texts.append(db.label)
        for exp in at.expander:
            collected_texts.append(exp.label)
        for btn in at.button:
            collected_texts.append(btn.label)

        for text in collected_texts:
            for ch in text:
                assert not is_emoji(ch), f"Emoji '{ch}' (U+{ord(ch):04X}) found in text: {text[:100]}"
                assert ch != "—", f"Em dash found in text: {text[:100]}"
                assert ch != "–", f"En dash found in text: {text[:100]}"

            lower = text.lower()
            for banned in NEVER_SHOW:
                pattern = rf"\b{re.escape(banned)}\b"
                assert not re.search(pattern, lower), f"Banned word '{banned}' found in text: {text[:100]}"

    def test_no_sidebar_content(self):
        at = AppTest.from_file(APP_PATH, default_timeout=30).run()
        assert not at.exception
        assert len(at.sidebar) == 0



def test_accuracy_note_replaces_how_well_section():
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()
    notes = [c.value for c in at.caption]
    assert any(
        "AI can make mistakes. On 4 hand-checked deals it got 98.3% of values right." in n
        for n in notes
    )
    assert "How well does it work?" not in [h.value for h in at.subheader]
    page_text = " ".join(m.value for m in at.markdown)
    assert "First scored" not in page_text
    assert "This deal:" not in page_text

def test_css_does_not_override_theme_fonts():
    source = (Path(__file__).resolve().parent.parent / "app.py").read_text(encoding="utf-8")
    assert "font-family" not in source


class TestCompanyLookupUi:
    def test_lookup_shows_not_set_up_when_no_identity(self, monkeypatch):
        monkeypatch.delenv("EDGAR_IDENTITY", raising=False)
        at = AppTest.from_file(APP_PATH, default_timeout=30).run()
        assert not at.exception
        assert len(at.segmented_control) > 0
        at.segmented_control[0].select("Search company").run()
        assert not at.exception
        all_info = [i.value for i in at.info]
        assert any("Company lookup is not set up on this deployment." in inf for inf in all_info)

    def test_lookup_and_extract_flow(self, monkeypatch, tmp_path):
        monkeypatch.setenv("EDGAR_IDENTITY", "Test User test@example.com")
        fake_sheet = {
            "accession": "0001-26-000001",
            "filing_date": "2026-08-10",
            "chars": 1500,
            "bond_count": 1,
            "text": "Pricing Term Sheet\nIssuer: KO Corp\n3.000% Notes due 2030\nCUSIP: 123456AA1",
        }
        import lookup
        monkeypatch.setattr(lookup, "find_term_sheets", lambda ticker, **kw: [fake_sheet])

        # Mock extract_terms to write a valid jsonl from fixture
        sample_jsonl = Path("data/fixtures/AAPL_FWP_TermSheet_2025-05-06_extractions.jsonl").read_text(encoding="utf-8")
        def fake_extract_terms(path, **kw):
            out_dir = kw.get("output_dir", path.parent)
            out_file = Path(out_dir) / f"{path.stem}_extractions.jsonl"
            out_file.write_text(sample_jsonl, encoding="utf-8")
            return out_file

        import extract
        monkeypatch.setattr(extract, "extract_terms", fake_extract_terms)
        import demo
        monkeypatch.setattr(demo, "get_gemini_api_key", lambda secrets=None: "fake-key")
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        monkeypatch.setenv("GOOGLE_API_KEY", "fake-key")

        at = AppTest.from_file(APP_PATH, default_timeout=30).run()
        assert not at.exception
        at.segmented_control[0].select("Search company").run()
        assert not at.exception

        # Enter ticker and search
        at.text_input[0].input("KO")
        # Find term sheets button is present
        find_btn = [b for b in at.button if b.label == "Find term sheets"][0]
        find_btn.click().run()
        assert not at.exception

        # Radio options present
        assert len(at.radio) == 0
        picker = [s for s in at.selectbox if s.label == "Recent bond term sheets"][0]
        assert "Filed 2026-08-10 · 1 bond" in picker.options[0]

        # Extract button is present
        extract_btn = [b for b in at.button if b.label == "Extract"][0]
        extract_btn.click().run()
        assert not at.exception

        # The deal line reads '<TICKER> · term sheet filed <date> · live run'
        markdowns = [m.value for m in at.markdown]
        assert any("KO · term sheet filed 2026-08-10 · live run" in m for m in markdowns)
        # Muted line under step 2
        assert any("Live run: there is no hand-checked answer for this deal" in m for m in markdowns)

    def test_budget_exhausted_shows_cap_message_and_blocks_extract(self, monkeypatch):
        monkeypatch.setenv("EDGAR_IDENTITY", "Test User test@example.com")
        fake_sheet = {
            "accession": "0001-26-000001",
            "filing_date": "2026-08-10",
            "chars": 1500,
            "bond_count": 1,
            "text": "Pricing Term Sheet\nIssuer: KO Corp\n3.000% Notes due 2030\nCUSIP: 123456AA1",
        }
        import lookup
        monkeypatch.setattr(lookup, "find_term_sheets", lambda ticker, **kw: [fake_sheet])

        # Exhaust budget
        import streamlit as st
        st.cache_resource.clear()
        exhausted_budget = lookup.RunBudget(daily_limit=20)
        for _ in range(20):
            exhausted_budget.record_run()
        monkeypatch.setattr(lookup, "RunBudget", lambda *a, **kw: exhausted_budget)

        extract_called = []
        import extract
        monkeypatch.setattr(extract, "extract_terms", lambda *a, **kw: extract_called.append(True))

        at = AppTest.from_file(APP_PATH, default_timeout=30).run()
        at.segmented_control[0].select("Search company").run()
        at.text_input[0].input("KO")
        find_btn = [b for b in at.button if b.label == "Find term sheets"][0]
        find_btn.click().run()

        extract_btn = [b for b in at.button if b.label == "Extract"][0]
        extract_btn.click().run()
        assert not at.exception
        assert len(extract_called) == 0

        errors = [e.value for e in at.error]
        assert any("Today's 20 free runs are used up. Try again tomorrow." in err for err in errors)




def test_lookup_extract_without_gemini_key_shows_message(monkeypatch):
    monkeypatch.setenv("EDGAR_IDENTITY", "Test User test@example.com")
    fake_sheet = {
        "accession": "0001-26-000001",
        "filing_date": "2026-08-10",
        "chars": 1500,
        "bond_count": 1,
        "text": "Pricing Term Sheet\n3.000% Notes due 2030\nCUSIP: 123456AA1",
    }
    import lookup, extract, demo
    import streamlit as st
    st.cache_data.clear()
    st.cache_resource.clear()
    monkeypatch.setattr(lookup, "find_term_sheets", lambda ticker, **kw: [fake_sheet])
    calls = []
    monkeypatch.setattr(extract, "extract_terms", lambda *a, **kw: calls.append(a))
    monkeypatch.setattr(demo, "get_gemini_api_key", lambda secrets=None: None)

    at = AppTest.from_file(APP_PATH, default_timeout=30).run()
    at.segmented_control[0].select("Search company").run()
    at.text_input[0].input("KO")
    [b for b in at.button if b.label == "Find term sheets"][0].click().run()
    [b for b in at.button if b.label == "Extract"][0].click().run()

    assert not at.exception
    assert any("Live extraction is not set up on this deployment." in e.value for e in at.error)
    assert calls == []


def test_headings_have_no_link_anchor():
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()
    headings = list(at.title) + list(at.subheader)
    assert headings
    assert all(h.proto.hide_anchor for h in headings)




class TestSearchPickerCurrencyLabel:
    def test_search_picker_labels_include_currency(self, monkeypatch):
        monkeypatch.setenv("EDGAR_IDENTITY", "Test User test@example.com")
        fake_sheets = [
            {
                "accession": "0001-24-000001",
                "filing_date": "2024-08-09",
                "chars": 1500,
                "bond_count": 2,
                "currencies": ["EUR"],
                "text": "sample text",
            },
            {
                "accession": "0001-26-000002",
                "filing_date": "2026-07-27",
                "chars": 1500,
                "bond_count": 1,
                "currencies": ["GBP"],
                "text": "sample text",
            },
            {
                "accession": "0001-26-000003",
                "filing_date": "2026-07-27",
                "chars": 1500,
                "bond_count": 5,
                "currencies": ["EUR", "GBP"],
                "text": "sample text",
            },
            {
                "accession": "0001-25-000004",
                "filing_date": "2025-05-06",
                "chars": 1500,
                "bond_count": 4,
                "currencies": ["USD"],
                "text": "sample text",
            },
        ]
        import lookup
        import streamlit as st
        st.cache_data.clear()
        monkeypatch.setattr(lookup, "find_term_sheets", lambda ticker, **kw: fake_sheets)

        at = AppTest.from_file(APP_PATH, default_timeout=30).run()
        at.segmented_control[0].select("Search company").run()
        at.text_input[0].input("KO")
        [b for b in at.button if b.label == "Find term sheets"][0].click().run()

        assert not at.exception
        sb = at.selectbox[0]
        assert sb.options[0] == "Filed 2024-08-09 · 2 bonds in euros"
        assert sb.options[1] == "Filed 2026-07-27 · 1 bond in pounds"
        assert sb.options[2] == "Filed 2026-07-27 · 5 bonds in euros and pounds"
        assert sb.options[3] == "Filed 2025-05-06 · 4 bonds"

