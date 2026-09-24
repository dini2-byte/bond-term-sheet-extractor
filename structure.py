"""
structure.py: Converts raw LangExtract JSONL output into structured DCM comps tables.
Groups extractions by tranche, inherits deal-level fields, normalizes finance metrics,
and preserves character-level source text spans for auditability.
"""

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
    clean_str = val.replace("$", "").replace(",", "").strip()
    match = re.search(r"(\d+(?:\.\d+)?)", clean_str)
    if not match:
        return None
    num = float(match.group(1))
    if num >= 1_000_000_000:
        return round(num / 1_000_000, 2)
    elif num >= 1_000_000:
        return round(num / 1_000_000, 2)
    elif num >= 1_000:
        return round(num, 2)
    return round(num, 2)

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

    if not char_interval:
        return {
            "grounded": False,
            "alignment_status": alignment_status,
            "span_text": None,
            "grounding_quality": "none",
        }

    if not doc_text:
        return {
            "grounded": False,
            "alignment_status": alignment_status,
            "span_text": None,
            "grounding_quality": "no_source_text",
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
        }

    if alignment_status == "match_exact":
        return {
            "grounded": True,
            "alignment_status": alignment_status,
            "span_text": span_text,
            "grounding_quality": "exact",
        }

    if alignment_status == "match_fuzzy":
        return {
            "grounded": False,
            "alignment_status": alignment_status,
            "span_text": span_text,
            "grounding_quality": "fuzzy",
        }

    return {
        "grounded": False,
        "alignment_status": alignment_status,
        "span_text": span_text,
        "grounding_quality": "partial",
    }

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
        raw_issuer = merged.get("issuer", {}).get("raw", "Not found")
        raw_ratings = merged.get("ratings", {}).get("raw", "Not found")
        raw_trade_date = merged.get("trade_date", {}).get("raw", "Not found")
        raw_settle_date = merged.get("settlement_date", {}).get("raw", "Not found")
        raw_principal = merged.get("principal_amount", {}).get("raw")
        raw_coupon = merged.get("coupon", {}).get("raw")
        raw_price = merged.get("issue_price", {}).get("raw")
        raw_yield = merged.get("yield_to_maturity", {}).get("raw")
        raw_spread = merged.get("spread_bps", {}).get("raw")
        raw_benchmark = merged.get("benchmark_treasury", {}).get("raw", "Not found")
        raw_maturity = merged.get("maturity_date", {}).get("raw", "Not found")
        raw_day_count = merged.get("day_count", {}).get("raw", "Not found")
        raw_make_whole = merged.get("make_whole_call", {}).get("raw", "Not found")
        raw_par_call = merged.get("par_call_date", {}).get("raw", "Not found")
        raw_cusip = merged.get("cusip", {}).get("raw", "Not found")
        raw_bookrunners = merged.get("bookrunners", {}).get("raw", "Not found")

        row = {
            "Tranche": raw_tranche_name,
            "Issuer": raw_issuer,
            "Ratings": raw_ratings.replace("\n", " ").strip(),
            "Trade Date": raw_trade_date,
            "Settlement Date": raw_settle_date,
            "Principal ($M)": clean_principal(raw_principal),
            "Coupon (%)": clean_coupon(raw_coupon),
            "Issue Price": clean_issue_price(raw_price),
            "Yield (%)": clean_yield(raw_yield),
            "Spread (bps)": clean_spread(raw_spread),
            "Benchmark Treasury": raw_benchmark,
            "Maturity Date": raw_maturity,
            "Day Count": raw_day_count,
            "Make-Whole Call": raw_make_whole,
            "Par Call Date": raw_par_call,
            "CUSIP": raw_cusip,
            "Bookrunners": ", ".join([b.strip() for b in raw_bookrunners.split("\n") if b.strip()]),
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
