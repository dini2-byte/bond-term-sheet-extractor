"""
ui.py: Pure render helpers and UI presentation utilities for the comps table app.
No Streamlit imports; all functions are independently testable.
"""

from collections import OrderedDict
import html
import json
from pathlib import Path
import re
from typing import Any

import pandas as pd

from structure import normalize_ws

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

# Ordered list of (label, source_column, field_class, help_text) for the comps table.
TABLE_COLUMNS: list[tuple[str, str | None, str | None, str]] = [
    ("Tranche", "Tranche", None, "One bond in the deal. A deal often sells several bonds with different maturities."),
    ("Size ($M)", "Principal ($M)", "principal_amount", "Amount of this bond sold, in millions of dollars."),
    ("Coupon", "Coupon (%)", "coupon", "Yearly interest rate the issuer pays."),
    ("Price", "Issue Price", "issue_price", "Price paid per 100 of face value."),
    ("Yield", "Yield (%)", "yield_to_maturity", "Return to an investor who buys at the issue price and holds to maturity."),
    ("Spread (bps)", "Spread (bps)", "spread_bps", "Extra yield over the benchmark bond, in basis points (1 bp = 0.01%)."),
    ("Benchmark", "Benchmark Treasury", "benchmark_treasury", "The government bond the spread is measured against, such as a US Treasury, German Bund or UK Gilt."),
    ("Maturity", "Maturity Date", "maturity_date", "Date the bond is repaid."),
    ("Par call", "Par Call Date", "par_call_date", "Date after which the issuer can repay early at 100."),
    ("CUSIP", "CUSIP", "cusip", "The bond's 9-character ID."),
    ("Check", None, None, "OK, or the first thing worth checking in this row."),
]


def size_label(currencies: list[str] | set[str] | None) -> str:
    """Returns 'Size ($M)', 'Size (€M)', 'Size (£M)', or 'Size (M)' for multiple currencies."""
    if not currencies:
        return "Size ($M)"
    unique = sorted(set(currencies))
    if len(unique) > 1:
        return "Size (M)"
    cur = unique[0]
    symbol = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥"}.get(cur, "$")
    return f"Size ({symbol}M)"


def size_help(currencies: list[str] | set[str] | None) -> str:
    """Help text naming the currency of the deal."""
    if not currencies:
        return "Amount of this bond sold, in millions of dollars."
    unique = sorted(set(currencies))
    if len(unique) > 1:
        return "Amount of this bond sold, in millions."
    cur = unique[0]
    names = {"USD": "dollars", "EUR": "euros", "GBP": "pounds", "JPY": "yen"}
    name = names.get(cur)
    if name:
        return f"Amount of this bond sold, in millions of {name}."
    return "Amount of this bond sold, in millions."


def is_word_for_word(meta: dict[str, Any] | None) -> bool:
    """
    True when the cited span in the filing equals the extracted value.
    'fuzzy' grounding means langextract located the span loosely, but
    structure.assess_grounding has already checked the span text matches.
    Whitespace-only differences between span_text and raw are also word for word.
    """
    if not meta or not isinstance(meta, dict):
        return False
    if meta.get("grounded") is True or meta.get("grounding_quality") == "fuzzy":
        return True
    span_text = meta.get("span_text")
    if span_text is not None:
        norm_span = normalize_ws(span_text)
        if norm_span and norm_span == normalize_ws(meta.get("raw") or ""):
            return True
    return False


def plain_status(meta: dict[str, Any] | None) -> str:
    """
    Returns plain words status for an extracted field's audit metadata:
    - 'Found word for word' when meta['grounded'] is True
    - 'Found, but the match is not exact' when extracted but not grounded
    - 'Not in the filing' when nothing was extracted (missing meta, raw is None or 'Not found')
    """
    if not meta or not isinstance(meta, dict):
        return "Not in the filing"
    raw = meta.get("raw")
    if raw is None or (isinstance(raw, str) and raw.strip().lower() in ("", "none", "nan", "not found", "n/a")):
        return "Not in the filing"
    if is_word_for_word(meta):
        return "Found word for word"
    return "Found, but the match is not exact"


