"""
Results view shared by the Search and Upload tabs: deal line, comps table,
source panel for the selected cell and the Excel download.
"""

from __future__ import annotations

import html
import io
import re
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from structure import structure_filing_extractions
from theme import NOT_EXACT_TINT
from ui import (
    TABLE_COLUMNS,
    cell_source,
    load_document_text,
    not_exact_mask,
    size_help,
    size_label,
    table_frame,
)
from validate import validate_comps_table

STATUS_TAGS = {
    "Found word for word": "WORD FOR WORD",
    "Found, but the match is not exact": "NOT EXACT",
    "Not in the filing": "NOT IN THE FILING",
}
EMPTY_PANEL_TEXT = "Click a number in the table to see where it came from."
LEGEND_TEXT = "Amber cells do not match the filing text word for word. Click one to compare."
DOWNLOAD_LABEL = "Download Excel"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
SIZE_FORMATS = {
    "Size ($M)": "$%,.1fM",
    "Size (€M)": "€%,.1fM",
    "Size (£M)": "£%,.1fM",
    "Size (¥M)": "¥%,.1fM",
}


def build_deal_line(df: pd.DataFrame) -> str:
    """Constructs sell-side research summary line from comps dataframe."""
    issuer = "Unknown Issuer"
    if "Issuer" in df.columns:
        issuers = df["Issuer"].dropna()
        if not issuers.empty:
            raw_iss = str(issuers.iloc[0]).strip()
            issuer = raw_iss.title() if raw_iss.isupper() else raw_iss

    principal_col = None
    for col in ["Principal ($M)", "Size ($M)"]:
        if col in df.columns:
            principal_col = col
            break
    if not principal_col:
        for col in df.columns:
            if col.startswith("Principal (") or col.startswith("Size ("):
                principal_col = col
                break

    totals_by_curr: dict[str, float] = {}
    curr_order: list[str] = []
    if principal_col:
        for _, row in df.iterrows():
            val = row[principal_col]
            if pd.isna(val):
                continue
            amt = 0.0
            if isinstance(val, (int, float)):
                amt = float(val)
            else:
                s = str(val).strip().replace(",", "")
                m = re.search(r"([0-9]+(?:\.[0-9]+)?)", s)
                if m:
                    amt = float(m.group(1))
            c = "USD"
            if "Currency" in df.columns and pd.notna(row["Currency"]):
                raw_c = str(row["Currency"]).strip()
                if raw_c:
                    c = raw_c
            if c not in totals_by_curr:
                totals_by_curr[c] = 0.0
                curr_order.append(c)
            totals_by_curr[c] += amt

    size_parts: list[str] = []
    syms = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥"}
    for c in curr_order:
        total_m = totals_by_curr[c]
        sym = syms.get(c, "$")
        if total_m >= 1000:
            val = total_m / 1000.0
            size_parts.append(f"{sym}{int(val)}bn" if val.is_integer() else f"{sym}{val:.1f}bn")
        else:
            size_parts.append(f"{sym}{int(total_m):,d}m" if total_m.is_integer() else f"{sym}{total_m:,.1f}m")

    if not size_parts:
        size_str = "$0m"
    elif len(size_parts) == 1:
        size_str = size_parts[0]
    elif len(size_parts) == 2:
        size_str = f"{size_parts[0]} and {size_parts[1]}"
    else:
        size_str = f"{', '.join(size_parts[:-1])} and {size_parts[-1]}"

    n_bonds = len(df)
    bond_str = f"{n_bonds} bond" if n_bonds == 1 else f"{n_bonds} bonds"

    priced_str = ""
    for col in ["Trade Date", "Trade date"]:
        if col in df.columns:
            dates = df[col].dropna()
            if not dates.empty and str(dates.iloc[0]).strip():
                priced_str = f"priced {dates.iloc[0]}"
                break

    parts = [issuer, f"{size_str} senior notes", bond_str]
    if priced_str:
        parts.append(priced_str)
    return " · ".join(parts)


def status_tag(status: str) -> str:
    return STATUS_TAGS.get(status, status.upper())


