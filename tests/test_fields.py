import json
from pathlib import Path
import pytest
from fields import PROMPT_DESCRIPTION, SAMPLE_TERM_SHEET, FEW_SHOT_EXAMPLES


def build_tranche_leak_strings(tranche: dict) -> list[tuple[str, str]]:
    """Build list of (field_name, leak_string) for a benchmark deal tranche."""
    leaks = []
    if "Coupon (%)" in tranche and tranche["Coupon (%)"] is not None:
        c = float(tranche["Coupon (%)"])
        leaks.append(("Coupon (%)", f"{c:.3f}%"))
    if "Issue Price" in tranche and tranche["Issue Price"] is not None:
        p = float(tranche["Issue Price"])
        leaks.append(("Issue Price", f"{p:.3f}"))
    if "Yield (%)" in tranche and tranche["Yield (%)"] is not None:
        y = float(tranche["Yield (%)"])
        leaks.append(("Yield (%)", f"{y:.3f}%"))
    if "Spread (bps)" in tranche and tranche["Spread (bps)"] is not None:
        s = int(tranche["Spread (bps)"])
        leaks.append(("Spread (bps)", f"{s} basis points"))
        leaks.append(("Spread (bps)", f"+{s} bps"))
        leaks.append(("Spread (bps)", f"{s} bps"))
    if "Principal ($M)" in tranche and tranche["Principal ($M)"] is not None:
        p = float(tranche["Principal ($M)"])
        leaks.append(("Principal ($M)", f"${p * 1_000_000:,.0f}"))

    for direct_key in [
        "CUSIP",
        "Benchmark Treasury",
        "Maturity Date",
        "Par Call Date",
        "Trade Date",
        "Settlement Date",
    ]:
        if direct_key in tranche and tranche[direct_key]:
            leaks.append((direct_key, str(tranche[direct_key])))

    return leaks


def test_leak_strings_formatting():
    """Verify leak string builder correctly formats values and excludes generic fields."""
    sample_tranche = {
        "Tranche": "4.000% Notes due 2028",
        "Issuer": "Apple Inc.",
        "Ratings": "Aaa / AA+",
        "Trade Date": "May 5, 2025",
        "Settlement Date": "May 12, 2025",
        "Principal ($M)": 1500.0,
        "Coupon (%)": 4.0,
        "Issue Price": 99.804,
        "Yield (%)": 4.07,
        "Spread (bps)": 25,
        "Benchmark Treasury": "3.750% due April 15, 2028",
        "Maturity Date": "May 12, 2028",
        "Day Count": "30/360",
        "Par Call Date": "April 12, 2028",
        "CUSIP": "037833EY2",
    }
    leaks = build_tranche_leak_strings(sample_tranche)
    leak_dict = {}
    for field, val in leaks:
        leak_dict.setdefault(field, []).append(val)

    assert leak_dict["Coupon (%)"] == ["4.000%"]
    assert leak_dict["Issue Price"] == ["99.804"]
    assert leak_dict["Yield (%)"] == ["4.070%"]
    assert "25 basis points" in leak_dict["Spread (bps)"]
    assert "+25 bps" in leak_dict["Spread (bps)"]
    assert "25 bps" in leak_dict["Spread (bps)"]
    assert leak_dict["Principal ($M)"] == ["$1,500,000,000"]
    assert leak_dict["CUSIP"] == ["037833EY2"]
    assert leak_dict["Benchmark Treasury"] == ["3.750% due April 15, 2028"]
    assert leak_dict["Maturity Date"] == ["May 12, 2028"]
    assert leak_dict["Par Call Date"] == ["April 12, 2028"]
    assert leak_dict["Trade Date"] == ["May 5, 2025"]
    assert leak_dict["Settlement Date"] == ["May 12, 2025"]

    # Excluded fields
    assert "Issuer" not in leak_dict
    assert "Ratings" not in leak_dict
    assert "Day Count" not in leak_dict


def test_few_shot_extractions_are_verbatim_in_sample():
    """Verify every extraction_text in FEW_SHOT_EXAMPLES appears verbatim in SAMPLE_TERM_SHEET."""
    for eg in FEW_SHOT_EXAMPLES:
        for ex in eg.extractions:
            assert ex.extraction_text in eg.text, (
                f"Extraction text '{ex.extraction_text}' ({ex.extraction_class}) not found in sample text"
            )


def test_prompt_contains_no_benchmark_values():
    """Verify prompt text, sample text, and few-shot examples contain no answer-key values."""
    answer_key_path = Path("data/answer_key.json")
    assert answer_key_path.exists(), "data/answer_key.json not found"

    with open(answer_key_path) as f:
        answer_key = json.load(f)

    searchable_prompt = (
        PROMPT_DESCRIPTION
        + "\n"
        + SAMPLE_TERM_SHEET
        + "\n"
        + "\n".join(
            ex.extraction_text for eg in FEW_SHOT_EXAMPLES for ex in eg.extractions
        )
    )

    leaked = []
    for deal_id, tranches in answer_key.items():
        for tranche in tranches:
            tranche_name = tranche.get("Tranche", "Unknown Tranche")
            leak_strings = build_tranche_leak_strings(tranche)
            for field, leak_str in leak_strings:
                if leak_str in searchable_prompt:
                    leaked.append(
                        f"Deal: {deal_id} | Tranche: {tranche_name} | Field: {field} | Leaked: '{leak_str}'"
                    )

    assert not leaked, (
        f"Benchmark leakage detected in fields.py ({len(leaked)} values):\n"
        + "\n".join(f"  - {item}" for item in leaked)
    )
