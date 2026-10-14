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
