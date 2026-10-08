"""
structure.py: Converts raw LangExtract JSONL output into structured DCM comps tables.
Groups extractions by tranche, inherits deal-level fields, normalizes finance metrics,
and preserves character-level source text spans for auditability.
"""

import datetime
import json
import re
from pathlib import Path
from typing import Any
import pandas as pd

def clean_coupon(val: str | None) -> float | None:
    if not val:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)\s*%", val)
    if match:
        return float(match.group(1))
    match_num = re.search(r"(\d+\.\d+)", val)
    return float(match_num.group(1)) if match_num else None

def clean_principal(val: str | None) -> float | None:
    """Normalizes principal amounts into millions ($M). e.g. $1,500,000,000 -> 1500.0"""
    if not val:
        return None
    val_str = str(val).strip()

    # Strip commas before matching unit words
    val_clean = val_str.replace(",", "")

    # Check for billion
    match_billion = re.search(r"(\d+(?:\.\d+)?)\s*(?:billion|bn|b)\b", val_clean, re.IGNORECASE)
    if match_billion:
        return round(float(match_billion.group(1)) * 1000.0, 1)

    # Check for million
    match_million = re.search(r"(\d+(?:\.\d+)?)\s*(?:million|mn|mm)\b", val_clean, re.IGNORECASE)
    if match_million:
        return round(float(match_million.group(1)), 1)

    clean_str = val_clean.replace("$", "").strip()
    match = re.search(r"(\d+(?:\.\d+)?)", clean_str)
    if not match:
        return None
    num = float(match.group(1))
    if num >= 1_000_000:
        return round(num / 1_000_000, 1)
    return round(num, 1)

def clean_issue_price(val: str | None) -> float | None:
    """Normalizes issue price as % of par. e.g. 99.804% -> 99.804"""
    if not val:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", val)
    return float(match.group(1)) if match else None

def clean_yield(val: str | None) -> float | None:
    """Normalizes yield to maturity. e.g. 4.070% -> 4.07"""
    if not val:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", val)
    return float(match.group(1)) if match else None

def clean_spread(val: str | None) -> int | None:
    """Normalizes benchmark spread to integer basis points. e.g. '25 basis points' -> 25"""
    if not val:
        return None
    match = re.search(r"(\d+)\s*(?:basis points|bps)", val, re.IGNORECASE)
    if match:
        return int(match.group(1))
    match_plus = re.search(r"\+?\s*(\d+)", val)
    return int(match_plus.group(1)) if match_plus else None

def clean_cusip(val: str | None) -> str | None:
    """
    Extracts the first 9-character CUSIP in the extracted text:
    6 alphanumerics, optional whitespace, 3 alphanumerics.
    Returns uppercase with whitespace removed, or None if no CUSIP.
    """
    if not val:
        return None
    val_str = str(val).strip()
    if not val_str:
        return None
    match = re.search(r"(?<![A-Za-z0-9])([A-Za-z0-9]{6})\s*([A-Za-z0-9]{3})(?![A-Za-z0-9])", val_str)
    if not match:
        return None
    return f"{match.group(1)}{match.group(2)}".upper()

def normalize_ws(s: str) -> str:
    """Collapses whitespace runs to a single space and strips."""
    if not s:
        return ""
    return re.sub(r"\s+", " ", str(s)).strip()

def normalize_ratings(raw: str | None) -> str | None:
    """
    Normalizes rating strings into grades joined by ' / '.
    Removes parentheticals first.
    Matches Moody's and S&P/Fitch grades as whole tokens in order of appearance.
    Returns None if no grades found.
    """
    if not raw:
        return None
    raw_str = str(raw).strip()
    if not raw_str:
        return None

    # Whole-value check for unrated or NA markers
    if raw_str.rstrip(".").lower() in ["n/a", "na", "not rated", "nr"]:
        return None

    cleaned = re.sub(r"\(.*?\)", "", raw_str, flags=re.DOTALL)

    grade_pattern = re.compile(
        r"(?<![A-Za-z0-9+-])("
        r"Baa[1-3]|Caa[1-3]|Aa[1-3]|Ba[1-3]|A[1-3]|B[1-3]|Aaa|Ca|"
        r"BBB[+-]?|CCC[+-]?|AAA[+-]?|BB[+-]?|AA[+-]?|B[+-]?|A[+-]?|CC|D|"
        r"C"
        r")(?![A-Za-z0-9+-])"
    )

    grades = []
    for m in grade_pattern.finditer(cleaned):
        grade = m.group(1)
        if grade in ["A", "B", "C", "D"]:
            start, end = m.start(), m.end()
            prefix = cleaned[:start]
            suffix = cleaned[end:]
            is_preceded = bool(re.search(r"[/;:,]\s*$", prefix))
            is_followed = bool(
                re.match(r"^\s*$", suffix)
                or re.match(r"^[ \t]*\n", suffix)
                or re.match(r"^\s*[/;,(]", suffix)
                or re.match(r"^\s*(?:by|from)\b", suffix, re.IGNORECASE)
            )
            if not (is_preceded or is_followed):
                continue
        grades.append(grade)

    if not grades:
        return None
    return " / ".join(grades)

