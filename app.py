"""TAM's Research & Reporting Agent - Institutional-Grade Chat Interface."""

import os
import sys
import re
import base64
import importlib
import streamlit as st
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from config import (
    ANTHROPIC_API_KEY, MODEL, TAMS_LOGO, ASSETS_DIR, OUTPUT_DIR,
    resolve_ticker
)
from data.market_data import (
    fetch_stock_data, fetch_price_history, fetch_financials,
    fetch_dividend_history, calculate_technical_indicators,
    format_market_data_for_prompt
)
from data.web_search import search_company_news, search_sector_news
from data.source_collector import SourceCollector
from data.report_store import save_report, list_reports, load_report, get_versions
from data.watchlist import (
    get_watchlists, get_default_watchlist, create_watchlist,
    add_ticker, remove_ticker, get_watchlist, get_all_watched_tickers,
)
from data.market_monitor import scan_watchlist, get_all_alerts
from data.alert_engine import (
    process_monitor_alerts, get_recent_alerts, get_unread_count, mark_all_read,
)
from data.report_comparator import (
    compare_metrics, compare_text_sections, build_comparison_summary,
    detect_rating_change, detect_outlook_change,
    SECTION_TITLES as CMP_SECTION_TITLES,
)
from data.chart_generator import generate_all_charts
from generators.docx_generator import generate_docx_report
from generators.pdf_generator import generate_pdf_report, convert_docx_to_pdf
from generators.pptx_generator import generate_pptx_report
from prompts.report_compiler import (
    EXECUTIVE_SUMMARY_PROMPT, DISCLAIMER_TEXT,
    get_analysis_type_from_request
)
from templates.report_structure import SECTION_CONFIG

import anthropic

