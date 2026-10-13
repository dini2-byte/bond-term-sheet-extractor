"""
score_test_set.py: Scores saved extractor output for the non-dollar test set against its hand-keyed answers.
Offline only: reads data/test_set/extractions/*.jsonl, makes no Gemini calls. Not part of the benchmark.
"""

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from lookup import count_bonds
from structure import structure_filing_extractions

TEST_SET_DIR = Path("data/test_set")
SCORED_FIELDS = ["Currency", "Size", "Coupon", "Price", "Yield", "Benchmark", "Spread", "Maturity", "CUSIP"]


def _year(date_text: Any) -> str | None:
    match = re.search(r"\b(19|20)\d{2}\b", str(date_text or ""))
    return match.group(0) if match else None


def _same_number(a: Any, b: Any) -> bool:
    if a is None or b is None or pd.isna(a) or pd.isna(b):
        return False
    return abs(float(a) - float(b)) < 1e-6


def _squash(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def _is_floating(text: Any) -> bool:
    return "floating" in str(text or "").lower()


def _matches(key: dict, row: dict) -> bool:
    if _year(key["Maturity Date"]) != _year(row.get("Maturity Date")):
        return False
    if key["Coupon (%)"] is None:
        return _is_floating(key["Tranche"]) and _is_floating(row.get("Tranche"))
    return _same_number(key["Coupon (%)"], row.get("Coupon (%)"))


def pair_bonds(df: pd.DataFrame, key_bonds: list[dict]) -> list[tuple[dict, dict | None]]:
    """Pairs each key bond with one extracted row by coupon and maturity year (floating notes by name)."""
    rows = df.to_dict("records")
    used: set[int] = set()
    pairs = []
    for key in key_bonds:
        match = next((i for i, row in enumerate(rows) if i not in used and _matches(key, row)), None)
        if match is not None:
            used.add(match)
        pairs.append((key, rows[match] if match is not None else None))
    return pairs


def _expected(key: dict) -> dict[str, Any]:
    return {
        "Currency": key["Currency"],
        "Size": key["Size (M)"],
        "Coupon": key["Coupon (%)"],
        "Price": key["Issue Price"],
        "Yield": key["Yield (%)"] if key["Yield (%)"] is not None else key["Semi-annual yield (%)"],
        "Benchmark": key["Benchmark text"],
        "Spread": key["Spread to benchmark (bps)"],
        "Maturity": key["Maturity Date"],
        "CUSIP": key["CUSIP"],
    }


def score_bond(key: dict, row: dict | None) -> dict[str, bool | None]:
    """True or False per scored field; None where the key has no value to score."""
    expected = _expected(key)
    if row is None:
        return {f: (None if expected[f] is None else False) for f in SCORED_FIELDS}
    yields = {key["Yield (%)"], key["Semi-annual yield (%)"]} - {None}
    checks = {
        "Currency": row.get("Currency") == expected["Currency"],
        "Size": _same_number(row.get("Principal ($M)"), expected["Size"]),
        "Coupon": _same_number(row.get("Coupon (%)"), expected["Coupon"]),
        "Price": _same_number(row.get("Issue Price"), expected["Price"]),
        "Yield": any(_same_number(row.get("Yield (%)"), y) for y in yields),
        "Benchmark": bool(expected["Benchmark"]) and _squash(expected["Benchmark"]) in _squash(row.get("Benchmark Treasury")),
        "Spread": _same_number(row.get("Spread (bps)"), expected["Spread"]),
        "Maturity": _squash(row.get("Maturity Date")) == _squash(expected["Maturity"]),
        "CUSIP": str(row.get("CUSIP") or "").upper() == expected["CUSIP"],
    }
    return {f: (None if expected[f] is None else checks[f]) for f in SCORED_FIELDS}


def spread_source(key: dict, row: dict | None) -> str:
    """Which keyed spread the extracted spread equals: benchmark, mid-swaps, other or missing."""
    value = None if row is None else row.get("Spread (bps)")
    if value is None or pd.isna(value):
        return "missing"
    if _same_number(value, key["Spread to benchmark (bps)"]):
        return "benchmark"
    if _same_number(value, key["Spread to mid-swaps (bps)"]):
        return "mid-swaps"
    return "other"


def score_deal(df: pd.DataFrame, entry: dict) -> dict[str, Any]:
    pairs = pair_bonds(df, entry["bonds"])
    fields: dict[str, tuple[int, int]] = {}
    for field in SCORED_FIELDS:
        results = [score_bond(k, r)[field] for k, r in pairs]
        scored = [r for r in results if r is not None]
        fields[field] = (sum(scored), len(scored))
    return {
        "extracted_bonds": len(df),
        "bond_count_right": len(df) == entry["bond_count"],
        "fields": fields,
        "spread_sources": Counter(spread_source(k, r) for k, r in pairs if k["Coupon (%)"] is not None),
    }


def main() -> None:
    key = json.loads((TEST_SET_DIR / "answer_key.json").read_text(encoding="utf-8"))
    totals = {f: [0, 0] for f in SCORED_FIELDS}
    sources: Counter = Counter()
    deals = 0
    print("| Deal | Bonds (key / extracted / search count) | " + " | ".join(SCORED_FIELDS) + " |")
    print("|---|---|" + "---|" * len(SCORED_FIELDS))
    for path in sorted((TEST_SET_DIR / "extractions").glob("*_extractions.jsonl")):
        stem = path.name.removesuffix("_extractions.jsonl")
        df, _ = structure_filing_extractions(path)
        result = score_deal(df, key[stem])
        search_count = count_bonds((TEST_SET_DIR / "raw" / f"{stem}.txt").read_text(encoding="utf-8"))
        cells = []
        for field in SCORED_FIELDS:
            right, total = result["fields"][field]
            totals[field][0] += right
            totals[field][1] += total
            cells.append(f"{right}/{total}")
        sources += result["spread_sources"]
        deals += 1
        print(f"| {stem} | {key[stem]['bond_count']} / {result['extracted_bonds']} / {search_count} | " + " | ".join(cells) + " |")
    print(f"| **All {deals} deals** | | " + " | ".join(f"{r}/{t}" for r, t in totals.values()) + " |")
    print(f"\nExtracted spread on fixed-rate bonds: {dict(sources)}")


if __name__ == "__main__":
    main()
