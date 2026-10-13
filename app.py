"""
app.py: Streamlit web application for Bond Term Sheet Extractor.
Pulls pricing terms for investment-grade bond deals out of SEC term sheets
and builds a comps table with source grounding.
"""

import html
import io
import logging
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
from extract import extract_terms
import lookup
from lookup import (
    RunBudget,
    edgar_filing_url,
    find_term_sheets,
    get_edgar_identity,
    normalize_ticker,
)
from structure import structure_filing_extractions
from ui import (
    TABLE_COLUMNS,
    cell_source,
    load_document_text,
    not_exact_mask,
    plain_status,
    size_help,
    size_label,
    table_frame,
)
from validate import validate_comps_table


load_dotenv()
logger = logging.getLogger(__name__)


@st.cache_resource
def get_run_budget() -> RunBudget:
    return lookup.RunBudget()



@st.cache_data(ttl=86400, show_spinner=False)
def cached_find_term_sheets(ticker: str) -> list[dict[str, Any]]:
    return find_term_sheets(ticker)


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
st.title("Bond Term Sheet Extractor", anchor=False)
st.markdown("Turn a bond term sheet into a comps table, with every number traced back to the SEC filing.")

# 2. How to use it
st.markdown("Pick a deal, read the table, then click any number to see the sentence it came from.")

acc_info = parse_accuracy_report()
acc_match = re.search(
    r"Field accuracy:\s*([0-9.]+)%\s*\([0-9]+/[0-9]+\s*fields,\s*([0-9]+)\s*deals",
    (acc_info or {}).get("headline_line", ""),
)
if acc_match:
    st.caption(
        f"AI can make mistakes. On {acc_match.group(2)} hand-checked deals it got "
        f"{acc_match.group(1)}% of values right. Highlighted values are worth checking against the filing."
    )

# 3. Step 1: Pick a deal
st.subheader("1. Pick a deal", anchor=False)

deal_source = st.segmented_control(
    "Deal source",
    ["Saved deals", "Search company"],
    default="Saved deals",
    label_visibility="collapsed",
) or "Saved deals"

selected_jsonl: Path | None = None
deal_identifier: str | None = None
is_uploaded = False
is_live_run = False
live_deal_line: str = ""

if deal_source == "Saved deals":
    benchmark_deals = list_benchmark_deals()
    deal_options = {d["label"]: d for d in benchmark_deals}
    labels = list(deal_options.keys())
    default_idx = 0
    for i, d in enumerate(benchmark_deals):
        if "AAPL" in d["deal_key"]:
            default_idx = i
            break

    selected_label = st.selectbox("Saved deals", labels, index=default_idx)

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
else:
    # "Search company"
    secrets_dict = None
    try:
        if hasattr(st, "secrets"):
            secrets_dict = dict(st.secrets)
    except Exception:
        secrets_dict = None

    identity = get_edgar_identity(secrets_dict)
    if not identity:
        st.info("Company lookup is not set up on this deployment.")
    else:
        try:
            import edgar
            edgar.set_identity(identity)
        except Exception:
            pass

        ticker_input = st.text_input("Stock ticker", placeholder="KO")
        find_clicked = st.button("Find term sheets")
        if find_clicked:
            st.session_state["lookup_ticker"] = ticker_input
            st.session_state.pop("live_deal", None)

        active_ticker = st.session_state.get("lookup_ticker")
        term_sheets = None
        if active_ticker is not None:
            try:
                norm_ticker = normalize_ticker(active_ticker)
                with st.spinner("Searching SEC EDGAR..."):
                    term_sheets = cached_find_term_sheets(norm_ticker)
            except (ValueError, LookupError) as e:
                st.error(str(e))
            except Exception as e:
                logger.exception("SEC EDGAR lookup error: %s", e)
                st.error("SEC EDGAR did not respond. Try again in a minute.")

        if term_sheets is not None:
            if len(term_sheets) == 0:
                st.info(
                    f"No bond term sheets in {norm_ticker}'s latest 25 SEC filings. "
                    "Banks and brokers file many structured-note filings, which this tool skips."
                )
                st.markdown(f"[View {norm_ticker}'s filings on SEC EDGAR](https://www.sec.gov/edgar/browse/?CIK={norm_ticker})")
            else:
                options_indices = list(range(len(term_sheets)))

                def sheet_label(idx: int) -> str:
                    item = term_sheets[idx]
                    bc = item.get("bond_count", 0)
                    bword = "1 bond" if bc == 1 else f"{bc} bonds"
                    return f"Filed {item['filing_date']} · {bword}"

                selected_idx = st.selectbox(
                    "Recent bond term sheets",
                    options_indices,
                    format_func=sheet_label,
                )
                selected_sheet = term_sheets[selected_idx]
                filing_url = edgar_filing_url(selected_sheet["accession"])
                st.markdown(f"[View on SEC EDGAR]({filing_url})")

                budget = get_run_budget()
                col1, col2 = st.columns([1, 4])
                with col1:
                    extract_btn = st.button("Extract", type="primary")
                with col2:
                    st.markdown(
                        f'<div style="padding-top: 6px; font-size: 0.85rem;" class="muted">'
                        f'{budget.remaining()} of 20 free runs left today</div>',
                        unsafe_allow_html=True,
                    )

                if extract_btn:
                    session_runs = st.session_state.get("session_runs", 0)
                    can_run, reason = budget.can_run(session_runs)
                    gemini_key = get_gemini_api_key(secrets_dict)
                    if not can_run:
                        st.error(reason)
                    elif not gemini_key:
                        st.error("Live extraction is not set up on this deployment.")
                    else:
                        os.environ["GEMINI_API_KEY"] = gemini_key
                        os.environ["GOOGLE_API_KEY"] = gemini_key
                        temp_dir = Path(tempfile.mkdtemp())
                        filing_path = temp_dir / f"{norm_ticker}_{selected_sheet['accession']}.txt"
                        filing_path.write_text(selected_sheet["text"], encoding="utf-8")
                        with st.spinner("Extracting with Gemini. This takes about 20 seconds."):
                            try:
                                extract_terms(
                                    filing_path,
                                    model_id="gemini-3.5-flash-lite",
                                    log_attempt=False,
                                    output_dir=temp_dir,
                                )
                            except Exception as e:
                                logger.exception("Gemini extraction error: %s", e)
                                st.error("The extraction did not finish. Your run was not counted.")
                            else:
                                budget.record_run()
                                st.session_state["session_runs"] = session_runs + 1
                                extracted_jsonl = temp_dir / f"{filing_path.stem}_extractions.jsonl"
                                st.session_state["live_deal"] = {
                                    "jsonl_path": str(extracted_jsonl),
                                    "ticker": norm_ticker,
                                    "filing_date": selected_sheet["filing_date"],
                                    "accession": selected_sheet["accession"],
                                }
                                st.rerun()

    if st.session_state.get("live_deal"):
        live_deal = st.session_state["live_deal"]
        live_path = Path(live_deal["jsonl_path"])
        if live_path.exists():
            selected_jsonl = live_path
            deal_identifier = f"{live_deal['ticker']}_{live_deal['accession']}"
            is_uploaded = False
            is_live_run = True
            live_deal_line = f"{live_deal['ticker']} · term sheet filed {live_deal['filing_date']} · live run"
        else:
            st.session_state.pop("live_deal", None)
            selected_jsonl = None
            deal_identifier = None
            is_uploaded = False
            is_live_run = False

