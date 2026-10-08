"""
evaluate.py: Quantitative accuracy evaluation framework for AINA scholarship reporting.
Compares extracted bond comps table values against hand-verified ground truth answer keys.
Calculates field-level accuracy, grounding fidelity %, and outputs a publication-ready scorecard.
"""

import json
from pathlib import Path
import re
from typing import Any
import pandas as pd
from structure import normalize_date, normalize_ratings, structure_filing_extractions
from validate import validate_comps_table

ANSWER_KEY_PATH = Path("data/answer_key.json")
FIXTURES_DIR = Path("data/fixtures")
OUTPUT_DIR = Path("output")

def normalize_text(s: Any) -> str:
    if s is None:
        return ""
    return str(s).lower().replace(",", "").replace(".", "").replace("-", " ").strip()

def is_nan_scalar(val: Any) -> bool:
    if val is None:
        return False
    if isinstance(val, bool):
        return False
    try:
        return bool(pd.isna(val))
    except (ValueError, TypeError):
        return False

def matches_value(actual: Any, expected: Any, field_name: str) -> bool:
    if is_nan_scalar(actual) or (isinstance(actual, str) and actual.strip().lower() == "not found"):
        actual = None
    if is_nan_scalar(expected) or (isinstance(expected, str) and expected.strip().lower() == "not found"):
        expected = None

    if actual is None and expected is None:
        return True
    if actual is None or expected is None:
        return False

    # Coupon (%), Issue Price, Yield (%): Equal after rounding both values to 3 decimal places
    if field_name in ["Coupon (%)", "Issue Price", "Yield (%)"]:
        try:
            return round(float(actual), 3) == round(float(expected), 3)
        except (ValueError, TypeError):
            return False

    # Principal ($M): compare abs(a - b) <= 0.05 after converting both to float
    if field_name == "Principal ($M)":
        if isinstance(actual, bool) or isinstance(expected, bool):
            return False
        try:
            return abs(float(actual) - float(expected)) <= 0.050000001
        except (ValueError, TypeError):
            return False

    # Spread (bps): Integer equality, rejects bool
    if field_name == "Spread (bps)":
        if isinstance(actual, bool) or isinstance(expected, bool):
            return False
        try:
            act_f = float(actual)
            exp_f = float(expected)
            if not act_f.is_integer() or not exp_f.is_integer():
                return False
            return int(act_f) == int(exp_f)
        except (ValueError, TypeError):
            return False

    # Trade Date, Settlement Date, Maturity Date, Par Call Date: Parse to calendar date and compare
    if field_name in ["Trade Date", "Settlement Date", "Maturity Date", "Par Call Date"]:
        d_act = normalize_date(actual)
        d_exp = normalize_date(expected)
        if d_act is None or d_exp is None:
            return False
        return d_act == d_exp

    # Ratings: normalize_ratings(actual) == normalize_ratings(expected), both not None
    if field_name == "Ratings":
        act_norm = normalize_ratings(actual)
        exp_norm = normalize_ratings(expected)
        if act_norm is None or exp_norm is None:
            return False
        return act_norm == exp_norm

    # CUSIP: Exact match after removing whitespace and converting to uppercase
    if field_name == "CUSIP":
        act_cusip = re.sub(r"\s+", "", str(actual)).upper()
        exp_cusip = re.sub(r"\s+", "", str(expected)).upper()
        return act_cusip == exp_cusip

    # Issuer, Benchmark Treasury, Day Count (and other text fields): Equal after normalize_text
    return normalize_text(actual) == normalize_text(expected)