def _field_label_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for label, src_col, fc, _ in TABLE_COLUMNS:
        if fc:
            mapping[fc] = label.lower()
        if src_col:
            mapping[src_col] = label.lower()
        mapping[label] = label.lower()
    for col_name, fc in SCORED_FIELDS.items():
        if fc not in mapping:
            mapping[fc] = col_name.lower()
        if col_name not in mapping:
            mapping[col_name] = col_name.lower()
    return mapping


FUZZY_ISSUE = re.compile(r"^WEAK_GROUNDING:\s*\S+\s*\(fuzzy\b")


TABLE_FIELD_CLASSES: set[str] = {fc for _, _, fc, _ in TABLE_COLUMNS if fc}


def plain_check(
    status: str | None,
    issues: Any,
    audit_fields: dict[str, Any] | None = None,
) -> str:
    """
    Returns plain-words validation check result for a tranche row.
    'OK' for PASSED.
    For FLAGGED, the first reason in plain words, capitalized, plus ' (+N more)'
    when there are more issues.
    """
    if not status or str(status).strip().upper() != "FLAGGED":
        return "OK"

    if isinstance(issues, str):
        issue_list = [i.strip() for i in issues.split(";") if i.strip() and not i.strip().lower().startswith("none")]
    elif isinstance(issues, (list, tuple)):
        issue_list = [str(i).strip() for i in issues if str(i).strip() and not str(i).strip().lower().startswith("none")]
    else:
        issue_list = []

    if not issue_list:
        return "See validation details"

    if audit_fields is not None:
        filtered = []
        for i in issue_list:
            parts = i.split(":", 1)
            code = parts[0].strip()
            if code in ("UNGROUNDED", "WEAK_GROUNDING") and len(parts) > 1:
                field = parts[1].strip().split()[0] if parts[1].strip() else ""
                if field and (field not in TABLE_FIELD_CLASSES or is_word_for_word(audit_fields.get(field))):
                    continue
            filtered.append(i)
        issue_list = filtered
    else:
        issue_list = [i for i in issue_list if not FUZZY_ISSUE.match(i)]

    if not issue_list:
        return "OK"

    first_issue = issue_list[0]
    parts = first_issue.split(":", 1)
    code = parts[0].strip()
    rest = parts[1].strip() if len(parts) > 1 else ""

    if code in ("UNGROUNDED", "WEAK_GROUNDING"):
        raw_field = rest.split()[0].strip() if rest else ""
        raw_field_clean = re.sub(r"[^a-zA-Z0-9_% \-]", "", raw_field)
        field_map = _field_label_map()
        label = (
            field_map.get(raw_field)
            or field_map.get(raw_field_clean)
            or field_map.get(raw_field.lower())
            or field_map.get(raw_field_clean.lower())
            or (raw_field_clean.lower() if raw_field_clean else "field")
        )
        reason = f"{label} not exact"
    elif code == "SUSPICIOUS_COUPON":
        reason = "coupon looks unusual"
    elif code == "MISSING_COUPON":
        reason = "coupon missing"
    elif code == "PRICE_DEVIATION":
        reason = "price far from 100"
    elif code == "SPREAD_ANOMALY":
        reason = "spread looks unusual"
    elif code == "DATE_SEQUENCE_ERROR":
        reason = "dates out of order"
    else:
        reason = "see validation details"

    reason = reason[:1].upper() + reason[1:]
    more = len(issue_list) - 1
    if more > 0:
        return f"{reason} (+{more} more)"
    return reason


NA_TEXT = "n/a"
DATE_COLUMNS = ("Maturity", "Par call")
TEXT_COLUMNS = ("Tranche", "Benchmark", "CUSIP")


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and pd.isna(value):
        return True
    return isinstance(value, str) and value.strip().lower() in ("", "nan", "none", "not found", "n/a")


