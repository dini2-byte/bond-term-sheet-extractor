"""
app.py: Streamlit web application for Bond Term Sheet Extractor.
Pulls pricing terms for investment-grade bond deals out of SEC term sheets
and builds a comps table with source grounding.
"""

import html
import io
import os
from pathlib import Path
import re
import tempfile
from typing import Any

from dotenv import load_dotenv
import pandas as pd
import streamlit as st

from demo import (
    build_visualization_html,
    check_password,
    check_upload_size,
    get_gemini_api_key,
    list_benchmark_deals,
    parse_accuracy_report,
    save_uploaded_filing,
    visualization_src,
)
from evaluate import load_scoring_changes
from extract import extract_terms
from structure import structure_filing_extractions
from ui import (
    TABLE_COLUMNS,
    cell_source,
    load_document_text,
    not_exact_mask,
    plain_status,
    scored_grounding,
    table_frame,
)
from validate import validate_comps_table


load_dotenv()

st.set_page_config(
    page_title="Bond Term Sheet Extractor",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.html("""<style>
.main .block-container {
    max-width: 1180px;
    padding-top: 1.5rem;
    padding-bottom: 2rem;
}
.table-wrap {
    overflow-x: auto;
    width: 100%;
    margin-bottom: 0.5rem;
}
table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.88rem;
    line-height: 1.4;
}
th {
    border-top: 1px solid #D9D9D9;
    border-bottom: 1px solid #D9D9D9;
    padding: 6px 10px;
    font-weight: 600;
    text-align: left;
    background-color: transparent;
}
td {
    border-bottom: 1px solid #D9D9D9;
    padding: 6px 10px;
    text-align: left;
}
th.num, td.num {
    text-align: right;
    font-variant-numeric: tabular-nums;
}
mark {
    background-color: #FFF1B8;
    padding: 1px 2px;
}
.muted {
    color: #5F6368;
}
.accent {
    color: #1F3A5F;
    font-weight: 500;
}
hr.thin {
    border: 0;
    border-top: 1px solid #D9D9D9;
    margin: 1.25rem 0;
}
</style>""")


@st.cache_data
def get_cached_visualization_html(fixture_path_str: str) -> str:
    """Cache runtime HTML visualization generation from fixture JSONL."""
    return build_visualization_html(fixture_path_str)


def build_deal_line(df: pd.DataFrame) -> str:
    """Constructs sell-side research summary line from comps dataframe."""
    issuer = "Unknown Issuer"
    if "Issuer" in df.columns:
        issuers = df["Issuer"].dropna()
        if not issuers.empty:
            raw_iss = str(issuers.iloc[0]).strip()
            issuer = raw_iss.title() if raw_iss.isupper() else raw_iss

    total_m = 0.0
    for col in ["Principal ($M)", "Size ($M)"]:
        if col in df.columns:
            nums = df[col].dropna()
            if not nums.empty:
                total_m = float(nums.sum())
                break

    if total_m >= 1000:
        val = total_m / 1000.0
        size_str = f"${int(val)}bn" if val.is_integer() else f"${val:.1f}bn"
    else:
        size_str = f"${total_m:,.1f}m"

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


# 1. Title and one sentence
st.title("Bond Term Sheet Extractor")
st.markdown("Turn a bond term sheet into a comps table, with every number traced back to the SEC filing.")

# 2. How to use it
st.markdown("Pick a deal, read the table, then click any number to see the sentence it came from.")

# 3. Step 1: Pick a deal
st.subheader("1. Pick a deal")
benchmark_deals = list_benchmark_deals()
deal_options = {d["label"]: d for d in benchmark_deals}
labels = list(deal_options.keys())
default_idx = 0
for i, d in enumerate(benchmark_deals):
    if "AAPL" in d["deal_key"]:
        default_idx = i
        break

selected_label = st.selectbox("Sample deals", labels, index=default_idx)

# Determine active deal
selected_deal = deal_options[selected_label]
if st.session_state.get("active_deal_label") != selected_label:
    st.session_state["active_deal_label"] = selected_label
    st.session_state["is_uploaded"] = False

if st.session_state.get("is_uploaded") and st.session_state.get("uploaded_jsonl"):
    selected_jsonl = Path(st.session_state["uploaded_jsonl"])
    deal_identifier = "uploaded_term_sheet"
    is_uploaded = True
else:
    selected_jsonl = Path(selected_deal["fixture_path"])
    deal_identifier = selected_deal["deal_key"]
    is_uploaded = False

df, audit_records = structure_filing_extractions(selected_jsonl)
validated_df = validate_comps_table(df, audit_records)

if is_uploaded:
    st.markdown("**Uploaded term sheet**")
else:
    st.markdown(f"**{build_deal_line(validated_df)}**")

# 4. Step 2: Read the table
st.subheader("2. Read the table")

tf = table_frame(validated_df)
mask = not_exact_mask(validated_df, audit_records)


def highlight_not_exact(data: pd.DataFrame) -> pd.DataFrame:
    styles = pd.DataFrame("", index=data.index, columns=data.columns)
    for col in data.columns:
        if col in mask.columns:
            styles[col] = [
                "background-color: #FFF1B8" if is_not_exact else ""
                for is_not_exact in mask[col]
            ]
    return styles


styled = tf.style.apply(highlight_not_exact, axis=None)

column_config: dict[str, Any] = {}
for col_label, _, _, col_help in TABLE_COLUMNS:
    if col_label == "Size ($M)":
        column_config[col_label] = st.column_config.NumberColumn(
            col_label,
            help=col_help,
            format="$%,.1fM",
        )
    elif col_label in ("Coupon", "Yield"):
        column_config[col_label] = st.column_config.NumberColumn(
            col_label,
            help=col_help,
            format="%.3f%%",
        )
    elif col_label == "Price":
        column_config[col_label] = st.column_config.NumberColumn(
            col_label,
            help=col_help,
            format="%.3f",
        )
    elif col_label == "Spread (bps)":
        column_config[col_label] = st.column_config.NumberColumn(
            col_label,
            help=col_help,
            format="+%d bps",
        )
    else:
        column_config[col_label] = st.column_config.Column(
            col_label,
            help=col_help,
            width="large" if col_label == "Check" else None,
        )

selection_default = (
    {"selection": {"cells": [(0, "Coupon")]}}
    if len(tf) > 0
    else {"selection": {"cells": []}}
)

st.dataframe(
    styled,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-cell",
    key="comps",
    column_config=column_config,
    selection_default=selection_default,
)

st.html(
    '<div style="font-size: 0.85rem; margin-top: 0.3rem; margin-bottom: 0.5rem;">'
    '<span style="display: inline-block; width: 12px; height: 12px; background-color: #FFF1B8; border: 1px solid #D9D9D9; vertical-align: middle; margin-right: 6px;"></span>'
    'Found, but the match is not exact. Click it to see the filing text.'
    '</div>'
)

excel_buffer = io.BytesIO()
with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
    validated_df.to_excel(writer, sheet_name="Comps Table", index=False)
excel_data = excel_buffer.getvalue()

st.download_button(
    label="Download .xlsx",
    data=excel_data,
    file_name=f"{deal_identifier}_comps_table.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

# 5. Step 3: Check any number
st.subheader("3. Check any number")
doc_text = load_document_text(selected_jsonl)

comps_state = st.session_state.get("comps")
selected_cells = []
if isinstance(comps_state, dict):
    selected_cells = comps_state.get("selection", {}).get("cells", [])

cs = None
if selected_cells:
    cell_row, cell_col = selected_cells[0]
    cs = cell_source(audit_records, cell_row, cell_col, validated_df, doc_text)

if cs is not None:
    status = cs["status"]
    if status == "Found word for word":
        status_color = "#1E6B3A"
    elif status == "Found, but the match is not exact":
        status_color = "#8A5A00"
    else:
        status_color = "#5F6368"

    card_lines = [
        '<div style="border: 1px solid #D9D9D9; border-radius: 6px; padding: 1rem 1.25rem; margin: 0.5rem 0 1rem 0; background-color: #FAFAFA;">',
        f'<div style="font-weight: 600; font-size: 0.95rem; color: #333333;">{html.escape(cs["field"])} · {html.escape(cs["tranche"])}</div>',
        f'<div style="font-size: 1.8rem; font-weight: 700; margin: 0.2rem 0; color: #111111;">{html.escape(cs["value"])}</div>',
        f'<div style="color: {status_color}; font-weight: 500; font-size: 0.9rem; margin-bottom: 0.75rem;">{html.escape(status)}</div>',
    ]
    if cs["quote_html"]:
        card_lines.extend([
            '<div style="font-size: 0.85rem; font-weight: 600; margin-bottom: 0.25rem;">From the filing</div>',
            f'<div style="font-size: 0.9rem; line-height: 1.5; color: #222222;">{cs["quote_html"]}</div>',
        ])
    card_lines.append('</div>')
    if status == "Found, but the match is not exact":
        card_lines.insert(
            4,
            '<div style="color: #5F6368; font-size: 0.85rem; margin: -0.5rem 0 0.75rem 0;">'
            "The value is in the filing, but the extracted text does not line up exactly with it. "
            "Compare it with the text below.</div>",
        )
    st.html("".join(card_lines))
else:
    st.markdown("Click any number in the table to see the sentence it came from.")

# 6. How well does it work?
st.subheader("How well does it work?")
acc_info = parse_accuracy_report()
if acc_info:
    m1 = re.search(
        r"Field accuracy:\s*([0-9.]+)%\s*\(([0-9]+)/([0-9]+)\s*fields,\s*([0-9]+)\s*deals",
        acc_info.get("headline_line", ""),
    )
    if m1:
        pct, correct, total, deals = m1.group(1), m1.group(2), m1.group(3), m1.group(4)
        st.markdown(
            f"On {deals} sample deals with hand-checked answers, it got {correct} of {total} values right ({pct}%)."
        )

    m2 = re.search(r"Grounded:\s*([0-9.]+)%", acc_info.get("grounded_line", ""))
    if m2:
        g_pct = m2.group(1)
        st.markdown(
            f"{g_pct}% of values were found word for word in the filing. The rest are marked in the table so you can check them."
        )

    m3 = re.search(r"Not-in-source:\s*[0-9.]+%\s*\(([0-9]+)/([0-9]+)", acc_info.get("not_in_source_line", ""))
    if m3:
        nis_count, nis_total = m3.group(1), m3.group(2)
        st.markdown(
            f"None were made up: {nis_count} of {nis_total} values were missing from the filing."
        )

    scoring_changes = load_scoring_changes(Path("data/fixtures/scoring_changes.jsonl"))
    if scoring_changes:
        first_change = scoring_changes[0]
        m_before = re.search(r"([0-9.]+%)\s*\(([0-9]+/[0-9]+)", first_change.get("headline_before", ""))
        m_after = re.search(r"([0-9.]+%)", acc_info.get("headline_line", ""))
        if m_before and m_after:
            scoring_text = (
                f"First scored {m_before.group(1)} ({m_before.group(2)}). A CUSIP formatting fix after the run, "
                f"with no new extraction, gave {m_after.group(1)}."
            )
            st.markdown(f'<div class="muted" style="font-size: 0.85rem;">{scoring_text}</div>', unsafe_allow_html=True)

g_res = scored_grounding(audit_records)
n_bonds = len(validated_df)
bond_phrase = f"all {n_bonds} bonds" if n_bonds > 1 else f"{n_bonds} bond"
deal_grounded_line = (
    f"This deal: {g_res['percent']:.1f}% found word for word "
    f"({g_res['grounded']} of {g_res['extracted']} values, {bond_phrase})."
)
st.markdown(f'<div class="muted" style="font-size: 0.85rem;">{deal_grounded_line}</div>', unsafe_allow_html=True)

# 7. Collapsed sections
with st.expander("Full filing with highlights", expanded=False):
    try:
        html_content = get_cached_visualization_html(str(selected_jsonl))
        st.iframe(visualization_src(html_content), height=600, width="stretch")
    except Exception as e:
        st.warning(f"Could not load visualization: {e}")

with st.expander("Validation details", expanded=False):
    for _, r in validated_df.iterrows():
        st.markdown(f"**{r['Tranche']}**")
        st.text(f"Status: {r.get('Validation Status', 'n/a')}")
        st.text(f"Issues: {r.get('Validation Issues', 'None')}")
        st.text(f"Bookrunners: {r.get('Bookrunners', 'n/a')}")
        st.text(f"Ratings: {r.get('Ratings', 'n/a')}")
        st.text(f"Trade date: {r.get('Trade Date', 'n/a')}")
        st.text(f"Settlement date: {r.get('Settlement Date', 'n/a')}")

with st.expander("Try your own term sheet", expanded=False):
    app_password = None
    try:
        if hasattr(st, "secrets") and "APP_PASSWORD" in st.secrets:
            app_password = st.secrets["APP_PASSWORD"]
    except Exception:
        app_password = None

    if not app_password or not str(app_password).strip():
        st.info("Live extraction is disabled on this deployment")
    else:
        entered_password = st.text_input("Password", type="password")
        if not check_password(entered_password, app_password):
            if entered_password:
                st.error("Incorrect password.")
            else:
                st.caption("Password required to enable live extraction.")
        else:
            uploaded = st.file_uploader("Upload Term Sheet (.txt)", type=["txt"])
            if uploaded:
                content_bytes = uploaded.getvalue()
                is_valid, size_err = check_upload_size(len(content_bytes))
                if not is_valid:
                    st.error(size_err)
                else:
                    upload_hash = hash(content_bytes)
                    if st.session_state.get("upload_hash") != upload_hash:
                        upload_temp_dir = Path(tempfile.mkdtemp())
                        st.session_state["upload_temp_dir"] = upload_temp_dir
                        st.session_state["upload_hash"] = upload_hash
                    else:
                        upload_temp_dir = st.session_state["upload_temp_dir"]

                    saved_path = save_uploaded_filing(content_bytes, target_dir=upload_temp_dir)
                    if st.button("Extract", type="primary"):
                        secrets_dict = dict(st.secrets) if hasattr(st, "secrets") else None
                        gemini_key = get_gemini_api_key(secrets_dict)
                        if not gemini_key:
                            st.error("Gemini API key is not configured in secrets or environment.")
                        else:
                            os.environ["GEMINI_API_KEY"] = gemini_key
                            os.environ["GOOGLE_API_KEY"] = gemini_key
                            with st.spinner("Extracting terms with LangExtract..."):
                                try:
                                    extract_terms(
                                        saved_path,
                                        model_id="gemini-3.5-flash-lite",
                                        log_attempt=False,
                                        output_dir=upload_temp_dir,
                                    )
                                    extracted_jsonl = upload_temp_dir / f"{saved_path.stem}_extractions.jsonl"
                                    st.session_state["uploaded_jsonl"] = extracted_jsonl
                                    st.session_state["is_uploaded"] = True
                                    st.success("Extraction complete!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Extraction error: {e}")

# 8. Footer
st.html('<hr class="thin">')
st.markdown('<div class="muted" style="font-size: 0.85rem;">Code: github.com/dini2-byte/bond-term-sheet-extractor. Built on langextract and edgartools.</div>', unsafe_allow_html=True)
