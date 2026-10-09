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
    comps_table_html,
    field_rows,
    load_document_text,
    scored_grounding,
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

    n_tranches = len(df)
    tr_str = f"{n_tranches} tranche" if n_tranches == 1 else f"{n_tranches} tranches"

    priced_str = ""
    for col in ["Trade Date", "Trade date"]:
        if col in df.columns:
            dates = df[col].dropna()
            if not dates.empty and str(dates.iloc[0]).strip():
                priced_str = f"priced {dates.iloc[0]}"
                break

    parts = [issuer, f"{size_str} senior notes", tr_str]
    if priced_str:
        parts.append(priced_str)
    return " · ".join(parts)


def tranche_selector_options(df: pd.DataFrame) -> list[str]:
    """
    Labels each tranche by maturity year when all tranches have distinct years,
    otherwise by tranche name.
    """
    years: list[str | None] = []
    for _, r in df.iterrows():
        mat = r.get("Maturity Date") or r.get("Maturity") or ""
        match = re.search(r"\b(20\d{2})\b", str(mat))
        if match:
            years.append(match.group(1))
        else:
            tr_match = re.search(r"\b(20\d{2})\b", str(r.get("Tranche", "")))
            if tr_match:
                years.append(tr_match.group(1))
            else:
                years.append(None)

    if len(years) == len(df) and all(y is not None for y in years) and len(set(years)) == len(years):
        return [str(y) for y in years]
    return df["Tranche"].astype(str).tolist()


# 1. Header & Deal Picker
benchmark_deals = list_benchmark_deals()
deal_options = {d["label"]: d for d in benchmark_deals}
labels = list(deal_options.keys())
default_idx = 0
for i, d in enumerate(benchmark_deals):
    if "AAPL" in d["deal_key"]:
        default_idx = i
        break

col_header, col_deal = st.columns([3, 2])
with col_header:
    st.title("Bond Term Sheet Extractor")
    st.markdown("Pulls pricing terms for investment-grade bond deals out of SEC term sheets and builds a comps table. Every value links to the text it came from.")

with col_deal:
    selected_label = st.selectbox("Deal", labels, index=default_idx)

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

# 2. Deal Line
if is_uploaded:
    st.markdown("**Uploaded term sheet**")
else:
    st.markdown(f"**{build_deal_line(validated_df)}**")

# 3. Benchmark line
acc_info = parse_accuracy_report()
if acc_info:
    benchmark_summary = " · ".join([
        acc_info["headline_line"],
        acc_info["grounded_line"],
        acc_info["not_in_source_line"],
    ])
    st.markdown(benchmark_summary)

    scoring_changes = load_scoring_changes(Path("data/fixtures/scoring_changes.jsonl"))
    if scoring_changes:
        first_change = scoring_changes[0]
        m_before = re.search(r"([0-9.]+%)\s*\(([0-9]+/[0-9]+)", first_change.get("headline_before", ""))
        m_after = re.search(r"([0-9.]+%)", acc_info["headline_line"])
        if m_before and m_after:
            scoring_text = (
                f"First scored {m_before.group(1)} ({m_before.group(2)}). A CUSIP formatting fix after the run, "
                f"with no new extraction, gave {m_after.group(1)}."
            )
            st.markdown(f'<div class="muted" style="font-size: 0.85rem;">{scoring_text}</div>', unsafe_allow_html=True)

st.html('<hr class="thin">')

# 4. Comps Table & Excel Download
excel_buffer = io.BytesIO()
with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
    validated_df.to_excel(writer, sheet_name="Comps Table", index=False)
excel_data = excel_buffer.getvalue()

col_tbl_space, col_download = st.columns([5, 1])
with col_download:
    st.download_button(
        label="Download .xlsx",
        data=excel_data,
        file_name=f"{deal_identifier}_comps_table.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

st.html(comps_table_html(validated_df, audit_records))

st.markdown(
    '<div style="font-size: 0.85rem; margin-top: 0.4rem;">'
    '† Not grounded: the value was extracted but its text is not an exact match in the filing.'
    '</div>',
    unsafe_allow_html=True,
)

g_res = scored_grounding(audit_records)
tranche_count = len(validated_df)
tranche_phrase = f"all {tranche_count} tranches" if tranche_count > 1 else f"{tranche_count} tranche"
grounded_line = (
    f"Grounded: {g_res['percent']:.1f}% "
    f"({g_res['grounded']}/{g_res['extracted']} extracted fields, {tranche_phrase})"
)
st.markdown(
    f'<div class="muted" style="font-size: 0.85rem; margin-top: 0.2rem;">{grounded_line}</div>',
    unsafe_allow_html=True,
)

# 5. Where each value came from
st.subheader("Where each value came from")
tranche_options = tranche_selector_options(validated_df)
selected_tranche_opt = st.segmented_control(
    "Select tranche",
    options=tranche_options,
    default=tranche_options[0] if tranche_options else None,
    label_visibility="collapsed",
)

tranche_idx = 0
if selected_tranche_opt and selected_tranche_opt in tranche_options:
    tranche_idx = tranche_options.index(selected_tranche_opt)

doc_text = load_document_text(selected_jsonl)
rows = field_rows(audit_records[tranche_idx], doc_text)

source_table_lines = [
    '<div class="table-wrap">',
    "<table>",
    "<thead><tr>",
    "<th>Field</th><th>Value</th><th>Status</th><th>Source text</th>",
    "</tr></thead>",
    "<tbody>",
]
for r in rows:
    f_esc = html.escape(r["field"])
    v_esc = html.escape(r["value"]) if r["value"] != "Not found" else '<span class="muted">Not found</span>'
    status_str = r["status"]
    if status_str == "not exact":
        s_html = '<span class="accent">not exact</span>'
    elif status_str == "not found":
        s_html = '<span class="muted">not found</span>'
    else:
        s_html = "exact"
    q_html = r["quote_html"] if r["quote_html"] else '<span class="muted">n/a</span>'
    source_table_lines.append(f"<tr><td>{f_esc}</td><td>{v_esc}</td><td>{s_html}</td><td>{q_html}</td></tr>")
source_table_lines.extend(["</tbody>", "</table>", "</div>"])
st.html("".join(source_table_lines))

# 6. Collapsed sections (Expanders)
with st.expander("Full filing with highlights", expanded=False):
    try:
        html_content = get_cached_visualization_html(str(selected_jsonl))
        st.iframe(visualization_src(html_content), height=600, width="stretch")
    except Exception as e:
        st.warning(f"Could not load visualization: {e}")

with st.expander("Validation checks", expanded=False):
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

# 7. Footer
st.html('<hr class="thin">')
st.markdown('<div class="muted" style="font-size: 0.85rem;">Code: github.com/dini2-byte/bond-term-sheet-extractor. Built on langextract and edgartools.</div>', unsafe_allow_html=True)