MONTH_NAMES = {
    "jan": "January", "january": "January",
    "feb": "February", "february": "February",
    "mar": "March", "march": "March",
    "apr": "April", "april": "April",
    "may": "May",
    "jun": "June", "june": "June",
    "jul": "July", "july": "July",
    "aug": "August", "august": "August",
    "sep": "September", "sept": "September", "september": "September",
    "oct": "October", "october": "October",
    "nov": "November", "november": "November",
    "dec": "December", "december": "December",
}

MONTH_NUMBERS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

def normalize_date(raw: str | None) -> str | None:
    """
    Finds the first full date in the text, written as Month D, YYYY
    (full or abbreviated month name, optional trailing dot, comma optional),
    and returns it as Month D, YYYY with the full month name.
    Validates with datetime.date(year, month, day).
    Returns None if there is no full valid date.
    """
    if not raw:
        return None
    raw_str = str(raw).strip()
    if not raw_str:
        return None

    match = re.search(r"\b([A-Za-z]+)\.?\s+(\d{1,2}),?\s+(\d{4})\b", raw_str)
    if not match:
        return None

    month_token = match.group(1).lower()
    if month_token not in MONTH_NAMES:
        return None

    try:
        month_num = MONTH_NUMBERS[month_token]
        day = int(match.group(2))
        year = int(match.group(3))
        valid_date = datetime.date(year, month_num, day)
    except (ValueError, KeyError):
        return None

    full_month = MONTH_NAMES[month_token]
    return f"{full_month} {valid_date.day}, {valid_date.year}"



def assess_grounding(item: dict, doc_text: str) -> dict:
    """
    Assesses source grounding quality according to the 3-part strict rule:
    1. char_interval is not None
    2. alignment_status == 'match_exact'
    3. doc_text[start:end].strip() == extraction_text.strip()
    """
    char_interval = item.get("char_interval")
    alignment_status = item.get("alignment_status")
    extraction_text = item.get("extraction_text", "")

    norm_doc = normalize_ws(doc_text)
    norm_ext = normalize_ws(extraction_text)
    found_in_source = bool(norm_ext and norm_doc and (norm_ext in norm_doc))

    if not char_interval:
        return {
            "grounded": False,
            "alignment_status": alignment_status,
            "span_text": None,
            "grounding_quality": "none",
            "found_in_source": found_in_source,
        }

    if not doc_text:
        return {
            "grounded": False,
            "alignment_status": alignment_status,
            "span_text": None,
            "grounding_quality": "no_source_text",
            "found_in_source": found_in_source,
        }

    start_pos = char_interval.get("start_pos")
    end_pos = char_interval.get("end_pos")
    span_text = doc_text[start_pos:end_pos]

    if span_text.strip() != extraction_text.strip():
        return {
            "grounded": False,
            "alignment_status": alignment_status,
            "span_text": span_text,
            "grounding_quality": "span_mismatch",
            "found_in_source": found_in_source,
        }

    if alignment_status == "match_exact":
        return {
            "grounded": True,
            "alignment_status": alignment_status,
            "span_text": span_text,
            "grounding_quality": "exact",
            "found_in_source": found_in_source,
        }

    if alignment_status == "match_fuzzy":
        return {
            "grounded": False,
            "alignment_status": alignment_status,
            "span_text": span_text,
            "grounding_quality": "fuzzy",
            "found_in_source": found_in_source,
        }

    return {
        "grounded": False,
        "alignment_status": alignment_status,
        "span_text": span_text,
        "grounding_quality": "partial",
        "found_in_source": found_in_source,
    }