def evaluate_deal(deal_key: str, extracted_df: pd.DataFrame, audit_records: list[dict[str, Any]], ground_truth: list[dict[str, Any]]) -> pd.DataFrame:
    results = []
    
    # Core fields to evaluate
    fields_to_eval = [
        "Issuer", "Ratings", "Trade Date", "Settlement Date",
        "Principal ($M)", "Coupon (%)", "Issue Price", "Yield (%)",
        "Spread (bps)", "Benchmark Treasury", "Maturity Date",
        "Day Count", "Par Call Date", "CUSIP"
    ]

    field_class_map = {
        "Issuer": "issuer",
        "Ratings": "ratings",
        "Trade Date": "trade_date",
        "Settlement Date": "settlement_date",
        "Principal ($M)": "principal_amount",
        "Coupon (%)": "coupon",
        "Issue Price": "issue_price",
        "Yield (%)": "yield_to_maturity",
        "Spread (bps)": "spread_bps",
        "Benchmark Treasury": "benchmark_treasury",
        "Maturity Date": "maturity_date",
        "Day Count": "day_count",
        "Par Call Date": "par_call_date",
        "CUSIP": "cusip",
    }

    paired_map: dict[int, int] = {}
    paired_extracted_indices: set[int] = set()

    # Pass 1: Match every answer-key tranche by CUSIP
    for i, exp_row in enumerate(ground_truth):
        exp_cusip = exp_row.get("CUSIP")
        if exp_cusip is not None:
            for j in range(len(extracted_df)):
                if j not in paired_extracted_indices:
                    act_cusip = extracted_df.iloc[j].get("CUSIP")
                    if matches_value(act_cusip, exp_cusip, "CUSIP"):
                        paired_map[i] = j
                        paired_extracted_indices.add(j)
                        break

    # Pass 2: Match remaining answer-key tranches by maturity date fallback
    for i, exp_row in enumerate(ground_truth):
        if i not in paired_map:
            exp_maturity = exp_row.get("Maturity Date")
            if exp_maturity is not None:
                for j in range(len(extracted_df)):
                    if j not in paired_extracted_indices:
                        act_maturity = extracted_df.iloc[j].get("Maturity Date")
                        if matches_value(act_maturity, exp_maturity, "Maturity Date"):
                            paired_map[i] = j
                            paired_extracted_indices.add(j)
                            break

    for i, exp_row in enumerate(ground_truth):
        tranche_name = exp_row.get("Tranche", f"Tranche {i+1}")
        matched_idx = paired_map.get(i)

        if matched_idx is not None:
            act_row = extracted_df.iloc[matched_idx].to_dict()
            audit_entry = audit_records[matched_idx]["fields"] if matched_idx < len(audit_records) else {}
            for field in fields_to_eval:
                expected_val = exp_row.get(field)
                actual_val = act_row.get(field)
                if is_nan_scalar(actual_val) or (isinstance(actual_val, str) and actual_val.strip().lower() == "not found"):
                    actual_val = None
                if is_nan_scalar(expected_val) or (isinstance(expected_val, str) and expected_val.strip().lower() == "not found"):
                    expected_val = None

                raw_meta = audit_entry.get(field_class_map.get(field, ""), {})
                is_grounded = raw_meta.get("grounded", False) if actual_val is not None else False
                in_source = raw_meta.get("found_in_source", False) if actual_val is not None else None
                is_correct = matches_value(actual_val, expected_val, field)

                results.append({
                    "Tranche": tranche_name,
                    "Field": field,
                    "Expected": expected_val,
                    "Extracted": actual_val,
                    "Grounded": is_grounded,
                    "In Source": in_source,
                    "Correct": is_correct
                })
        else:
            # 4. If an answer-key tranche has no pair, score every field as incorrect
            for field in fields_to_eval:
                expected_val = exp_row.get(field)
                if is_nan_scalar(expected_val):
                    expected_val = None
                results.append({
                    "Tranche": tranche_name,
                    "Field": field,
                    "Expected": expected_val,
                    "Extracted": None,
                    "Grounded": False,
                    "In Source": None,
                    "Correct": False
                })

    unmatched_extracted = len(extracted_df) - len(paired_extracted_indices)
    columns = ["Tranche", "Field", "Expected", "Extracted", "Grounded", "In Source", "Correct"]
    res_df = pd.DataFrame(results, columns=columns)
    res_df.attrs["unmatched_extracted_tranches"] = unmatched_extracted
    return res_df

