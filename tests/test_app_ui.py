import re
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest


def is_emoji(char: str) -> bool:
    cp = ord(char)
    return (0x1F300 <= cp <= 0x1FAFF) or (0x2600 <= cp <= 0x27BF)


BANNED_WORDS = [
    "engine",
    "hallucination",
    "ground truth",
    "proprietary",
    "ai-native",
    "trustworthiness",
    "gate",
    "analyst-ready",
]


APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")


class TestAppUi:
    def test_app_runs_no_exceptions_and_defaults_to_aapl(self):
        at = AppTest.from_file(APP_PATH, default_timeout=30).run()
        assert not at.exception
        # AAPL deal is selected / displayed
        # Check title
        assert any("Bond Term Sheet Extractor" in t.value for t in at.title)
        # Check selectbox has AAPL or "Apple Inc."
        assert len(at.selectbox) > 0
        assert "AAPL" in at.selectbox[0].value or "Apple" in at.selectbox[0].value

    def test_comps_table_html_contains_coupons_and_no_index(self):
        at = AppTest.from_file(APP_PATH, default_timeout=30).run()
        assert not at.exception
        html_contents = [h.value for h in at.get("html")]
        table_html = next((h for h in html_contents if "<table" in h), None)
        assert table_html is not None, "Comps table HTML element not found"
        assert "4.000%" in table_html
        assert "4.200%" in table_html
        # No index column: exactly 11 th tags
        assert table_html.count("</th>") == 11

    def test_select_2030_in_segmented_control_shows_quote_with_mark(self):
        at = AppTest.from_file(APP_PATH, default_timeout=30).run()
        assert not at.exception
        assert len(at.segmented_control) > 0
        sc = at.segmented_control[0]
        # Find option for 2030
        opt_2030 = next((opt for opt in sc.options if "2030" in str(opt)), None)
        assert opt_2030 is not None, f"Option for 2030 not found in {sc.options}"
        sc.set_value(opt_2030).run()
        assert not at.exception

        html_contents = [h.value for h in at.get("html")]
        # Should show a source row whose quote contains 4.200% inside <mark>
        matching = [h for h in html_contents if "<mark>4.200%</mark>" in h]
        assert len(matching) > 0, "Source quote with <mark>4.200%</mark> not found"

    def test_no_emoji_and_no_banned_words(self):
        at = AppTest.from_file(APP_PATH, default_timeout=30).run()
        assert not at.exception

        # Collect all text strings rendered or used in widgets
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
            # Check for emoji ranges
            for ch in text:
                assert not is_emoji(ch), f"Emoji '{ch}' (U+{ord(ch):04X}) found in text: {text[:100]}"

            # Check for banned words (case-insensitive)
            lower = text.lower()
            for banned in BANNED_WORDS:
                pattern = rf"\b{re.escape(banned)}\b"
                assert not re.search(pattern, lower), f"Banned word '{banned}' found in text: {text[:100]}"

    def test_no_sidebar_content(self):
        at = AppTest.from_file(APP_PATH, default_timeout=30).run()
        assert not at.exception
        assert len(at.sidebar) == 0


def test_scoring_change_line_shows_first_score():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file("../app.py")
    at.run(timeout=20)
    lines = [m.value for m in at.markdown if "First scored" in m.value]
    assert lines and "88.0% (308/350)" in lines[0]


def test_css_does_not_override_theme_fonts():
    source = (Path(__file__).resolve().parent.parent / "app.py").read_text(encoding="utf-8")
    assert "font-family" not in source
