"""
validate.py: Finance sanity validator and source-grounding verification engine.
Enforces non-negotiable trustworthiness rules:
1. Grounding verification: Drop or flag ungrounded values (char_interval is None).
2. Economic bounds: Coupon (0-15%), Price (90-110), Spread (0-1000 bps).
3. Chronological consistency: Maturity > Trade Date; Settlement >= Trade Date.
"""

from typing import Any
import pandas as pd
from dateutil import parser as date_parser

def parse_flexible_date(date_str: str | None):
    if not date_str or date_str in ["Not found", "None"]:
        return None
    # Strip T+5 or extra notes in settlement dates
    cleaned = date_str.split("(")[0].split(", commencing")[0].strip()
    try:
        return date_parser.parse(cleaned, fuzzy=True)
    except Exception:
        return None

def validate_tranche(row: dict[str, Any], audit_fields: dict[str, Any]) -> list[str]:
    flags = []

    # 1. Source Grounding Gate
    for field_name, field_meta in audit_fields.items():
        if not field_meta.get("grounded", False):
            quality = field_meta.get("grounding_quality", "none")
            if quality in ("none", "no_source_text"):
                flags.append(f"UNGROUNDED: {field_name} not anchored to source text")
            else:
                span_text = str(field_meta.get("span_text") if field_meta.get("span_text") is not None else "")[:40]
                raw_text = str(field_meta.get("raw") if field_meta.get("raw") is not None else "")[:40]
                flags.append(f"WEAK_GROUNDING: {field_name} ({quality}, span '{span_text}' vs '{raw_text}')")


    # 2. Coupon Sanity Check (0.0% to 15.0%)
    coupon = row.get("Coupon (%)")
    if coupon is not None:
        if not (0.0 <= coupon <= 15.0):
            flags.append(f"SUSPICIOUS_COUPON: {coupon}% outside plausible range (0-15%)")
    else:
        flags.append("MISSING_COUPON")

    # 3. Issue Price Par Check (90.00 to 110.00)
    price = row.get("Issue Price")
    if price is not None:
        if not (90.0 <= price <= 110.0):
            flags.append(f"PRICE_DEVIATION: {price} deviates significantly from par (90-110)")

    # 4. Spread Sanity Check (0 to 1,000 bps)
    spread = row.get("Spread (bps)")
    if spread is not None:
        if not (0 <= spread <= 1000):
            flags.append(f"SPREAD_ANOMALY: {spread} bps outside standard bounds (0-1000 bps)")

    # 5. Date Chronology Checks
    trade_dt = parse_flexible_date(row.get("Trade Date"))
    settle_dt = parse_flexible_date(row.get("Settlement Date"))
    mat_dt = parse_flexible_date(row.get("Maturity Date"))

    if trade_dt and mat_dt:
        if mat_dt <= trade_dt:
            flags.append(f"DATE_SEQUENCE_ERROR: Maturity ({row.get('Maturity Date')}) <= Trade Date ({row.get('Trade Date')})")

    if trade_dt and settle_dt:
        if settle_dt < trade_dt:
            flags.append(f"DATE_SEQUENCE_ERROR: Settlement ({row.get('Settlement Date')}) < Trade Date ({row.get('Trade Date')})")

    return flags

def validate_comps_table(df: pd.DataFrame, audit_records: list[dict[str, Any]]) -> pd.DataFrame:
    validated_df = df.copy()
    status_list = []
    issues_list = []

    for i, row in validated_df.iterrows():
        audit_entry = audit_records[i] if i < len(audit_records) else {}
        audit_fields = audit_entry.get("fields", {})

        row_dict = row.to_dict()
        flags = validate_tranche(row_dict, audit_fields)

        if len(flags) == 0:
            status_list.append("PASSED")
            issues_list.append("None (All checks passed)")
        else:
            status_list.append("FLAGGED")
            issues_list.append("; ".join(flags))

    validated_df["Validation Status"] = status_list
    validated_df["Validation Issues"] = issues_list
    return validated_df

if __name__ == "__main__":
    from structure import structure_filing_extractions
    import sys

    test_jsonl = sys.argv[1] if len(sys.argv) > 1 else "output/AAPL_FWP_TermSheet_2025-05-06_extractions.jsonl"
    df, audit = structure_filing_extractions(test_jsonl)
    validated_df = validate_comps_table(df, audit)

    print("\n--- Validation Audit Report ---")
    cols_to_show = ["Tranche", "Coupon (%)", "Issue Price", "Spread (bps)", "Validation Status", "Validation Issues"]
    print(validated_df[cols_to_show].to_string(index=False))