def grounding_summary(audit_records: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculates overall grounding summary across all fields in all tranches."""
    total = 0
    grounded = 0
    for record in audit_records:
        fields = record.get("fields", {})
        for field_meta in fields.values():
            total += 1
            if field_meta.get("grounded") is True:
                grounded += 1
    pct = (grounded / total * 100.0) if total > 0 else 0.0
    return {"grounded": grounded, "total": total, "pct": pct}


def structure_filing_extractions(jsonl_path: str | Path) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    jsonl_path = Path(jsonl_path)
    if not jsonl_path.exists():
        raise FileNotFoundError(f"JSONL not found: {jsonl_path}")

    with open(jsonl_path, "r", encoding="utf-8") as f:
        line = f.readline()
        if not line:
            return pd.DataFrame(), []
        data = json.loads(line)

    doc_text = data.get("text", "")
    extractions = data.get("extractions", [])

    deal_fields: dict[str, dict[str, Any]] = {}
    tranche_extractions: dict[str, dict[str, dict[str, Any]]] = {}

    for item in extractions:
        field_class = item.get("extraction_class")
        raw_text = item.get("extraction_text", "").strip()
        char_interval = item.get("char_interval")
        attrs = item.get("attributes") or {}
        tranche_tag = attrs.get("tranche", "all")

        grounding_info = assess_grounding(item, doc_text)
        field_data = {
            "raw": raw_text,
            "char_interval": char_interval,
            **grounding_info,
        }


        if tranche_tag.lower() in ["all", "deal", "general"]:
            deal_fields[field_class] = field_data
        else:
            if tranche_tag not in tranche_extractions:
                tranche_extractions[tranche_tag] = {}
            tranche_extractions[tranche_tag][field_class] = field_data

    # If all extractions were tagged 'all', treat as single tranche deal
    if not tranche_extractions:
        tranche_extractions["Deal"] = deal_fields.copy()

    records = []
    audit_records = []

    for tranche_id, fields in tranche_extractions.items():
        merged = deal_fields.copy()
        merged.update(fields)

        raw_tranche_name = merged.get("tranche_name", {}).get("raw", tranche_id)
        def _clean_missing(val: Any) -> Any:
            if val is None:
                return None
            if isinstance(val, str) and val.strip().lower() == "not found":
                return None
            return val

        raw_tranche_name = merged.get("tranche_name", {}).get("raw", tranche_id)
        raw_issuer = _clean_missing(merged.get("issuer", {}).get("raw"))
        raw_ratings = merged.get("ratings", {}).get("raw")
        raw_trade_date = merged.get("trade_date", {}).get("raw")
        raw_settle_date = merged.get("settlement_date", {}).get("raw")
        raw_principal = merged.get("principal_amount", {}).get("raw")
        raw_coupon = merged.get("coupon", {}).get("raw")
        raw_price = merged.get("issue_price", {}).get("raw")
        raw_yield = merged.get("yield_to_maturity", {}).get("raw")
        raw_spread = merged.get("spread_bps", {}).get("raw")
        raw_benchmark = _clean_missing(merged.get("benchmark_treasury", {}).get("raw"))
        raw_maturity = merged.get("maturity_date", {}).get("raw")
        raw_day_count = _clean_missing(merged.get("day_count", {}).get("raw"))
        raw_make_whole = _clean_missing(merged.get("make_whole_call", {}).get("raw"))
        raw_par_call = merged.get("par_call_date", {}).get("raw")
        raw_cusip = _clean_missing(merged.get("cusip", {}).get("raw"))
        raw_bookrunners = _clean_missing(merged.get("bookrunners", {}).get("raw"))

        bookrunners_val = (
            ", ".join([b.strip() for b in raw_bookrunners.split("\n") if b.strip()])
            if raw_bookrunners
            else None
        )

        row = {
            "Tranche": raw_tranche_name,
            "Issuer": raw_issuer,
            "Ratings": normalize_ratings(raw_ratings),
            "Trade Date": normalize_date(raw_trade_date),
            "Settlement Date": normalize_date(raw_settle_date),
            "Principal ($M)": clean_principal(raw_principal),
            "Coupon (%)": clean_coupon(raw_coupon),
            "Issue Price": clean_issue_price(raw_price),
            "Yield (%)": clean_yield(raw_yield),
            "Spread (bps)": clean_spread(raw_spread),
            "Benchmark Treasury": raw_benchmark,
            "Maturity Date": normalize_date(raw_maturity),
            "Day Count": raw_day_count,
            "Make-Whole Call": raw_make_whole,
            "Par Call Date": normalize_date(raw_par_call),
            "CUSIP": clean_cusip(raw_cusip),
            "Bookrunners": bookrunners_val,
        }
        records.append(row)
        audit_records.append({
            "tranche": tranche_id,
            "fields": merged
        })

    df = pd.DataFrame(records)
    return df, audit_records

def export_comps_to_excel(df: pd.DataFrame, output_path: str | Path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="DCM Comps Table", index=False)
    print(f"[✓] Exported comps table to Excel: {output_path}")

if __name__ == "__main__":
    import sys
    test_jsonl = sys.argv[1] if len(sys.argv) > 1 else "output/AAPL_FWP_TermSheet_2025-05-06_extractions.jsonl"
    df, audit = structure_filing_extractions(test_jsonl)
    print("\n--- Structured DCM Comps Table ---")
    print(df.to_string(index=False))
    
    excel_out = Path("output") / f"{Path(test_jsonl).stem.replace('_extractions', '')}_comps.xlsx"
    export_comps_to_excel(df, excel_out)
