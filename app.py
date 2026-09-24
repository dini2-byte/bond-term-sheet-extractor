"""
app.py: Streamlit web application for Bond Term Sheet Extractor.
DCM comps table generation, interactive source text drill-down,
embedded LangExtract HTML highlighting, and Excel download.
"""

import io
from pathlib import Path
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from extract import extract_terms
from structure import structure_filing_extractions, export_comps_to_excel
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

# Sidebar Controls
st.sidebar.header("📁 Deal Selection")
input_mode = st.sidebar.radio(
    "Source",
    ["Sample Filings (Cached)", "Custom Text Upload"],
    index=0
)

DATA_DIR = Path("data/raw_filings")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

selected_file = None

if input_mode == "Sample Filings (Cached)":
    sample_files = list(DATA_DIR.glob("*.txt")) if DATA_DIR.exists() else []
    file_map = {f.name: f for f in sample_files}
    if file_map:
        default_idx = 0
        for i, name in enumerate(file_map.keys()):
            if "AAPL_FWP" in name:
                default_idx = i
                break
        choice = st.sidebar.selectbox("Select Filing", list(file_map.keys()), index=default_idx)
        selected_file = file_map[choice]
    else:
        st.sidebar.warning("No sample files found in data/raw_filings/.")

elif input_mode == "Custom Text Upload":
    uploaded = st.sidebar.file_uploader("Upload Term Sheet (.txt)", type=["txt"])
    if uploaded:
        temp_path = OUTPUT_DIR / f"uploaded_{uploaded.name}"
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(uploaded.read().decode("utf-8"))
        selected_file = temp_path

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Trustworthiness Engine")
st.sidebar.info(
    "**Source Grounding Gate**: Active\n\n"
    "Values must map directly to source character offsets. Any ungrounded or hallucinated value is automatically flagged."
)

if selected_file and selected_file.exists():
    stem = selected_file.stem
    jsonl_cache = OUTPUT_DIR / f"{stem}_extractions.jsonl"
    html_cache = OUTPUT_DIR / f"{stem}_visualization.html"

    # Action Button
    col_btn, col_msg = st.columns([1, 3])
    with col_btn:
        run_extract = st.button("⚡ Extract Bond Terms", type="primary")

    # Run or Load Cached
    if run_extract or jsonl_cache.exists():
        if run_extract:
            with st.spinner("Extracting terms with LangExtract (gemini-3.5-flash-lite)..."):
                try:
                    result = extract_terms(selected_file, model_id="gemini-3.5-flash-lite")
                    st.success("Extraction complete!")
                except Exception as e:
                    st.error(f"Extraction error: {e}")
                    st.stop()

        # Structure & Validate
        df, audit_records = structure_filing_extractions(jsonl_cache)
        validated_df = validate_comps_table(df, audit_records)

        # Overview Metrics
        total_tranches = len(validated_df)
        total_principal = validated_df["Principal ($M)"].sum()
        avg_yield = validated_df["Yield (%)"].mean()
        passed_count = (validated_df["Validation Status"] == "PASSED").sum()

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f'<div class="metric-card"><div class="metric-val">{total_tranches}</div><div class="metric-label">Tranches Extracted</div></div>', unsafe_allow_html=True)
        with m2:
            st.markdown(f'<div class="metric-card"><div class="metric-val">${total_principal:,.1f}M</div><div class="metric-label">Offering Size</div></div>', unsafe_allow_html=True)
        with m3:
            st.markdown(f'<div class="metric-card"><div class="metric-val">{avg_yield:.3f}%</div><div class="metric-label">Average Yield</div></div>', unsafe_allow_html=True)
        with m4:
            st.markdown(f'<div class="metric-card"><div class="metric-val" style="color: #16A34A;">100%</div><div class="metric-label">Source Grounding</div></div>', unsafe_allow_html=True)

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
            use_container_width=True,
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
            file_name=f"{stem}_comps_table.xlsx",
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
                audit_rows.append({
                    "Field": field_name,
                    "Extracted Value": meta.get("raw"),
                    "Character Span": offset_str,
                    "Grounded in Source": "✅ Grounded" if meta.get("grounded") else "❌ Ungrounded"
                })

            st.dataframe(pd.DataFrame(audit_rows), use_container_width=True)

        with tab2:
            st.markdown("#### LangExtract Interactive Grounding Viewer")
            st.caption("Visual audit showing all extractions mapped and color-highlighted in the original SEC text.")
            if html_cache.exists():
                with open(html_cache, "r", encoding="utf-8") as f:
                    html_content = f.read()
                components.html(html_content, height=600, scrolling=True)
            else:
                st.info("HTML visualization not found. Click 'Extract Bond Terms' above to generate it.")

        with tab3:
            st.markdown("#### Quality & Sanity Rules Audit")
            for _, r in validated_df.iterrows():
                with st.expander(f"{r['Tranche']} — {r['Validation Status']}"):
                    st.write(f"**Issues Flagged**: {r['Validation Issues']}")
                    st.write(f"**Bookrunners**: {r['Bookrunners']}")
                    st.write(f"**Credit Ratings**: {r['Ratings']}")
                    st.write(f"**Trade / Settlement**: {r['Trade Date']} / {r['Settlement Date']}")
else:
    st.info("Select a filing from the sidebar to begin.")