# --- Page config ---
st.set_page_config(
    page_title="TAM's Research & Reporting Agent",
    page_icon="https://www.tamcapital.com.sa/favicon.ico",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
css_path = os.path.join(ASSETS_DIR, "style.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# API key from .env (no UI input needed)
api_key = ANTHROPIC_API_KEY


# --- Logo helper ---
def get_logo_base64():
    """Get TAMS logo as base64 for HTML embedding."""
    if os.path.exists(TAMS_LOGO):
        with open(TAMS_LOGO, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""


LOGO_B64 = get_logo_base64()


# --- Sidebar ---
with st.sidebar:
    # Logo
    if LOGO_B64:
        st.markdown(
            f"""
            <div style="text-align: center; padding: 20px 0 10px 0;">
                <img src="data:image/png;base64,{LOGO_B64}" width="180"
                     style="filter: brightness(0) invert(1);" />
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown(
        """
        <div style="text-align: center; padding: 0 0 16px 0;">
            <span style="color: #2EAD6D; font-size: 0.75rem; font-weight: 600;
                         letter-spacing: 0.15em; text-transform: uppercase;">
                Research & Reporting Agent
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")

    # --- Watchlist ---
    st.markdown(
        '<p style="font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; '
        'color: #7B8FA3 !important; margin-bottom: 8px;">Watchlist</p>',
        unsafe_allow_html=True
    )

    # Ensure default watchlist exists with starter tickers
    wl_list = get_watchlists()
    if not wl_list:
        try:
            default_wl = create_watchlist("My Watchlist", "Default watchlist")
            for t, n in [("2020", "SABIC AN"), ("2222", "Aramco"),
                         ("1120", "Al Rajhi"), ("7010", "STC")]:
                add_ticker(default_wl["id"], resolve_ticker(t), n)
        except Exception:
            pass
        wl_list = get_watchlists()

    if wl_list:
        active_wl = get_default_watchlist()
        if active_wl and active_wl.get("items"):
            # Quick-report buttons from watchlist items
            items = active_wl["items"]
            for row_start in range(0, len(items), 2):
                cols = st.columns(2)
                for i, col in enumerate(cols):
                    idx = row_start + i
                    if idx < len(items):
                        item = items[idx]
                        with col:
                            if st.button(item["name"], key=f"wl_{idx}",
                                         use_container_width=True):
                                st.session_state["quick_prompt"] = (
                                    f"Full report on {item['name']} ({item['ticker']})"
                                )

        # Add / remove ticker controls
        with st.expander("Manage Watchlist", expanded=False):
            add_col, rm_col = st.columns(2)
            with add_col:
                new_ticker = st.text_input("Add ticker", key="wl_add_input",
                                           placeholder="e.g. 2222",
                                           label_visibility="collapsed")
                if st.button("Add", key="wl_add_btn", use_container_width=True) and new_ticker:
                    try:
                        resolved = resolve_ticker(new_ticker.strip())
                        add_ticker(active_wl["id"], resolved, new_ticker.strip().upper())
                        st.rerun()
                    except ValueError as e:
                        st.warning(str(e))
            with rm_col:
                if active_wl and active_wl.get("items"):
                    rm_choice = st.selectbox(
                        "Remove", [i["ticker"] for i in active_wl["items"]],
                        key="wl_rm_select", label_visibility="collapsed"
                    )
                    if st.button("Remove", key="wl_rm_btn", use_container_width=True):
                        remove_ticker(active_wl["id"], rm_choice)
                        st.rerun()
    else:
        # Fallback static buttons if watchlist init failed
        col1, col2 = st.columns(2)
        with col1:
            if st.button("SABIC AN", key="q1", use_container_width=True):
                st.session_state["quick_prompt"] = "Full report on SABIC Agri-Nutrients (2020)"
        with col2:
            if st.button("Aramco", key="q2", use_container_width=True):
                st.session_state["quick_prompt"] = "Full report on Saudi Aramco (2222)"
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Al Rajhi", key="q3", use_container_width=True):
                st.session_state["quick_prompt"] = "Full report on Al Rajhi Bank (1120)"
        with col2:
            if st.button("STC", key="q4", use_container_width=True):
                st.session_state["quick_prompt"] = "Full report on STC (7010)"

    st.markdown("---")

    # --- Market Alerts ---
    watched = get_all_watched_tickers()
    if watched:
        raw_alerts = get_all_alerts(watched)
        if raw_alerts:
            process_monitor_alerts(raw_alerts)  # Apply cooldown, save to history

        unread = get_unread_count()
        recent = get_recent_alerts(limit=5)

        if recent:
            badge = f" ({unread})" if unread > 0 else ""
            st.markdown(
                f'<p style="font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; '
                f'color: #7B8FA3 !important; margin-bottom: 8px;">Alerts{badge}</p>',
                unsafe_allow_html=True
            )
            for alert in recent:
                sev_color = {"major": "#D32F2F", "moderate": "#FF9800"}.get(
                    alert.get("severity"), "#6CB9B6"
                )
                read_opacity = "0.5" if alert.get("is_read") else "1.0"
                st.markdown(
                    f'<div style="font-size:0.78rem;margin-bottom:5px;padding:4px 8px;'
                    f'border-left:3px solid {sev_color};background:rgba(0,0,0,0.15);'
                    f'border-radius:0 4px 4px 0;opacity:{read_opacity};">'
                    f'{alert["message"]}'
                    f'<br/><span style="font-size:0.65rem;color:#7B8FA3;">{alert.get("display_time", "")}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            if unread > 0:
                if st.button("Mark all read", key="mark_read_btn", use_container_width=True):
                    mark_all_read()
                    st.rerun()
            st.markdown("---")

    # Output format
    st.markdown(
        '<p style="font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; '
        'color: #7B8FA3 !important; margin-bottom: 8px;">Report Format</p>',
        unsafe_allow_html=True
    )
    output_format = st.multiselect(
        "Format",
        ["Word (DOCX)", "PDF", "PowerPoint (PPTX)"],
        default=["Word (DOCX)"],
        label_visibility="collapsed"
    )

    st.markdown("---")

    # Capabilities
    st.markdown(
        '<p style="font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; '
        'color: #7B8FA3 !important; margin-bottom: 8px;">Capabilities</p>',
        unsafe_allow_html=True
    )
    st.markdown(
        """
        <div style="font-size: 0.8rem; line-height: 1.8; color: #9EAFC0 !important;">
        Fundamental Analysis<br>
        Technical Analysis<br>
        Earnings Analysis<br>
        Dividend Analysis<br>
        Risk Assessment<br>
        Sector Rotation<br>
        News Impact<br>
        Geopolitical Risk
        </div>
        """,
        unsafe_allow_html=True
    )

    # --- Report History & Compare ---
    st.markdown("---")
    st.markdown(
        '<p style="font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; '
        'color: #7B8FA3 !important; margin-bottom: 8px;">Report History</p>',
        unsafe_allow_html=True
    )

    saved_reports = list_reports()
    if saved_reports:
        # Group by ticker for version browsing
        tickers_seen = {}
        for r in saved_reports:
            if r["ticker"] not in tickers_seen:
                tickers_seen[r["ticker"]] = r["stock_name"]

        if tickers_seen:
            selected_ticker = st.selectbox(
                "Ticker",
                list(tickers_seen.keys()),
                format_func=lambda t: f"{tickers_seen[t]} ({t})",
                key="ver_ticker",
                label_visibility="collapsed",
            )
            versions = get_versions(selected_ticker)
            if versions:
                for v in versions[:5]:
                    ver_label = f"v{v['version']}"
                    summary = v.get("change_summary", "")
                    summary_short = (summary[:60] + "...") if len(summary) > 60 else summary
                    st.markdown(
                        f'<div style="font-size:0.8rem;margin-bottom:6px;">'
                        f'<span style="color:#1A6DB6;font-weight:600;">{ver_label}</span> '
                        f'<span style="color:#9EAFC0;font-size:0.7rem;">{v["date_display"]}</span>'
                        f'{"<br/><span style=&quot;color:#7B8FA3;font-size:0.7rem;&quot;>" + summary_short + "</span>" if summary_short else ""}'
                        f'</div>',
                        unsafe_allow_html=True
                    )

        # Compare selector
        if len(saved_reports) >= 2:
            st.markdown(
                '<p style="font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; '
                'color: #7B8FA3 !important; margin-bottom: 4px; margin-top: 10px;">Compare</p>',
                unsafe_allow_html=True
            )
            report_labels = {
                r["id"]: f"{'v' + str(r['version']) + ' ' if r.get('version') else ''}"
                         f"{r['stock_name']} - {r['date_display']}"
                for r in saved_reports
            }
            report_ids = list(report_labels.keys())

            cmp_old = st.selectbox("Older", report_ids,
                                   format_func=lambda x: report_labels[x],
                                   key="cmp_old", index=min(1, len(report_ids) - 1))
            cmp_new = st.selectbox("Newer", report_ids,
                                   format_func=lambda x: report_labels[x],
                                   key="cmp_new", index=0)

            if st.button("Compare", key="cmp_btn", use_container_width=True):
                st.session_state["compare_request"] = (cmp_old, cmp_new)
    else:
        st.markdown(
            '<p style="font-size: 0.78rem; color: #9EAFC0;">Reports will appear here after generation.</p>',
            unsafe_allow_html=True
        )

    # Footer
    st.markdown(
        """
        <div style="position: fixed; bottom: 16px; left: 16px; right: 16px; max-width: 240px;">
            <hr style="border-color: rgba(46, 173, 109, 0.2); margin-bottom: 8px;" />
            <p style="font-size: 0.65rem; color: #5A6B7E !important; text-align: center; margin: 0;">
                TAM Capital | CMA Regulated<br>
                Confidential - Internal Use Only
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )


# --- Initialize session state ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "report_files" not in st.session_state:
    st.session_state.report_files = {}


# --- Helper functions ---
def extract_ticker_from_message(message: str) -> tuple:
    """Extract stock ticker and company name from user message."""
    match = re.search(r'\((\w+(?:\.\w+)?)\)', message)
    if match:
        raw_ticker = match.group(1)
        ticker = resolve_ticker(raw_ticker)
        name_part = message[:match.start()].strip()
        for prefix in ["analyze", "full report on", "report on", "analysis of",
                       "technical analysis of", "dividend analysis of",
                       "earnings preview for", "earnings analysis of"]:
            name_part = re.sub(f"^{prefix}\\s*", "", name_part, flags=re.IGNORECASE).strip()
        return ticker, name_part if name_part else raw_ticker

    match = re.search(r'\b(\d{4})\b', message)
    if match:
        raw = match.group(1)
        return resolve_ticker(raw), raw

    match = re.search(r'\b([A-Z]{1,5})\b', message)
    if match:
        raw = match.group(1)
        if raw not in {"THE", "FOR", "AND", "BUT", "NOT", "ALL", "TAM", "EPS", "CEO",
                       "ETF", "IPO", "ROE", "ROA", "FCF", "YOY", "QOQ", "FULL"}:
            return resolve_ticker(raw), raw

    return None, None


def call_claude(prompt: str) -> str:
    """Call Claude API."""
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


def generate_section(section_type: str, market_data_str: str, news_str: str) -> str:
    """Generate a single analysis section."""
    config = SECTION_CONFIG.get(section_type)
    if not config:
        return ""
    module = importlib.import_module(config["prompt_module"])
    prompt_template = getattr(module, config["prompt_var"])
    prompt = prompt_template.format(market_data=market_data_str, news_data=news_str)
    return call_claude(prompt)


def run_full_analysis(ticker: str, company_name: str, user_message: str, formats: list) -> dict:
    """Run the complete analysis pipeline."""
    results = {"sections": {}, "charts": {}, "files": {}, "sources": None}

    # Initialize source collector
    collector = SourceCollector()

    # Step 1: Fetch data
    with st.status("Collecting market intelligence...", expanded=True) as status:
        st.write("Fetching live market data...")
        stock_data = fetch_stock_data(ticker, collector=collector)
        if stock_data.get("name") and stock_data["name"] != ticker:
            company_name = stock_data["name"]

        st.write("Loading price history...")
        hist = fetch_price_history(ticker, collector=collector)

        st.write("Computing technical indicators...")
        technicals = calculate_technical_indicators(hist) if not hist.empty else {}

        st.write("Scanning recent news & events...")
        news = search_company_news(company_name, ticker, collector=collector)

        st.write("Pulling financial statements...")
        financials = fetch_financials(ticker, collector=collector)

        st.write("Retrieving dividend history...")
        dividends = fetch_dividend_history(ticker, collector=collector)

        market_data_str = format_market_data_for_prompt(stock_data, technicals, hist)
        status.update(label=f"Market data collected ({len(collector)} sources tracked)", state="complete")

    # Step 2: Generate charts
    with st.status("Building visualizations...", expanded=False) as status:
        chart_dir = os.path.join(OUTPUT_DIR, "charts")
        charts = generate_all_charts(stock_data, technicals, hist, financials, dividends, chart_dir)
        results["charts"] = charts
        status.update(label=f"{len(charts)} charts generated", state="complete")

    # Step 3: Determine which sections to generate
    section_types = get_analysis_type_from_request(user_message)

    # Step 4: Generate each section
    with st.status("Running multi-framework analysis...", expanded=True) as status:
        total = len(section_types)
        for i, section_type in enumerate(section_types):
            config = SECTION_CONFIG.get(section_type)
            if not config:
                continue
            st.write(f"[{i+1}/{total}] {config['title']}")
            try:
                content = generate_section(section_type, market_data_str, news)
                results["sections"][config["section_key"]] = content
            except Exception as e:
                st.warning(f"Error: {config['title']} - {str(e)}")
                continue

        # Executive summary
        if results["sections"]:
            st.write(f"[{total}/{total}] Compiling Executive Summary...")
            all_sections_text = "\n\n---\n\n".join(
                f"[{k}]\n{v}" for k, v in results["sections"].items()
            )
            exec_prompt = EXECUTIVE_SUMMARY_PROMPT.format(
                market_data=market_data_str,
                all_sections=all_sections_text[:8000]
            )
            try:
                exec_summary = call_claude(exec_prompt)
                if "KEY TAKEAWAYS" in exec_summary.upper():
                    parts = re.split(r'(?i)key\s*takeaways', exec_summary, maxsplit=1)
                    results["sections"]["executive_summary"] = parts[0].strip()
                    results["sections"]["key_takeaways"] = "Key Takeaways" + parts[1] if len(parts) > 1 else ""
                else:
                    results["sections"]["executive_summary"] = exec_summary
            except Exception as e:
                st.warning(f"Executive summary error: {str(e)}")

        status.update(label="Analysis complete", state="complete")

    # Step 5: Generate documents
    with st.status("Preparing deliverables...", expanded=False) as status:
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        results["sources"] = collector

        if "Word (DOCX)" in formats:
            try:
                docx_path = generate_docx_report(
                    company_name, ticker, results["sections"],
                    charts=results["charts"], output_dir=OUTPUT_DIR,
                    sources=collector
                )
                results["files"]["docx"] = docx_path
            except Exception as e:
                st.warning(f"DOCX: {str(e)}")

        if "PDF" in formats:
            try:
                pdf_path = generate_pdf_report(
                    company_name, ticker, results["sections"],
                    charts=results["charts"], output_dir=OUTPUT_DIR,
                    sources=collector
                )
                results["files"]["pdf"] = pdf_path
            except Exception:
                # Fallback: convert DOCX to PDF
                docx_for_pdf = results["files"].get("docx")
                if not docx_for_pdf:
                    try:
                        docx_for_pdf = generate_docx_report(
                            company_name, ticker, results["sections"],
                            charts=results["charts"], output_dir=OUTPUT_DIR,
                            sources=collector
                        )
                    except Exception:
                        pass
                if docx_for_pdf:
                    try:
                        pdf_path = convert_docx_to_pdf(docx_for_pdf)
                        results["files"]["pdf"] = pdf_path
                    except Exception as e:
                        st.warning(f"PDF: {str(e)}")

        if "PowerPoint (PPTX)" in formats:
            try:
                pptx_path = generate_pptx_report(
                    company_name, ticker, results["sections"],
                    charts=results["charts"], output_dir=OUTPUT_DIR,
                    sources=collector
                )
                results["files"]["pptx"] = pptx_path
            except Exception as e:
                st.warning(f"PPTX: {str(e)}")

        # Save report to history for comparison
        try:
            save_report(company_name, ticker, results["sections"],
                        files=results.get("files", {}))
        except Exception:
            pass  # Non-critical; don't block the user

        status.update(label="Reports ready for download", state="complete")

    return results


# --- Main interface ---

# Show welcome screen when no messages
if not st.session_state.messages:
    # Header with logo
    if LOGO_B64:
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 4px;">
                <img src="data:image/png;base64,{LOGO_B64}" height="48" />
                <div>
                    <h1 style="margin: 0; padding: 0; font-size: 1.8rem;">Research & Reporting Agent</h1>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown("# TAM's Research & Reporting Agent")

    st.markdown(
        '<p style="color: #64748B; font-size: 1rem; margin-top: -8px;">'
        'Institutional-grade investment research. Powered by AI.</p>',
        unsafe_allow_html=True
    )

    st.markdown("")

    # Welcome cards
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, #1B2A4A 0%, #243656 100%);
                        border-radius: 14px; padding: 24px; height: 160px;">
                <p style="color: #2EAD6D; font-size: 0.7rem; text-transform: uppercase;
                          letter-spacing: 0.1em; margin-bottom: 8px;">Equity Analysis</p>
                <p style="color: white; font-size: 0.95rem; font-weight: 600; margin-bottom: 8px;">
                    Full Research Reports</p>
                <p style="color: #9EAFC0; font-size: 0.8rem; line-height: 1.4;">
                    Goldman Sachs-style fundamentals, JPMorgan earnings, Morgan Stanley technicals</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, #1B2A4A 0%, #243656 100%);
                        border-radius: 14px; padding: 24px; height: 160px;">
                <p style="color: #2EAD6D; font-size: 0.7rem; text-transform: uppercase;
                          letter-spacing: 0.1em; margin-bottom: 8px;">Risk Intelligence</p>
                <p style="color: white; font-size: 0.95rem; font-weight: 600; margin-bottom: 8px;">
                    News & Geopolitical Impact</p>
                <p style="color: #9EAFC0; font-size: 0.8rem; line-height: 1.4;">
                    Real-time news assessment, war impact scenarios, stress testing</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, #1B2A4A 0%, #243656 100%);
                        border-radius: 14px; padding: 24px; height: 160px;">
                <p style="color: #2EAD6D; font-size: 0.7rem; text-transform: uppercase;
                          letter-spacing: 0.1em; margin-bottom: 8px;">Deliverables</p>
                <p style="color: white; font-size: 0.95rem; font-weight: 600; margin-bottom: 8px;">
                    TAMS-Branded Reports</p>
                <p style="color: #9EAFC0; font-size: 0.8rem; line-height: 1.4;">
                    Word, PDF & PowerPoint on TAM Capital letterhead with charts</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("")
    st.markdown(
        '<p style="color: #94A3B8; font-size: 0.85rem; text-align: center;">'
        'Type a stock name or ticker below to begin analysis</p>',
        unsafe_allow_html=True
    )

else:
    # Compact header when in conversation
    if LOGO_B64:
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px; padding-bottom: 12px;
                        border-bottom: 1px solid #E2E8F0;">
                <img src="data:image/png;base64,{LOGO_B64}" height="32" />
                <span style="color: #1B2A4A; font-size: 1rem; font-weight: 600;">
                    Research & Reporting Agent</span>
            </div>
            """,
            unsafe_allow_html=True
        )

# Display chat history
for msg_idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        if msg["role"] == "assistant" and "files" in msg:
            cols = st.columns(len(msg["files"]))
            for i, (fmt, path) in enumerate(msg["files"].items()):
                if os.path.exists(path):
                    with cols[i]:
                        with open(path, "rb") as f:
                            st.download_button(
                                label=f"Download {fmt.upper()}",
                                data=f.read(),
                                file_name=os.path.basename(path),
                                mime="application/octet-stream",
                                key=f"hist_dl_{fmt}_{msg_idx}_{i}"
                            )

# --- Comparison display ---
compare_request = st.session_state.pop("compare_request", None)
if compare_request:
    old_id, new_id = compare_request
    old_report = load_report(old_id)
    new_report = load_report(new_id)

    if old_report and new_report:
        st.markdown("---")
        st.markdown(
            f"### Report Comparison\n"
            f"**{old_report['stock_name']}** ({old_report['date_display']})  vs  "
            f"**{new_report['stock_name']}** ({new_report['date_display']})"
        )

        metric_changes = compare_metrics(old_report["sections"], new_report["sections"])
        text_diffs = compare_text_sections(old_report["sections"], new_report["sections"])
        summary = build_comparison_summary(metric_changes, text_diffs)

        # Rating & outlook change alerts
        rating_change = detect_rating_change(old_report["sections"], new_report["sections"])
        outlook_change = detect_outlook_change(old_report["sections"], new_report["sections"])
        if rating_change:
            direction = "upgraded" if rating_change["is_upgrade"] else "downgraded"
            st.warning(
                f"Rating {direction}: **{rating_change['old_rating'].title()}** "
                f"\u2192 **{rating_change['new_rating'].title()}**"
            )
        if outlook_change:
            st.info(
                f"Outlook changed: **{outlook_change['old_outlook'].title()}** "
                f"\u2192 **{outlook_change['new_outlook'].title()}**"
            )

        # Summary dashboard
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Improved", summary["metrics_improved"],
                       delta=f"{summary['metrics_improved']}" if summary["metrics_improved"] else None,
                       delta_color="normal")
        with col2:
            st.metric("Declined", summary["metrics_deteriorated"],
                       delta=f"-{summary['metrics_deteriorated']}" if summary["metrics_deteriorated"] else None,
                       delta_color="inverse")
        with col3:
            st.metric("Sections Changed", summary["sections_changed"])
        with col4:
            largest = summary.get("largest_change")
            if largest and largest.get("change_pct") is not None:
                st.metric("Largest Move",
                           largest["metric"],
                           delta=f"{largest['change_pct']:+.1f}%")
            else:
                st.metric("Largest Move", "N/A")
        with col5:
            score = summary.get("change_score", 0)
            score_label = "Low" if score < 25 else ("Moderate" if score < 50 else "High")
            st.metric("Change Score", f"{score}/100", delta=score_label)

        # Metric details table
        if metric_changes:
            st.markdown("#### Financial Metrics")
            rows_html = ""
            for m in metric_changes:
                arrow = ""
                color = "#4A4A4A"
                if m["direction"] == "up":
                    arrow = "&#9650;"
                    color = "#2EAD6D"
                elif m["direction"] == "down":
                    arrow = "&#9660;"
                    color = "#D32F2F"

                old_str = f"{m['old']:.2f}" if m["old"] is not None else "N/A"
                new_str = f"{m['new']:.2f}" if m["new"] is not None else "N/A"
                pct_str = f"{m['change_pct']:+.1f}%" if m["change_pct"] is not None else ""

                sev = m.get("severity", "")
                sev_colors = {"minor": "#6CB9B6", "moderate": "#FF9800", "major": "#D32F2F"}
                sev_badge = (
                    f"<span style='background:{sev_colors.get(sev, '#B1B3B6')};color:white;"
                    f"padding:1px 6px;border-radius:3px;font-size:0.7em;'>{sev}</span>"
                ) if sev and sev != "unknown" else ""

                rows_html += (
                    f"<tr>"
                    f"<td style='padding:6px 12px;font-weight:600;color:#222F62;'>{m['metric']}</td>"
                    f"<td style='padding:6px 12px;text-align:right;'>{old_str}</td>"
                    f"<td style='padding:6px 12px;text-align:right;'>{new_str}</td>"
                    f"<td style='padding:6px 12px;text-align:right;color:{color};'>"
                    f"<span style='font-size:0.7em;'>{arrow}</span> {pct_str}</td>"
                    f"<td style='padding:6px 12px;text-align:center;'>{sev_badge}</td>"
                    f"</tr>"
                )

            st.markdown(
                f"""<table style="width:100%;border-collapse:collapse;font-size:0.9rem;">
                <thead><tr style="background:#222F62;color:white;">
                <th style="padding:8px 12px;text-align:left;">Metric</th>
                <th style="padding:8px 12px;text-align:right;">Previous</th>
                <th style="padding:8px 12px;text-align:right;">Current</th>
                <th style="padding:8px 12px;text-align:right;">Change</th>
                <th style="padding:8px 12px;text-align:center;">Severity</th>
                </tr></thead>
                <tbody>{rows_html}</tbody></table>""",
                unsafe_allow_html=True
            )

        # Text diffs
        if text_diffs:
            st.markdown("#### Section Changes")
            for section_key, diff_lines in text_diffs.items():
                title = CMP_SECTION_TITLES.get(section_key, section_key.replace("_", " ").title())
                with st.expander(f"{title} ({sum(1 for t,_ in diff_lines if t=='added')} added, "
                                 f"{sum(1 for t,_ in diff_lines if t=='removed')} removed)"):
                    diff_html = ""
                    for typ, text in diff_lines[:50]:
                        text_esc = text.replace("<", "&lt;").replace(">", "&gt;")
                        if typ == "added":
                            diff_html += f'<div style="background:#E6F4EA;padding:2px 8px;margin:1px 0;border-left:3px solid #2EAD6D;font-size:0.85rem;">+ {text_esc}</div>'
                        elif typ == "removed":
                            diff_html += f'<div style="background:#FCE8E6;padding:2px 8px;margin:1px 0;border-left:3px solid #D32F2F;font-size:0.85rem;">- {text_esc}</div>'
                        else:
                            diff_html += f'<div style="padding:2px 8px;margin:1px 0;font-size:0.85rem;color:#666;">&nbsp; {text_esc}</div>'
                    st.markdown(diff_html, unsafe_allow_html=True)

        st.markdown("---")

# Handle quick prompts from sidebar
quick_prompt = st.session_state.pop("quick_prompt", None)

# Chat input
user_input = st.chat_input("Enter stock name or ticker (e.g. SABIC Agri-Nutrients 2020, Aramco 2222, AAPL)")

# Use quick prompt if clicked, otherwise use chat input
prompt = quick_prompt or user_input

if prompt:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Check API key
    if not api_key or api_key == "your_api_key_here":
        with st.chat_message("assistant"):
            st.error("API key not configured. Please update the .env file with your Anthropic API key.")
            st.session_state.messages.append({
                "role": "assistant",
                "content": "API key not configured. Please update the .env file."
            })
    else:
        ticker, company_name = extract_ticker_from_message(prompt)

        if not ticker:
            # General question
            with st.chat_message("assistant"):
                with st.spinner(""):
                    try:
                        response = call_claude(
                            f"You are a senior financial analyst at TAM Capital, a Saudi Arabia-based "
                            f"asset management firm regulated by the CMA. Answer this question "
                            f"professionally and concisely:\n\n{prompt}"
                        )
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
        else:
            # Run analysis
            with st.chat_message("assistant"):
                st.markdown(f"Initiating analysis for **{company_name or ticker}** `{ticker}`")

                try:
                    results = run_full_analysis(
                        ticker, company_name or ticker, prompt, output_format
                    )

                    # Display summary
                    exec_summary = results["sections"].get("executive_summary", "")
                    if exec_summary:
                        st.markdown("---")
                        st.markdown("#### Executive Summary")
                        st.markdown(exec_summary[:2000])

                    takeaways = results["sections"].get("key_takeaways", "")
                    if takeaways:
                        st.markdown("---")
                        st.markdown("#### Key Takeaways")
                        st.markdown(takeaways[:1500])

                    # Charts
                    if results["charts"]:
                        st.markdown("---")
                        chart_cols = st.columns(min(len(results["charts"]), 2))
                        for i, (name, path) in enumerate(results["charts"].items()):
                            if os.path.exists(path):
                                with chart_cols[i % 2]:
                                    st.image(path, caption=name.replace("_", " ").title(),
                                             use_container_width=True)

                    # Download buttons
                    if results["files"]:
                        st.markdown("---")
                        st.markdown("#### Download Reports")
                        cols = st.columns(len(results["files"]))
                        for i, (fmt, path) in enumerate(results["files"].items()):
                            if os.path.exists(path):
                                with cols[i]:
                                    with open(path, "rb") as f:
                                        ext_labels = {"docx": "Word Document", "pdf": "PDF Report", "pptx": "Presentation"}
                                        st.download_button(
                                            label=f"{ext_labels.get(fmt, fmt.upper())}",
                                            data=f.read(),
                                            file_name=os.path.basename(path),
                                            mime="application/octet-stream",
                                            key=f"dl_{fmt}_{datetime.now().timestamp()}"
                                        )

                    # Show sources
                    if results.get("sources") and len(results["sources"]) > 0:
                        st.markdown("---")
                        with st.expander(f"Sources & References ({len(results['sources'])} sources)", expanded=False):
                            st.markdown(results["sources"].format_for_display())

                    # Save to session
                    summary_text = f"Analysis complete for **{company_name}** ({ticker}).\n\n"
                    if exec_summary:
                        summary_text += exec_summary[:500]

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": summary_text,
                        "files": results.get("files", {})
                    })

                except Exception as e:
                    error_msg = f"Error during analysis: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
