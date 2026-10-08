"""
app.py: Streamlit web application for Bond Term Sheet Extractor.
DCM comps table generation, interactive source text drill-down,
runtime LangExtract HTML highlighting, and Excel download.
"""

import io
import os
from pathlib import Path
import pandas as pd
import streamlit as st
import tempfile
from dotenv import load_dotenv

from demo import (
    list_benchmark_deals,
    build_visualization_html,
    check_password,
    check_upload_size,
    get_gemini_api_key,
    save_uploaded_filing,
    parse_accuracy_report,
)
from extract import extract_terms
from structure import structure_filing_extractions, export_comps_to_excel, grounding_summary
from validate import validate_comps_table


load_dotenv()

st.set_page_config(
    page_title="Bond Term Sheet Extractor | DCM Comps Engine",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for Finance Analyst Aesthetics
st.markdown("""
<style>
    .main-title {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        font-size: 2.1rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 12px 16px;
        text-align: center;
    }
    .metric-val {
        font-size: 1.5rem;
        font-weight: 700;
        color: #0F172A;
    }
    .metric-label {
        font-size: 0.8rem;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .badge-grounded {
        background-color: #DCFCE7;
        color: #166534;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">Bond Term Sheet Extractor</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">AI-Native DCM Comps Table Engine with Exact Source Grounding</div>', unsafe_allow_html=True)

# Section: How accurate is this?
acc_info = parse_accuracy_report()
if acc_info:
    st.markdown("### How accurate is this?")
    accuracy_lines = [
        acc_info["headline_line"],
        acc_info["grounded_line"],
        acc_info["not_in_source_line"],
    ]
    for change_line in acc_info.get("scoring_change_lines", []):
        accuracy_lines.append(change_line)
    accuracy_lines.append(acc_info["benchmark_line"])
    st.markdown("\n\n".join(accuracy_lines))

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@st.cache_data
def get_cached_visualization_html(fixture_path_str: str) -> str:
    """Cache runtime HTML visualization generation from fixture JSONL."""
    return build_visualization_html(fixture_path_str)


# Sidebar Controls
st.sidebar.header("📁 Deal Selection")
input_mode = st.sidebar.radio(
    "Source",
    ["Benchmark deals", "Upload a term sheet"],
    index=0,
)

selected_jsonl: Path | None = None
deal_identifier: str = ""
trigger_extraction = False
file_to_extract: Path | None = None

if input_mode == "Benchmark deals":
    benchmark_deals = list_benchmark_deals()
    if benchmark_deals:
        deal_options = {d["label"]: d for d in benchmark_deals}
        labels = list(deal_options.keys())
        default_idx = 0
        for i, d in enumerate(benchmark_deals):
            if "AAPL" in d["deal_key"]:
                default_idx = i
                break
        selected_label = st.sidebar.selectbox("Select Deal", labels, index=default_idx)
        selected_deal = deal_options[selected_label]
        selected_jsonl = Path(selected_deal["fixture_path"])
        deal_identifier = selected_deal["deal_key"]
    else:
        st.sidebar.warning("No benchmark deals found in data/fixtures/.")

elif input_mode == "Upload a term sheet":
    app_password = None
    try:
        if hasattr(st, "secrets") and "APP_PASSWORD" in st.secrets:
            app_password = st.secrets["APP_PASSWORD"]
    except Exception:
        app_password = None

    if not app_password or not str(app_password).strip():
        st.sidebar.info("Live extraction is disabled on this deployment")
    else:
        entered_password = st.sidebar.text_input("Password", type="password")
        if not check_password(entered_password, app_password):
            if entered_password:
                st.sidebar.error("Incorrect password.")
            else:
                st.sidebar.caption("Password required to enable live extraction.")
        else:
            uploaded = st.sidebar.file_uploader("Upload Term Sheet (.txt)", type=["txt"])
            if uploaded:
                content_bytes = uploaded.getvalue()
                is_valid, size_err = check_upload_size(len(content_bytes))
                if not is_valid:
                    st.sidebar.error(size_err)
                else:
                    upload_hash = hash(content_bytes)
                    if st.session_state.get("upload_hash") != upload_hash:
                        upload_temp_dir = Path(tempfile.mkdtemp())
                        st.session_state["upload_temp_dir"] = upload_temp_dir
                        st.session_state["upload_hash"] = upload_hash
                    else:
                        upload_temp_dir = st.session_state["upload_temp_dir"]

                    saved_path = save_uploaded_filing(content_bytes, target_dir=upload_temp_dir)
                    file_to_extract = saved_path
                    deal_identifier = "uploaded_term_sheet"
                    col_btn, _ = st.columns([1, 3])
                    with col_btn:
                        trigger_extraction = st.button("⚡ Extract Bond Terms", type="primary")

                    extracted_cache = upload_temp_dir / f"{saved_path.stem}_extractions.jsonl"
                    if extracted_cache.exists():
                        selected_jsonl = extracted_cache

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Trustworthiness Engine")
st.sidebar.info(
    "**Source Grounding Gate**: Active\n\n"
    "Every value links to the exact text it came from. "
    "Values that are not an exact match are flagged as not grounded. "
    "Fields not stated in the filing show Not found."
)

if trigger_extraction and file_to_extract:
    secrets_dict = dict(st.secrets) if hasattr(st, "secrets") else None
    gemini_key = get_gemini_api_key(secrets_dict)
    if not gemini_key:
        st.error("Gemini API key is not configured in secrets or environment.")
        st.stop()

    os.environ["GEMINI_API_KEY"] = gemini_key
    os.environ["GOOGLE_API_KEY"] = gemini_key

    with st.spinner("Extracting terms with LangExtract (gemini-3.5-flash-lite)..."):
        try:
            upload_dir = file_to_extract.parent
            extract_terms(
                file_to_extract,
                model_id="gemini-3.5-flash-lite",
                log_attempt=False,
                output_dir=upload_dir,
            )
            selected_jsonl = upload_dir / f"{file_to_extract.stem}_extractions.jsonl"
            st.success("Extraction complete!")
        except Exception as e:
            st.error(f"Extraction error: {e}")
            st.stop()

if selected_jsonl and selected_jsonl.exists():
    df, audit_records = structure_filing_extractions(selected_jsonl)
    validated_df = validate_comps_table(df, audit_records)

    # Overview Metrics
    total_tranches = len(validated_df)
    total_principal = validated_df["Principal ($M)"].sum()
    avg_yield = validated_df["Yield (%)"].mean()
    passed_count = (validated_df["Validation Status"] == "PASSED").sum()
    g_summary = grounding_summary(audit_records)
    g_pct = g_summary["pct"]
    g_color = "#16A34A" if g_pct == 100.0 else "#D97706"
    g_grounded = g_summary["grounded"]
    g_total = g_summary["total"]

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f'<div class="metric-card"><div class="metric-val">{total_tranches}</div><div class="metric-label">Tranches Extracted</div></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="metric-card"><div class="metric-val">${total_principal:,.1f}M</div><div class="metric-label">Deal Size</div></div>', unsafe_allow_html=True)
    with m3:
        st.markdown(f'<div class="metric-card"><div class="metric-val">{avg_yield:.3f}%</div><div class="metric-label">Average Yield</div></div>', unsafe_allow_html=True)
    with m4:
        st.markdown(f'<div class="metric-card"><div class="metric-val" style="color: {g_color};">{g_pct:.1f}%</div><div class="metric-label">Grounded</div><div style="font-size: 0.75rem; color: #64748B;">{g_grounded}/{g_total} fields exact</div></div>', unsafe_allow_html=True)

    st.markdown("### 📋 Debt Capital Markets (DCM) Comps Table")

    display_cols = [
        "Tranche", "Principal ($M)", "Coupon (%)", "Issue Price",
        "Yield (%)", "Spread (bps)", "Benchmark Treasury", "Maturity Date",
        "Day Count", "Par Call Date", "CUSIP", "Validation Status"
    ]

    st.dataframe(
        validated_df[display_cols].style.format({
            "Principal ($M)": "${:,.1f}M",
            "Coupon (%)": "{:.3f}%",
            "Issue Price": "{:.3f}",
            "Yield (%)": "{:.3f}%",
            "Spread (bps)": "+{} bps",
        }),
        width="stretch",
        height=200,
    )

    # Excel Download
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        validated_df.to_excel(writer, sheet_name="Comps Table", index=False)
    excel_data = excel_buffer.getvalue()

    st.download_button(
        label="📥 Download Comps Table (.xlsx)",
        data=excel_data,
        file_name=f"{deal_identifier}_comps_table.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    # Tabs for Source Grounding & Detailed Inspection
    tab1, tab2, tab3 = st.tabs(["🔍 Source Grounding Drill-Down", "🎨 Interactive Highlighted Source", "📜 Validation & Audit Log"])

    with tab1:
        st.markdown("#### Click a tranche to audit character offsets behind every cell")
        selected_tranche_name = st.selectbox(
            "Select Tranche to Inspect",
            validated_df["Tranche"].tolist()
        )
        tranche_idx = validated_df[validated_df["Tranche"] == selected_tranche_name].index[0]
        audit_entry = audit_records[tranche_idx]["fields"]

        audit_rows = []
        for field_name, meta in audit_entry.items():
            interval = meta.get("char_interval")
            offset_str = f"[{interval.get('start_pos')}:{interval.get('end_pos')}]" if interval else "N/A"
            grounded = meta.get("grounded", False)
            quality = meta.get("grounding_quality", "none")
            alignment = meta.get("alignment_status") or "none"
            span_text = meta.get("span_text")

            if grounded:
                badge = "✅ Exact"
            elif interval:
                badge = f"⚠️ Weak ({quality})"
            else:
                badge = "❌ Ungrounded"

            audit_rows.append({
                "Field": field_name,
                "Extracted Value": meta.get("raw"),
                "Character Span": offset_str,
                "Alignment": alignment,
                "Source Span Text": span_text if span_text is not None else "N/A",
                "Grounded in Source": badge,
            })

        st.dataframe(pd.DataFrame(audit_rows), width="stretch")

    with tab2:
        st.markdown("#### LangExtract Interactive Grounding Viewer")
        st.caption("Visual audit showing all extractions mapped and color-highlighted in the original SEC text.")
        try:
            html_content = get_cached_visualization_html(str(selected_jsonl))
            st.iframe(html_content, height=600, width="stretch")
        except Exception as e:
            st.warning(f"Could not load visualization: {e}")

    with tab3:
        st.markdown("#### Quality & Sanity Rules Audit")
        for _, r in validated_df.iterrows():
            with st.expander(f"{r['Tranche']} — {r['Validation Status']}"):
                st.write(f"**Issues Flagged**: {r['Validation Issues']}")
                st.write(f"**Bookrunners**: {r['Bookrunners']}")
                st.write(f"**Credit Ratings**: {r['Ratings']}")
                st.write(f"**Trade / Settlement**: {r['Trade Date']} / {r['Settlement Date']}")
else:
    if input_mode == "Benchmark deals":
        st.info("Select a benchmark deal from the sidebar.")
    else:
        st.info("Provide password and upload a term sheet to begin.")

st.markdown("---")
st.markdown("Code and benchmark: https://github.com/dini2-byte/bond-term-sheet-extractor")
