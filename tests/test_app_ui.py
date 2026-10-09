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
]


APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")


class TestAppUi:
    def test_app_runs_no_exceptions_and_defaults_to_aapl(self):
        at = AppTest.from_file(APP_PATH, default_timeout=30).run()
        assert not at.exception
        assert any("Bond Term Sheet Extractor" in t.value for t in at.title)
        assert len(at.selectbox) > 0
        sb = at.selectbox[0]
        assert sb.label == "Sample deals"
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



def test_scoring_change_line_shows_first_score():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file("../app.py")
    at.run(timeout=20)
    lines = [m.value for m in at.markdown if "First scored" in m.value]
    assert lines and "88.0% (308/350)" in lines[0]


def test_css_does_not_override_theme_fonts():
    source = (Path(__file__).resolve().parent.parent / "app.py").read_text(encoding="utf-8")
    assert "font-family" not in source
