"""
ui.py: Pure render helpers and UI presentation utilities for the comps table app.
No Streamlit imports; all functions are independently testable.
"""

from collections import OrderedDict
import json
from pathlib import Path
from typing import Any

# Scored fields: 14 pairs from comps table column name to extraction field class.
# Preserves order matching evaluate.py field_class_map.
SCORED_FIELDS: dict[str, str] = OrderedDict([
    ("Issuer", "issuer"),
    ("Ratings", "ratings"),
    ("Trade Date", "trade_date"),
    ("Settlement Date", "settlement_date"),
    ("Principal ($M)", "principal_amount"),
    ("Coupon (%)", "coupon"),
    ("Issue Price", "issue_price"),
    ("Yield (%)", "yield_to_maturity"),
    ("Spread (bps)", "spread_bps"),
    ("Benchmark Treasury", "benchmark_treasury"),
    ("Maturity Date", "maturity_date"),
    ("Day Count", "day_count"),
    ("Par Call Date", "par_call_date"),
    ("CUSIP", "cusip"),
])


def load_document_text(jsonl_path: str | Path) -> str:
    """Returns the text value from the first line of a fixture JSONL."""
    path = Path(jsonl_path)
    if not path.exists():
        raise FileNotFoundError(f"Fixture file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        line = f.readline()
        if not line:
            return ""
        data = json.loads(line)
        return data.get("text", "")


def scored_grounding(audit_records: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Computes grounded count, extracted count, and percent across all tranches,
    counting only the 14 scored field classes and only fields that were extracted
    (not 'Not found' or None).
    """
    scored_field_classes = set(SCORED_FIELDS.values())
    grounded = 0
    extracted = 0

    for record in audit_records:
        fields = record.get("fields", {})
        for field_class in scored_field_classes:
            meta = fields.get(field_class)
            if not meta:
                continue
            raw = meta.get("raw")
            if raw is None or (isinstance(raw, str) and raw.strip().lower() == "not found"):
                continue
            extracted += 1
            if meta.get("grounded") is True:
                grounded += 1

    percent = (grounded / extracted * 100.0) if extracted > 0 else 0.0
    return {
        "grounded": grounded,
        "extracted": extracted,
        "percent": percent,
        "pct": percent,
    }


def source_quote(
    doc_text: str,
    start: int | None,
    end: int | None,
    context: int = 60,
) -> str:
    """
    Returns an HTML quote around character span [start:end] in doc_text.
    Up to context characters before and after the span, whitespace collapsed,
    the span wrapped in <mark>, and leading/trailing ellipsis when text was cut.
    Every piece of filing text goes through html.escape before <mark> tags are added.
    """
    import html

    if not doc_text or start is None or end is None:
        return ""
    if start < 0:
        start = 0
    if end > len(doc_text):
        end = len(doc_text)
    if start >= end or start >= len(doc_text):
        return ""

    prefix_start = max(0, start - context)
    suffix_end = min(len(doc_text), end + context)

    has_leading_cut = prefix_start > 0
    has_trailing_cut = suffix_end < len(doc_text)

    prefix_raw = doc_text[prefix_start:start]
    span_raw = doc_text[start:end]
    suffix_raw = doc_text[end:suffix_end]

    # Drop the partial word at a cut edge so the quote never starts or ends mid-word.
    if has_leading_cut and not prefix_raw[:1].isspace():
        prefix_raw = prefix_raw.split(None, 1)[1] if len(prefix_raw.split(None, 1)) > 1 else ""
    if has_trailing_cut and not suffix_raw[-1:].isspace():
        suffix_raw = suffix_raw.rsplit(None, 1)[0] if len(suffix_raw.rsplit(None, 1)) > 1 else ""

    prefix_clean = " ".join(prefix_raw.split())
    span_clean = " ".join(span_raw.split())
    suffix_clean = " ".join(suffix_raw.split())

    prefix_esc = html.escape(prefix_clean)
    span_esc = html.escape(span_clean)
    suffix_esc = html.escape(suffix_clean)

    parts: list[str] = []
    if has_leading_cut:
        parts.append("...")
    if prefix_esc:
        parts.append(prefix_esc)
    parts.append(f"<mark>{span_esc}</mark>")
    if suffix_esc:
        parts.append(suffix_esc)
    if has_trailing_cut:
        parts.append("...")

    return " ".join(parts)


def comps_table_html(df: Any, audit_records: list[dict[str, Any]] | None = None) -> str:
    """
    Renders an HTML <table> wrapped in <div class="table-wrap">.
    Columns in exact order:
    Tranche, Size ($M), Coupon, Price, Yield, Spread (bps), Benchmark, Maturity, Par call, CUSIP, Checks.
    No index column. Numbers right-aligned with standard app formatting.
    Extracted but ungrounded values receive a <sup>†</sup> dagger.
    Missing values show '<span class="muted">n/a</span>'.
    All cell values are escaped with html.escape.
    """
    import html
    import pandas as pd

    records = audit_records or []

    # Column specifications: (Display Name, Candidate df keys, field_class, is_numeric)
    col_specs = [
        ("Tranche", ["Tranche"], None, False),
        ("Size ($M)", ["Size ($M)", "Principal ($M)"], "principal_amount", True),
        ("Coupon", ["Coupon", "Coupon (%)"], "coupon", True),
        ("Price", ["Price", "Issue Price"], "issue_price", True),
        ("Yield", ["Yield", "Yield (%)"], "yield_to_maturity", True),
        ("Spread (bps)", ["Spread (bps)", "Spread"], "spread_bps", True),
        ("Benchmark", ["Benchmark", "Benchmark Treasury"], "benchmark_treasury", False),
        ("Maturity", ["Maturity", "Maturity Date"], "maturity_date", False),
        ("Par call", ["Par call", "Par Call Date"], "par_call_date", False),
        ("CUSIP", ["CUSIP"], "cusip", False),
        ("Checks", ["Checks", "Validation Status"], None, False),
    ]

    lines = ['<div class="table-wrap">', "<table>", "<thead>", "<tr>"]
    for header, _, _, is_num in col_specs:
        align = ' class="num" style="text-align: right;"' if is_num else ""
        lines.append(f"<th{align}>{html.escape(header)}</th>")
    lines.extend(["</tr>", "</thead>", "<tbody>"])

    if hasattr(df, "iterrows"):
        row_iter = df.iterrows()
    else:
        row_iter = enumerate(df)

    for row_idx, row in row_iter:
        fields = records[row_idx].get("fields", {}) if row_idx < len(records) else {}
        lines.append("<tr>")

        for col_name, keys, field_class, is_num in col_specs:
            val = None
            for k in keys:
                if k in row:
                    val = row[k]
                    break

            is_missing = False
            if val is None:
                is_missing = True
            elif isinstance(val, float) and pd.isna(val):
                is_missing = True
            elif isinstance(val, str) and val.strip().lower() in ("", "nan", "none", "not found", "n/a"):
                is_missing = True

            align = ' class="num" style="text-align: right;"' if is_num else ""

            if is_missing:
                cell_content = '<span class="muted">n/a</span>'
            else:
                formatted_str = ""
                if is_num and isinstance(val, (int, float)):
                    if col_name == "Size ($M)":
                        formatted_str = f"${float(val):,.1f}M"
                    elif col_name == "Coupon":
                        formatted_str = f"{float(val):.3f}%"
                    elif col_name == "Price":
                        formatted_str = f"{float(val):.3f}"
                    elif col_name == "Yield":
                        formatted_str = f"{float(val):.3f}%"
                    elif col_name == "Spread (bps)":
                        v_flt = float(val)
                        formatted_str = f"+{int(v_flt)} bps" if v_flt.is_integer() else f"+{v_flt} bps"
                    else:
                        formatted_str = str(val)
                elif col_name == "Checks":
                    formatted_str = str(val).capitalize()
                else:
                    formatted_str = str(val)

                cell_escaped = html.escape(formatted_str)

                # Check if extracted but not grounded
                dagger = ""
                if field_class and field_class in fields:
                    meta = fields[field_class]
                    raw = meta.get("raw")
                    raw_extracted = raw is not None and not (
                        isinstance(raw, str) and raw.strip().lower() in ("not found", "none", "n/a")
                    )
                    if raw_extracted and meta.get("grounded") is not True:
                        dagger = "<sup>†</sup>"

                cell_content = f"{cell_escaped}{dagger}"

            lines.append(f"<td{align}>{cell_content}</td>")
        lines.append("</tr>")

    lines.extend(["</tbody>", "</table>", "</div>"])
    return "".join(lines)


def field_rows(audit_entry: dict[str, Any], doc_text: str) -> list[dict[str, Any]]:
    """
    Returns one row per scored field for one tranche, in SCORED_FIELDS order.
    Keys: field, value, status ('exact', 'not exact', 'not found'),
    and quote_html (from source_quote, or an empty string when not found).
    """
    fields = audit_entry.get("fields", audit_entry) if isinstance(audit_entry, dict) else {}
    rows: list[dict[str, Any]] = []

    for col_name, field_class in SCORED_FIELDS.items():
        meta = fields.get(field_class) or {}
        raw = meta.get("raw")
        if raw is None or (isinstance(raw, str) and raw.strip().lower() in ("not found", "none", "n/a")):
            rows.append({
                "field": col_name,
                "value": "Not found",
                "status": "not found",
                "quote_html": "",
            })
            continue

        grounded = meta.get("grounded") is True
        status = "exact" if grounded else "not exact"

        interval = meta.get("char_interval")
        quote = ""
        if interval and "start_pos" in interval and "end_pos" in interval:
            quote = source_quote(doc_text, interval["start_pos"], interval["end_pos"])

        rows.append({
            "field": col_name,
            "value": str(raw),
            "status": status,
            "quote_html": quote,
        })

    return rows
