"""Upload term sheet tab: one live run on a .txt term sheet. Uploads are never saved."""

from __future__ import annotations

import hashlib
import html
import tempfile
from pathlib import Path
from typing import Any

import streamlit as st

import demo
from lookup import RunBudget
from runner import run_upload
from views.results import render_results
from views.search import EXTRACT_LABEL, runs_hint

HEADING = "Extract terms from your own term sheet"
SUBLINE = "Upload a pricing term sheet saved as a .txt file, up to 500 KB. Uploads are not saved."
NOT_TEXT = "The file is not plain text. Save it as .txt and try again."
STEM = "uploaded_term_sheet"


def render_upload(budget: RunBudget, secrets: dict[str, Any] | None) -> None:
    st.header(HEADING, anchor=False)
    st.html(f'<div class="tse-muted">{html.escape(SUBLINE)}</div>')
    uploaded = st.file_uploader("Term sheet (.txt)", type=["txt"], label_visibility="collapsed", key="upload_file")
    st.html(f'<div class="tse-hint">{html.escape(runs_hint(budget.remaining(), budget.daily_limit))}</div>')
    if uploaded is None:
        st.session_state.pop("upload_result", None)
        return

    content = uploaded.getvalue()
    ok, size_error = demo.check_upload_size(len(content))
    if not ok:
        st.error(size_error)
        return
    digest = hashlib.sha256(content).hexdigest()

    result = st.session_state.get("upload_result")
    if result is None or result["digest"] != digest:
        if not st.button(EXTRACT_LABEL, type="primary", key="upload_extract"):
            return
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            st.error(NOT_TEXT)
            return
        with st.spinner("Extracting with Gemini. This takes about 20 seconds."):
            outcome = run_upload(
                filing_text=text,
                stem=STEM,
                budget=budget,
                session_runs=st.session_state.get("session_runs", 0),
                api_key=demo.get_gemini_api_key(secrets),
                work_dir=Path(tempfile.mkdtemp()),
            )
        if outcome.error:
            st.error(outcome.error)
            return
        st.session_state["session_runs"] = st.session_state.get("session_runs", 0) + 1
        st.session_state["upload_result"] = {"digest": digest, "jsonl_path": str(outcome.jsonl_path)}
        st.rerun()

    path = Path(result["jsonl_path"])
    if not path.is_file():
        st.session_state.pop("upload_result", None)
        return
    render_results(path, key="upload", file_stem=STEM)