def source_panel_html(cs: dict[str, Any]) -> str:
    """Card for one clicked cell. quote_html is already escaped by ui.source_quote."""
    parts = [
        f'<div class="tse-label">{html.escape(cs["field"])} · {html.escape(cs["tranche"])}</div>',
        f'<div class="tse-value">{html.escape(cs["value"])}</div>',
        f'<span class="tse-tag">{status_tag(cs["status"])}</span>',
    ]
    if cs["quote_html"]:
        parts.append(f'<div class="tse-quote">{cs["quote_html"]}</div>')
    return "".join(parts)


def _currencies(validated_df: pd.DataFrame) -> list[str]:
    if "Currency" not in validated_df.columns:
        return []
    return [c for c in validated_df["Currency"].dropna().unique() if c]


def column_config_for(validated_df: pd.DataFrame) -> dict[str, Any]:
    """Same columns, formats and help text as the old page."""
    curs = _currencies(validated_df)
    current_size_label = size_label(curs)
    config: dict[str, Any] = {}
    for col_label, _, _, col_help in TABLE_COLUMNS:
        if col_label == "Size ($M)":
            fmt = SIZE_FORMATS.get(current_size_label)
            if fmt is None:
                config[current_size_label] = st.column_config.Column(current_size_label, help=size_help(curs))
            else:
                config[current_size_label] = st.column_config.NumberColumn(current_size_label, help=size_help(curs), format=fmt)
        elif col_label in ("Coupon", "Yield"):
            config[col_label] = st.column_config.NumberColumn(col_label, help=col_help, format="%.3f%%")
        elif col_label == "Price":
            config[col_label] = st.column_config.NumberColumn(col_label, help=col_help, format="%.3f")
        else:
            config[col_label] = st.column_config.Column(
                col_label, help=col_help, width="large" if col_label == "Check" else None
            )
    return config


def excel_bytes(validated_df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        validated_df.to_excel(writer, sheet_name="Comps Table", index=False)
    return buffer.getvalue()


def needs_legend(mask: pd.DataFrame) -> bool:
    return bool(mask.values.any())


def _render_table(
    validated_df: pd.DataFrame, audit_records: list[dict[str, Any]], key: str
) -> tuple[tuple[int, str] | None, bool]:
    """Draws the comps table and returns the selected (row, column label), if any, and whether legend is needed."""
    tf = table_frame(validated_df, audit_records)
    mask = not_exact_mask(validated_df, audit_records)

    def tint(data: pd.DataFrame) -> pd.DataFrame:
        styles = pd.DataFrame("", index=data.index, columns=data.columns)
        for col in data.columns:
            if col in mask.columns:
                styles[col] = [f"background-color: {NOT_EXACT_TINT}" if flag else "" for flag in mask[col]]
        return styles

    table_key = f"comps_{key}"
    st.dataframe(
        tf.style.apply(tint, axis=None),
        hide_index=True,
        on_select="rerun",
        selection_mode="single-cell",
        key=table_key,
        column_config=column_config_for(validated_df),
        selection_default={"selection": {"cells": [(0, "Coupon")] if len(tf) > 0 else []}},
    )
    show_legend = needs_legend(mask)
    state = st.session_state.get(table_key)
    cells = state.get("selection", {}).get("cells", []) if isinstance(state, dict) else []
    if not cells:
        return None, show_legend
    row, col = cells[0]
    return (int(row), str(col)), show_legend


def render_results(jsonl_path: Path, key: str, file_stem: str) -> None:
    df, audit_records = structure_filing_extractions(jsonl_path)
    validated_df = validate_comps_table(df, audit_records)
    st.html(f'<div class="tse-deal">{html.escape(build_deal_line(validated_df))}</div>')

    left, right = st.columns([2, 1], gap="medium")
    with left:
        selected, show_legend = _render_table(validated_df, audit_records, key)
        if show_legend:
            st.html(f'<div class="tse-legend"><i></i>{html.escape(LEGEND_TEXT)}</div>')
        st.download_button(
            DOWNLOAD_LABEL,
            data=excel_bytes(validated_df),
            file_name=f"{file_stem}_comps_table.xlsx",
            mime=XLSX_MIME,
            key=f"download_{key}",
        )
    with right:
        with st.container(border=True, key=f"source_panel_{key}"):
            cs = None
            if selected is not None:
                cs = cell_source(audit_records, selected[0], selected[1], validated_df, load_document_text(jsonl_path))
            if cs is None:
                st.html(f'<div class="tse-muted">{html.escape(EMPTY_PANEL_TEXT)}</div>')
            else:
                st.html(source_panel_html(cs))
