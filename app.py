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
