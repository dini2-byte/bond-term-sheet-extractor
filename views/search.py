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