def short_date(value: Any) -> str:
    """Format a date as '6 Feb 2020'; 'n/a' when missing; unchanged when it cannot be parsed."""
    if _is_missing(value):
        return NA_TEXT
    parsed = pd.to_datetime(str(value), errors="coerce")
    if pd.isna(parsed):
        return str(value)
    return f"{parsed.day} {parsed:%b %Y}"


def table_frame(
    validated_df: pd.DataFrame,
    audit_records: list[dict[str, Any]] | None = None,
) -> pd.DataFrame:
    """
    Returns the table with TABLE_COLUMNS labels in order,
    the Check column from plain_check, and a fresh 0..n-1 index.
    Size column label and values reflect the deal's currency.
    Spread column formats whole numbers without decimals and keeps decimals when present.
    """
    n_rows = len(validated_df)
    data: dict[str, Any] = {}
    curs = [c for c in validated_df["Currency"].dropna().unique() if c] if "Currency" in validated_df.columns else []
    s_label = size_label(curs)
    is_mixed = (s_label == "Size (M)")

    for label, source_column, _, _ in TABLE_COLUMNS:
        col_name = s_label if label == "Size ($M)" else label
        if label == "Check":
            checks = []
            for i in range(n_rows):
                row = validated_df.iloc[i]
                status = row.get("Validation Status") if "Validation Status" in row else (row.get("Status") if "Status" in row else "PASSED")
                issues = row.get("Validation Issues") if "Validation Issues" in row else (row.get("Issues") if "Issues" in row else "")
                audit_fields = None
                if audit_records is not None and i < len(audit_records):
                    rec = audit_records[i]
                    if isinstance(rec, dict) and "fields" in rec:
                        audit_fields = rec["fields"]
                checks.append(plain_check(status, issues, audit_fields))
            data[col_name] = checks
        elif label == "Size ($M)":
            if source_column and source_column in validated_df.columns:
                values = validated_df[source_column].tolist()
                if is_mixed:
                    row_curs = validated_df["Currency"].tolist() if "Currency" in validated_df.columns else ["USD"] * n_rows
                    syms = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥"}
                    data[col_name] = [
                        NA_TEXT if _is_missing(v) else f"{syms.get(c, '$')}{float(v):,.1f}M"
                        for v, c in zip(values, row_curs)
                    ]
                else:
                    data[col_name] = values
            else:
                data[col_name] = [None] * n_rows
        elif label == "Spread (bps)":
            if source_column and source_column in validated_df.columns:
                values = validated_df[source_column].tolist()
                formatted_spreads = []
                for v in values:
                    if _is_missing(v):
                        formatted_spreads.append(NA_TEXT)
                    else:
                        v_flt = float(v)
                        sign = "+" if v_flt >= 0 else ""
                        formatted_spreads.append(
                            f"{sign}{int(v_flt)} bps" if v_flt.is_integer() else f"{sign}{v_flt} bps"
                        )
                data[col_name] = formatted_spreads
            else:
                data[col_name] = [None] * n_rows
        else:
            if source_column and source_column in validated_df.columns:
                values = validated_df[source_column].tolist()
                if label in DATE_COLUMNS:
                    values = [short_date(v) for v in values]
                elif label in TEXT_COLUMNS:
                    values = [NA_TEXT if _is_missing(v) else v for v in values]
                data[col_name] = values
            elif label in validated_df.columns:
                data[col_name] = validated_df[label].tolist()
            else:
                data[col_name] = [None] * n_rows

    res_df = pd.DataFrame(data, index=pd.RangeIndex(n_rows))
    return res_df


