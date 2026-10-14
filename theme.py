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
[data-testid="stTab"][aria-selected="true"], [data-testid="stTab"][aria-selected="true"] p {{ color: inherit !important; font-weight: 600; }}
.react-aria-SelectionIndicator {{ background-color: currentColor !important; }}
[data-testid="stHeader"] {{ background: transparent; pointer-events: none; }}
[data-testid="stHeader"] * {{ pointer-events: none !important; }}
[data-testid="stHeader"] [data-testid="stMainMenu"], [data-testid="stHeader"] [data-testid="stMainMenu"] *, [data-testid="stHeader"] [data-testid="stStatusWidget"], [data-testid="stHeader"] [data-testid="stStatusWidget"] * {{ pointer-events: auto !important; }}
[data-testid="stRadio"], [data-testid="stRadio"] [role="radiogroup"] {{ width: 100%; }}
[data-testid="stRadio"] [role="radiogroup"] {{ max-height: 15.5rem; overflow-y: auto; flex-wrap: nowrap; }}
[data-testid="stRadio"] [role="radiogroup"] > div {{ width: 100%; }}
[data-testid="stRadioOption"] {{ width: 100%; box-sizing: border-box; padding: 0.5rem 0.75rem; border: 1px solid {LINE}; border-radius: 8px; margin-bottom: 0.25rem; }}
[data-testid="stRadioOption"][data-selected] {{ border-color: currentColor; }}
[class*="st-key-source_panel"] {{ backdrop-filter: blur(8px); }}
"""
