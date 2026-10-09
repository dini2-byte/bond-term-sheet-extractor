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


# Known collisions between prompt/sample text in fields.py (written 2026-09-24)
# and benchmark deals added later (2026-10-07). These are coincidental matches,
# not leakage. See CONTEXT.md (Leakage and Collision) and docs/plans/02-benchmark-run.md Task E3.
KNOWN_COLLISIONS = {
    ("MSFT_FWP_TermSheet_2017-01-31", "594918BY9", "Spread (bps)"),
    ("MSFT_FWP_TermSheet_2017-01-31", "594918CB8", "Principal ($M)"),
    ("ORCL_FWP_TermSheet_2025-09-24", "68389XDT9", "Principal ($M)"),
    ("GOOGL_FWP_TermSheet_2026-08-07", "02079KCL9", "Principal ($M)"),
    ("GOOGL_FWP_TermSheet_2026-08-07", "02079KCN5", "Principal ($M)"),
    ("GOOGL_FWP_TermSheet_2026-08-07", "02079KCS4", "Spread (bps)"),
}


def _get_searchable_prompt() -> str:
    return (
        PROMPT_DESCRIPTION
        + "\n"
        + "\n".join(eg.text for eg in FEW_SHOT_EXAMPLES)
        + "\n"
        + "\n".join(
            ex.extraction_text for eg in FEW_SHOT_EXAMPLES for ex in eg.extractions
        )
    )


def test_prompt_contains_no_benchmark_values():
    """Verify prompt text, sample text, and few-shot examples contain no answer-key values."""
    answer_key_path = Path("data/answer_key.json")
    assert answer_key_path.exists(), "data/answer_key.json not found"

    with open(answer_key_path) as f:
        answer_key = json.load(f)

    searchable_prompt = _get_searchable_prompt()

    leaked = []
    for deal_id, tranches in answer_key.items():
        for tranche in tranches:
            tranche_name = tranche.get("Tranche", "Unknown Tranche")
            cusip = tranche.get("CUSIP")
            leak_strings = build_tranche_leak_strings(tranche)
            for field, leak_str in leak_strings:
                if (deal_id, cusip, field) in KNOWN_COLLISIONS:
                    continue
                if leak_str in searchable_prompt:
                    leaked.append(
                        f"Deal: {deal_id} | Tranche: {tranche_name} | Field: {field} | Leaked: '{leak_str}'"
                    )

    assert not leaked, (
        f"Benchmark leakage detected in fields.py ({len(leaked)} values):\n"
        + "\n".join(f"  - {item}" for item in leaked)
    )


def test_known_collisions_has_no_stale_entries():
    """Verify every entry in KNOWN_COLLISIONS corresponds to an actual collision in fields.py."""
    answer_key_path = Path("data/answer_key.json")
    assert answer_key_path.exists(), "data/answer_key.json not found"

    with open(answer_key_path) as f:
        answer_key = json.load(f)

    searchable_prompt = _get_searchable_prompt()

    active_collisions = set()
    for deal_id, tranches in answer_key.items():
        for tranche in tranches:
            cusip = tranche.get("CUSIP")
            for field, leak_str in build_tranche_leak_strings(tranche):
                if leak_str in searchable_prompt:
                    active_collisions.add((deal_id, cusip, field))

    stale_entries = KNOWN_COLLISIONS - active_collisions
    assert not stale_entries, (
        f"Stale entries found in KNOWN_COLLISIONS ({len(stale_entries)} entries):\n"
        + "\n".join(f"  - {entry}" for entry in sorted(stale_entries))
    )



def _test_set_leak_strings(bond: dict) -> list[str]:
    symbol = {"EUR": "€", "GBP": "£", "JPY": "¥"}[bond["Currency"]]
    leaks = [f"{symbol}{round(bond['Size (M)'] * 1_000_000):,}"]
    for field in ("Benchmark text", "ISIN", "Common Code", "CUSIP", "Maturity Date", "Par Call Date"):
        if bond[field]:
            leaks.append(bond[field])
    for field, fmt in (("Coupon (%)", "{:.3f}%"), ("Issue Price", "{:.3f}%"), ("Yield (%)", "{:.3f}%")):
        if bond[field] is not None:
            leaks.append(fmt.format(bond[field]))
    if bond["Spread to benchmark (bps)"] is not None:
        leaks.append(f"+{bond['Spread to benchmark (bps)']} bps")
    return leaks


# Coupons in SAMPLE_TERM_SHEET (written 2026-09-24) that match test set coupons keyed on 2026-10-09.
# Coincidental, not leakage.
TEST_SET_KNOWN_COLLISIONS = {
    ("KO_FWP_TermSheet_EUR_2024-05-07", "3.500%"),
    ("IBM_FWP_TermSheet_EUR_2026-01-29", "3.850%"),
}


def test_prompt_contains_no_test_set_values():
    key = json.loads(Path("data/test_set/answer_key.json").read_text(encoding="utf-8"))
    searchable = _get_searchable_prompt()
    leaked = [
        f"{stem}: {leak}"
        for stem, deal in key.items()
        for bond in deal["bonds"]
        for leak in _test_set_leak_strings(bond)
        if leak in searchable and (stem, leak) not in TEST_SET_KNOWN_COLLISIONS
    ]
    assert not leaked, "Test set values in fields.py:\n" + "\n".join(leaked)


def _prompt_line(field: str) -> str:
    return next(line for line in PROMPT_DESCRIPTION.splitlines() if line.strip().startswith(f"- {field}:"))


def test_prompt_takes_spread_over_government_benchmark_not_mid_swaps():
    spread_line = _prompt_line("spread_bps").lower()
    assert "government" in spread_line
    assert "mid-swap" in spread_line
    assert "government" in _prompt_line("benchmark_treasury").lower()


def test_prompt_explains_side_by_side_tables():
    assert "side by side" in PROMPT_DESCRIPTION.lower()


def test_euro_example_spreads_come_from_the_bund_row_not_the_mid_swap_row():
    assert len(FEW_SHOT_EXAMPLES) == 2
    euro = FEW_SHOT_EXAMPLES[1]
    lines = euro.text.splitlines()
    bund_row = next(l for l in lines if l.startswith("Spread to Benchmark Bund"))
    swap_row = next(l for l in lines if l.startswith("Spread to Mid-Swaps"))
    spreads = [ex.extraction_text for ex in euro.extractions if ex.extraction_class == "spread_bps"]
    assert len(spreads) == 2
    for spread in spreads:
        assert spread in bund_row
        assert spread not in swap_row


def test_euro_example_tags_both_tranches():
    euro = FEW_SHOT_EXAMPLES[1]
    tags = {ex.attributes["tranche"] for ex in euro.extractions}
    assert {"2031 Notes", "2036 Notes"} <= tags
    for tag in ("2031 Notes", "2036 Notes"):
        classes = {ex.extraction_class for ex in euro.extractions if ex.attributes["tranche"] == tag}
        assert {"principal_amount", "coupon", "spread_bps", "benchmark_treasury", "cusip"} <= classes


def test_prompt_forbids_joining_text_from_different_places():
    prompt = PROMPT_DESCRIPTION.lower()
    assert "one continuous piece of text" in prompt
    assert "never change its date" in _prompt_line("benchmark_treasury").lower()