def compute_summary_metrics(eval_df: pd.DataFrame) -> dict[str, Any]:
    total = len(eval_df)
    correct = int(eval_df["Correct"].sum()) if total > 0 else 0
    accuracy_pct = (correct / total * 100.0) if total > 0 else 0.0

    if total > 0 and "Extracted" in eval_df.columns:
        extracted_mask = eval_df["Extracted"].notna() & (eval_df["Extracted"] != "Not found")
        extracted = int(extracted_mask.sum())
        if "In Source" in eval_df.columns:
            not_in_source_mask = extracted_mask & (eval_df["In Source"] == False)
            not_in_source = int(not_in_source_mask.sum())
        else:
            not_in_source = 0
    elif total > 0 and "In Source" in eval_df.columns:
        extracted_mask = eval_df["In Source"].notna()
        extracted = int(extracted_mask.sum())
        not_in_source_mask = eval_df["In Source"] == False
        not_in_source = int(not_in_source_mask.sum())
    else:
        extracted = 0
        not_in_source = 0

    grounded = int(eval_df["Grounded"].sum()) if total > 0 else 0
    grounding_pct = (grounded / extracted * 100.0) if extracted > 0 else 0.0
    not_in_source_pct = (not_in_source / extracted * 100.0) if extracted > 0 else 0.0

    return {
        "total": total,
        "correct": correct,
        "accuracy_pct": accuracy_pct,
        "grounded": grounded,
        "grounding_pct": grounding_pct,
        "extracted": extracted,
        "not_in_source": not_in_source,
        "not_in_source_pct": not_in_source_pct,
    }