if selected_jsonl is not None and selected_jsonl.exists():
    df, audit_records = structure_filing_extractions(selected_jsonl)
    validated_df = validate_comps_table(df, audit_records)
    if is_uploaded:
        st.markdown("**Uploaded term sheet**")
    elif is_live_run:
        st.markdown(f"**{live_deal_line}**")
    else:
        st.markdown(f"**{build_deal_line(validated_df)}**")
else:
    df = None
    audit_records = None
    validated_df = None

# 4. Step 2: Read the table
st.subheader("2. Read the table", anchor=False)

if validated_df is not None and selected_jsonl is not None:
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
    curs = [c for c in validated_df["Currency"].dropna().unique() if c] if "Currency" in validated_df.columns else []
    current_size_label = size_label(curs)

    for col_label, _, _, col_help in TABLE_COLUMNS:
        target_label = current_size_label if col_label == "Size ($M)" else col_label
        if col_label == "Size ($M)":
            help_text = size_help(curs)
            if current_size_label == "Size (M)":
                column_config[target_label] = st.column_config.Column(
                    target_label,
                    help=help_text,
                )
            elif current_size_label == "Size (€M)":
                column_config[target_label] = st.column_config.NumberColumn(
                    target_label,
                    help=help_text,
                    format="€%,.1fM",
                )
            elif current_size_label == "Size (£M)":
                column_config[target_label] = st.column_config.NumberColumn(
                    target_label,
                    help=help_text,
                    format="£%,.1fM",
                )
            elif current_size_label == "Size (¥M)":
                column_config[target_label] = st.column_config.NumberColumn(
                    target_label,
                    help=help_text,
                    format="¥%,.1fM",
                )
            else:
                column_config[target_label] = st.column_config.NumberColumn(
                    target_label,
                    help=help_text,
                    format="$%,.1fM",
                )
        elif col_label in ("Coupon", "Yield"):
            column_config[target_label] = st.column_config.NumberColumn(
                target_label,
                help=col_help,
                format="%.3f%%",
            )
        elif col_label == "Price":
            column_config[target_label] = st.column_config.NumberColumn(
                target_label,
                help=col_help,
                format="%.3f",
            )
        elif col_label == "Spread (bps)":
            column_config[target_label] = st.column_config.Column(
                target_label,
                help=col_help,
            )
        else:
            column_config[target_label] = st.column_config.Column(
                target_label,
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

    if is_live_run:
        st.markdown(
            '<div class="muted" style="font-size: 0.85rem; margin-top: 0.25rem;">'
            'Live run: there is no hand-checked answer for this deal, so check values against the filing text.'
            '</div>',
            unsafe_allow_html=True,
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
else:
    st.markdown("Search for a company above and extract a term sheet to build the table.")

# 5. Step 3: Check any number
st.subheader("3. Check any number", anchor=False)

if validated_df is not None and selected_jsonl is not None:
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
else:
    st.markdown("Click any number in the table to see the sentence it came from.")

# 7. Collapsed sections
with st.expander("Full filing with highlights", expanded=False):
    if selected_jsonl is not None:
        try:
            html_content = get_cached_visualization_html(str(selected_jsonl))
            st.iframe(visualization_src(html_content), height=600, width="stretch")
        except Exception as e:
            st.warning(f"Could not load visualization: {e}")
    else:
        st.info("No term sheet loaded.")

with st.expander("Validation details", expanded=False):
    if validated_df is not None:
        for _, r in validated_df.iterrows():
            st.markdown(f"**{r['Tranche']}**")
            st.text(f"Status: {r.get('Validation Status', 'n/a')}")
            st.text(f"Issues: {r.get('Validation Issues', 'None')}")
            st.text(f"Bookrunners: {r.get('Bookrunners', 'n/a')}")
            st.text(f"Ratings: {r.get('Ratings', 'n/a')}")
            st.text(f"Trade date: {r.get('Trade Date', 'n/a')}")
            st.text(f"Settlement date: {r.get('Settlement Date', 'n/a')}")
    else:
        st.info("No term sheet loaded.")


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