def not_exact_mask(
    validated_df: pd.DataFrame,
    audit_records: list[dict[str, Any]],
) -> pd.DataFrame:
    """
    Same shape and labels as table_frame, True where a value was extracted
    but is not word for word.
    """
    n_rows = len(validated_df)
    curs = [c for c in validated_df["Currency"].dropna().unique() if c] if "Currency" in validated_df.columns else []
    s_label = size_label(curs)

    col_labels = [s_label if label == "Size ($M)" else label for label, _, _, _ in TABLE_COLUMNS]
    field_class_by_label = {s_label if label == "Size ($M)" else label: fc for label, _, fc, _ in TABLE_COLUMNS}

    mask_dict: dict[str, list[bool]] = {label: [False] * n_rows for label in col_labels}

    for row_idx in range(n_rows):
        audit_entry = audit_records[row_idx] if row_idx < len(audit_records) else {}
        fields = audit_entry.get("fields", {}) if isinstance(audit_entry, dict) else {}

        for label in col_labels:
            fc = field_class_by_label.get(label)
            if not fc:
                continue
            meta = fields.get(fc)
            if not meta or not isinstance(meta, dict):
                continue
            raw = meta.get("raw")
            if raw is None or (isinstance(raw, str) and raw.strip().lower() in ("", "none", "nan", "not found", "n/a")):
                continue
            if not is_word_for_word(meta):
                mask_dict[label][row_idx] = True

    return pd.DataFrame(mask_dict, index=pd.RangeIndex(n_rows))


def _format_cell_display_value(val: Any, label: str, currency: str = "USD") -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "Not in the filing"
    if isinstance(val, str) and val.strip().lower() in ("", "none", "nan", "not found", "n/a"):
        return "Not in the filing"
    if isinstance(val, (int, float)):
        if label.startswith("Size") or label in ("Principal ($M)", "Principal (M)"):
            symbol = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥"}.get(currency, "$")
            return f"{symbol}{float(val):,.1f}M"
        elif label in ("Coupon", "Coupon (%)"):
            return f"{float(val):.3f}%"
        elif label in ("Price", "Issue Price"):
            return f"{float(val):.3f}"
        elif label in ("Yield", "Yield (%)"):
            return f"{float(val):.3f}%"
        elif label in ("Spread (bps)", "Spread"):
            v_flt = float(val)
            sign = "+" if v_flt >= 0 else ""
            return f"{sign}{int(v_flt)} bps" if v_flt.is_integer() else f"{sign}{v_flt} bps"
    return str(val)


def cell_source(
    audit_records: list[dict[str, Any]],
    row: int,
    label: str,
    validated_df: pd.DataFrame,
    doc_text: str,
) -> dict[str, Any] | None:
    """
    For a clicked cell, returns:
    {"field": label, "tranche": <tranche name>, "value": <displayed value>,
     "status": plain_status(...), "quote_html": source_quote(...) or ""}
    Returns None for the Tranche and Check columns.
    """
    if label in ("Tranche", "Check"):
        return None
    if row < 0 or row >= len(validated_df):
        return None

    matched_col = next(
        (col for col in TABLE_COLUMNS if col[0] == label or (col[0].startswith("Size") and label.startswith("Size"))),
        None,
    )
    if not matched_col:
        return None

    _, source_column, field_class, _ = matched_col
    tranche_name = str(validated_df.iloc[row]["Tranche"])

    audit_entry = audit_records[row] if row < len(audit_records) else {}
    fields = audit_entry.get("fields", {}) if isinstance(audit_entry, dict) else {}
    meta = fields.get(field_class) if field_class else {}

    status = plain_status(meta)

    raw_val = None
    if source_column and source_column in validated_df.columns:
        raw_val = validated_df.iloc[row][source_column]
    elif label in validated_df.columns:
        raw_val = validated_df.iloc[row][label]
    elif isinstance(meta, dict):
        raw_val = meta.get("raw")

    row_currency = validated_df.iloc[row].get("Currency") if "Currency" in validated_df.columns else "USD"
    if not row_currency or pd.isna(row_currency):
        row_currency = "USD"

    if status == "Not in the filing":
        displayed_val = "Not in the filing"
    else:
        displayed_val = _format_cell_display_value(raw_val, label, currency=str(row_currency))

    quote_html = ""
    if isinstance(meta, dict) and doc_text:
        interval = meta.get("char_interval")
        if interval and "start_pos" in interval and "end_pos" in interval:
            quote_html = source_quote(doc_text, interval["start_pos"], interval["end_pos"])

    return {
        "field": label,
        "tranche": tranche_name,
        "value": displayed_val,
        "status": status,
        "quote_html": quote_html,
    }



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