def load_extraction_attempts(attempts_path: Path = FIXTURES_DIR / "attempts.jsonl") -> list[dict[str, Any]]:
    if not attempts_path.exists():
        return []
    attempts = []
    with open(attempts_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                attempts.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return attempts


def format_extraction_attempts(attempts: list[dict[str, Any]]) -> str:
    aapl_line = "AAPL: produced 2026-09-24 before the attempt log existed"
    if not attempts:
        return aapl_line

    rows = []
    for att in attempts:
        rows.append({
            "Deal": att.get("deal", ""),
            "Timestamp": att.get("timestamp", ""),
            "Model": att.get("model_id", ""),
            "Outcome": att.get("outcome", ""),
            "Error": att.get("error") or "",
        })
    df = pd.DataFrame(rows)
    return f"{aapl_line}\n\n{df.to_markdown(index=False)}"


def run_evaluation():
    if not ANSWER_KEY_PATH.exists():
        raise FileNotFoundError(f"Answer key not found: {ANSWER_KEY_PATH}")

    with open(ANSWER_KEY_PATH, "r", encoding="utf-8") as f:
        answer_keys = json.load(f)

    if not answer_keys:
        raise ValueError(f"No deals found in answer key: {ANSWER_KEY_PATH}")

    all_deal_dfs = []
    deal_summaries = []

    for deal_key, ground_truth in answer_keys.items():
        fixture_file = FIXTURES_DIR / f"{deal_key}_extractions.jsonl"
        if not fixture_file.exists():
            raise FileNotFoundError(f"Fixture not found for deal '{deal_key}': {fixture_file}")

        df, audit = structure_filing_extractions(fixture_file)
        validated_df = validate_comps_table(df, audit)

        deal_eval_df = evaluate_deal(deal_key, validated_df, audit, ground_truth)
        deal_eval_df.insert(0, "Deal", deal_key)

        deal_metrics = compute_summary_metrics(deal_eval_df)
        unmatched_tranches = deal_eval_df.attrs.get("unmatched_extracted_tranches", 0)

        deal_summaries.append({
            "Deal": deal_key,
            "Tranches": len(ground_truth),
            "Fields": deal_metrics["total"],
            "Correct": deal_metrics["correct"],
            "Accuracy (%)": round(deal_metrics["accuracy_pct"], 1),
            "Grounded (%)": round(deal_metrics["grounding_pct"], 1),
            "Unmatched Extracted Tranches": unmatched_tranches,
        })
        all_deal_dfs.append(deal_eval_df)

    eval_columns = ["Deal", "Tranche", "Field", "Expected", "Extracted", "Grounded", "In Source", "Correct"]
    if all_deal_dfs:
        all_eval_df = pd.concat(all_deal_dfs, ignore_index=True)
    else:
        all_eval_df = pd.DataFrame(columns=eval_columns)

    overall_metrics = compute_summary_metrics(all_eval_df)

    num_deals = len(deal_summaries)
    deal_word = "deal" if num_deals == 1 else "deals"
    total_tranches = sum(d["Tranches"] for d in deal_summaries)
    tranche_word = "tranche" if total_tranches == 1 else "tranches"

    headline = (
        f"Field accuracy: {overall_metrics['accuracy_pct']:.1f}% "
        f"({overall_metrics['correct']}/{overall_metrics['total']} fields, "
        f"{num_deals} {deal_word}, {total_tranches} {tranche_word})"
    )
    grounded_line = (
        f"Grounded: {overall_metrics['grounding_pct']:.1f}% "
        f"({overall_metrics['grounded']}/{overall_metrics['extracted']} extracted fields)"
    )
    not_in_source_line = (
        f"Not-in-source: {overall_metrics['not_in_source_pct']:.1f}% "
        f"({overall_metrics['not_in_source']}/{overall_metrics['extracted']} extracted fields)"
    )
    total_unmatched = sum(d["Unmatched Extracted Tranches"] for d in deal_summaries)
    unmatched_line = f"Unmatched extracted tranches: {total_unmatched}"

    deal_summary_cols = ["Deal", "Tranches", "Fields", "Correct", "Accuracy (%)", "Grounded (%)", "Unmatched Extracted Tranches"]
    per_deal_df = pd.DataFrame(deal_summaries, columns=deal_summary_cols)

    if not all_eval_df.empty and "Field" in all_eval_df.columns:
        field_summary = all_eval_df.groupby("Field").agg(
            Total=("Correct", "count"),
            Correct=("Correct", "sum"),
            Grounded=("Grounded", "sum")
        )
        field_summary["Accuracy (%)"] = (field_summary["Correct"] / field_summary["Total"] * 100.0).round(1)
        field_summary["Grounded (%)"] = (field_summary["Grounded"] / field_summary["Total"] * 100.0).round(1)
    else:
        field_summary = pd.DataFrame(columns=["Total", "Correct", "Grounded", "Accuracy (%)", "Grounded (%)"])

    if not all_eval_df.empty and "Correct" in all_eval_df.columns:
        discrepancies = all_eval_df[~all_eval_df["Correct"]][["Deal", "Tranche", "Field", "Expected", "Extracted"]]
    else:
        discrepancies = pd.DataFrame(columns=["Deal", "Tranche", "Field", "Expected", "Extracted"])
    # Console output
    print(headline)
    print(grounded_line)
    print(not_in_source_line)
    print(unmatched_line)
    print("\n--- Per-Deal Breakdown ---")
    print(per_deal_df.to_string(index=False))
    print("\n--- Per-Field Breakdown ---")
    print(field_summary.to_string())
    print("\n--- Discrepancy Log ---")
    if len(discrepancies) == 0:
        print("None. All extracted fields matched answer key.")
    else:
        print(discrepancies.to_string(index=False))

    attempts = load_extraction_attempts()
    print("\n--- Extraction Attempts ---")
    print("AAPL: produced 2026-09-24 before the attempt log existed")
    if attempts:
        attempts_df = pd.DataFrame([{
            "Deal": att.get("deal", ""),
            "Timestamp": att.get("timestamp", ""),
            "Model": att.get("model_id", ""),
            "Outcome": att.get("outcome", ""),
            "Error": att.get("error") or "",
        } for att in attempts])
        print(attempts_df.to_string(index=False))

    # Export markdown report
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = OUTPUT_DIR / "accuracy_benchmark_report.md"
    attempts_content = format_extraction_attempts(attempts)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"{headline}\n")
        f.write(f"{grounded_line}\n")
        f.write(f"{not_in_source_line}\n")
        f.write(f"{unmatched_line}\n\n")
        f.write("### Per-Deal Breakdown\n\n")
        f.write(per_deal_df.to_markdown(index=False))
        f.write("\n\n### Per-Field Breakdown\n\n")
        f.write(field_summary.to_markdown())
        f.write("\n\n### Discrepancy Log\n\n")
        if len(discrepancies) == 0:
            f.write("None. All extracted fields matched answer key.\n")
        else:
            f.write(discrepancies.to_markdown(index=False))
            f.write("\n")
        f.write("\n### Extraction Attempts\n\n")
        f.write(f"{attempts_content}\n")

    print(f"\n[✓] Saved evaluation report: {report_path}")

if __name__ == "__main__":
    run_evaluation()
