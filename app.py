"""TAM's Research & Reporting Agent — Finance Dashboard UI."""

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
    ANTHROPIC_API_KEY, MODEL, FALLBACK_MODEL, TAMS_LOGO, ASSETS_DIR, OUTPUT_DIR,
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
from data.portfolio import (
    get_positions, add_position, remove_position, calculate_portfolio_metrics
)
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
from generators.xlsx_generator import generate_xlsx_report
from prompts.report_compiler import (
    EXECUTIVE_SUMMARY_PROMPT, DISCLAIMER_TEXT,
    get_analysis_type_from_request
)
from templates.report_structure import SECTION_CONFIG

import anthropic
import threading

# --- Plotly charts (optional — graceful fallback to matplotlib) ---
try:
    from data.interactive_charts import (
        generate_candlestick_chart, generate_rsi_chart, generate_macd_chart,
        generate_comparison_chart,
        calculate_technical_indicators as calc_plotly_technicals,
    )
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# --- DCF model (optional) ---
try:
    from data.dcf_model import DCFModel, get_default_assumptions, format_dcf_for_display
    DCF_AVAILABLE = True
except ImportError:
    DCF_AVAILABLE = False

# --- Risk metrics (optional) ---
try:
    from data.risk_metrics import calculate_portfolio_risk, generate_risk_charts
    RISK_AVAILABLE = True
except ImportError:
    RISK_AVAILABLE = False

# --- Peer benchmarking (optional) ---
try:
    from data.peer_benchmark import (
        get_sector_for_ticker, get_peers, fetch_peer_metrics,
        calculate_peer_rankings, generate_peer_heatmap, generate_peer_comparison_table,
    )
    PEERS_AVAILABLE = True
except ImportError:
    PEERS_AVAILABLE = False

# --- Financial statement viewer (optional) ---
try:
    from data.financial_viewer import generate_financial_overview
    FINANCIALS_VIEWER_AVAILABLE = True
except ImportError:
    FINANCIALS_VIEWER_AVAILABLE = False

# --- Supabase client (optional) ---
try:
    from data.supabase_client import SUPABASE_AVAILABLE
except ImportError:
    SUPABASE_AVAILABLE = False

# --- Auth & RBAC (optional) ---
try:
    from auth.login import render_login_page, is_authenticated, get_current_user, logout
    from auth.rbac import has_permission, can_access_page, is_admin, is_super_admin
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False

# --- Admin panel (optional) ---
try:
    from views.admin import render_admin
    ADMIN_AVAILABLE = True
except ImportError:
    ADMIN_AVAILABLE = False

# --- Alert rules UI (optional) ---
try:
    from data.alert_rules_ui import render_alert_rules_panel, check_alert_rules
    ALERT_RULES_AVAILABLE = True
except ImportError:
    ALERT_RULES_AVAILABLE = False

# --- Morning brief (optional) ---
try:
    from prompts.morning_brief import generate_morning_brief, format_brief_for_display
    MORNING_BRIEF_AVAILABLE = True
except ImportError:
    MORNING_BRIEF_AVAILABLE = False

# --- Activity tracking (optional) ---
try:
    from data.activity_tracker import track_activity, get_activity_summary
    ACTIVITY_AVAILABLE = True
except ImportError:
    ACTIVITY_AVAILABLE = False

# --- Audit logging (optional) ---
try:
    from data.audit_logger import log_audit
    AUDIT_AVAILABLE = True
except ImportError:
    AUDIT_AVAILABLE = False

# --- Token usage tracking (optional) ---
try:
    from data.token_tracker import track_tokens
    TOKEN_TRACKER_AVAILABLE = True
except ImportError:
    TOKEN_TRACKER_AVAILABLE = False

# --- Sentiment tracking (optional) ---
try:
    from data.sentiment_tracker import extract_sentiment, store_sentiment, generate_sentiment_chart
    SENTIMENT_AVAILABLE = True
except ImportError:
    SENTIMENT_AVAILABLE = False

# --- Recommendations (optional) ---
try:
    from data.recommendation_engine import get_smart_suggestions, generate_suggestions_html
    RECOMMENDATIONS_AVAILABLE = True
except ImportError:
    RECOMMENDATIONS_AVAILABLE = False

# --- Predictive signals (optional) ---
try:
    from data.predictive_signals import get_all_signals, generate_signal_badges_html
    SIGNALS_AVAILABLE = True
except ImportError:
    SIGNALS_AVAILABLE = False

# --- Research notes (optional) ---
try:
    from data.research_notes import render_notes_panel
    NOTES_AVAILABLE = True
except ImportError:
    NOTES_AVAILABLE = False

# --- Scheduled reports (optional) ---
try:
    from data.scheduled_reports import render_schedule_panel
    SCHEDULES_AVAILABLE = True
except ImportError:
    SCHEDULES_AVAILABLE = False

# --- Landing page (optional) ---
try:
    from views.landing import render_landing_page
    LANDING_AVAILABLE = True
except ImportError:
    LANDING_AVAILABLE = False

# --- Page config ---
st.set_page_config(
    page_title="TAM Capital — Research Terminal",
    page_icon="https://www.tamcapital.com.sa/favicon.ico",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
css_path = os.path.join(ASSETS_DIR, "style.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# API key: try Streamlit secrets first (cloud), then .env (local)
try:
    api_key = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    api_key = ANTHROPIC_API_KEY


# --- Logo helper ---
def get_logo_base64():
    """Get TAMS logo as base64 for HTML embedding."""
    if os.path.exists(TAMS_LOGO):
        with open(TAMS_LOGO, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""


LOGO_B64 = get_logo_base64()

# ==========================================================
# DESIGN SYSTEM — Light Theme (must match CSS vars)
# ==========================================================

# Backgrounds
C_BG = "#FFFFFF"
C_SURFACE = "#F8FAFC"
C_CARD = "#FFFFFF"
C_CARD_HOVER = "#F8FAFC"
C_INPUT = "#F1F5F9"

# TAM Brand Palette
C_DEEP = "#222F62"
C_ACCENT = "#1A6DB6"
C_TURQUOISE = "#6CB9B6"
C_ACCENT2 = "#6CB9B6"
C_CYAN = "#6CB9B6"
C_GREEN = "#16A34A"
C_RED = "#DC2626"
C_ORANGE = "#D97706"

# Borders
C_BORDER = "#E2E8F0"
C_BORDER_HOVER = "#CBD5E1"

# Text — dark on light
C_TEXT = "#0F172A"
C_TEXT2 = "#475569"
C_MUTED = "#94A3B8"
C_DIM = "#CBD5E1"

# Gradients
ACCENT_GRADIENT = "linear-gradient(135deg, #1A6DB6 0%, #6CB9B6 100%)"
ACCENT_TEXT_GRADIENT = "linear-gradient(135deg, #1A6DB6 0%, #6CB9B6 100%)"


def _card_style(padding="20px", height=None, extra=""):
    """Reusable white card inline style."""
    h = f"height:{height};" if height else ""
    return (
        f"background:{C_CARD};border:1px solid {C_BORDER};border-radius:12px;"
        f"padding:{padding};{h}box-shadow:0 1px 2px rgba(0,0,0,0.04);"
        f"transition:all 0.2s ease;position:relative;overflow:hidden;{extra}"
    )

# Keep old name as alias for backward compat
_glass_card_style = _card_style


def _accent_label(text):
    """Small accent label text."""
    return (
        f'<p style="color:{C_MUTED};font-size:0.6rem;text-transform:uppercase;'
        f'letter-spacing:0.12em;margin-bottom:6px;font-weight:700;">{text}</p>'
    )


def _section_label(text):
    """Sidebar section label."""
    return (
        f'<p style="font-size:0.6rem;text-transform:uppercase;letter-spacing:0.14em;'
        f'color:{C_DIM} !important;margin-bottom:8px;font-weight:600;">{text}</p>'
    )


# ==========================================================
# SESSION STATE INITIALIZATION
# ==========================================================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "report_files" not in st.session_state:
    st.session_state.report_files = {}
if "current_page" not in st.session_state:
    st.session_state.current_page = "research"
if "cancel_analysis" not in st.session_state:
    st.session_state.cancel_analysis = False
if "analysis_running" not in st.session_state:
    st.session_state.analysis_running = False
if "analysis_preferences" not in st.session_state:
    st.session_state.analysis_preferences = {
        "horizon": "Medium-term (6-12 months)",
        "focus": ["Full Analysis"],
        "language": "English",
        "include_dcf": False,
    }
if "show_preferences" not in st.session_state:
    st.session_state.show_preferences = False
if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None
if "show_landing" not in st.session_state:
    st.session_state.show_landing = True

# Check if user clicked "enter" from the landing page CTA (via URL query param)
if st.query_params.get("enter") == "true":
    st.session_state.show_landing = False
    st.query_params.clear()


# ==========================================================
# NAVIGATION PAGES
# ==========================================================
NAV_PAGES = [
    ("dashboard", "Dashboard",    "grid_view"),
    ("research",  "Research",     "search"),
    ("portfolio", "Portfolio",    "account_balance_wallet"),
    ("sectors",   "Sectors",      "domain"),
    ("comparison","Compare",      "compare_arrows"),
    ("watchlist", "Watchlist",    "visibility"),
    ("alerts",    "Alerts",       "notifications"),
    ("admin",     "Admin",        "admin_panel_settings"),
]

# Unicode icons (Material Symbols fallback)
NAV_ICONS = {
    "dashboard": "\u25A6",
    "research": "\u2315",
    "portfolio": "\u25C8",
    "sectors": "\u25A3",
    "comparison": "\u21C4",
    "watchlist": "\u25C9",
    "alerts": "\u26A0",
    "admin": "\u2699",
}


# ==========================================================
# SIDEBAR — Navigation Panel
# ==========================================================

# Determine visibility state
_show_landing = LANDING_AVAILABLE and st.session_state.get("show_landing", True)
# Auth bypassed for now — show full sidebar whenever not on landing page
_is_authed = True  # AUTH_AVAILABLE and is_authenticated()
_show_full_sidebar = not _show_landing  # and _is_authed

# Hide sidebar completely on landing page
if _show_landing:
    st.markdown("""<style>section[data-testid="stSidebar"]{display:none!important;}</style>""", unsafe_allow_html=True)
elif not _is_authed:
    # Login page: minimal sidebar with logo only
    with st.sidebar:
        if LOGO_B64:
            st.markdown(
                f'<div style="text-align:center;padding:30px 0 10px 0;">'
                f'<img src="data:image/png;base64,{LOGO_B64}" width="160"'
                f' style="opacity:0.85;" />'
                f'</div>',
                unsafe_allow_html=True
            )
        st.markdown(
            f'<div style="text-align:center;padding:0 0 20px 0;">'
            f'<span style="color:{C_TURQUOISE};font-size:0.65rem;font-weight:700;'
            f'letter-spacing:0.18em;text-transform:uppercase;">Research Terminal</span>'
            f'</div>',
            unsafe_allow_html=True
        )

# Full sidebar only when authenticated
if _show_full_sidebar:
  with st.sidebar:
    # Logo + Brand
    if LOGO_B64:
        st.markdown(
            f'<div style="text-align:center;padding:16px 0 4px 0;">'
            f'<img src="data:image/png;base64,{LOGO_B64}" width="140"'
            f' style="opacity:0.9;" />'
            f'</div>',
            unsafe_allow_html=True
        )
    st.markdown(
        f'<div style="text-align:center;padding:0 0 10px 0;">'
        f'<span style="font-size:0.6rem;font-weight:600;color:{C_MUTED};'
        f'letter-spacing:0.14em;text-transform:uppercase;">Research Terminal</span>'
        f'</div>',
        unsafe_allow_html=True
    )

    st.markdown("---")

    # --- RESEARCH section ---
    st.markdown(_section_label("Research"), unsafe_allow_html=True)
    _nav_research = [("research", "Research", "\u2315"), ("comparison", "Compare", "\u21C4")]
    for page_key, page_label, icon in _nav_research:
        is_active = st.session_state.current_page == page_key
        btn_type = "primary" if is_active else "secondary"
        if st.button(f"{icon}  {page_label}", key=f"nav_{page_key}",
                      use_container_width=True, type=btn_type):
            st.session_state.current_page = page_key
            st.rerun()

    # --- MARKETS section ---
    st.markdown(_section_label("Markets"), unsafe_allow_html=True)
    _nav_markets = [("dashboard", "Overview", "\u25A6"), ("sectors", "Sectors", "\u25A3")]
    for page_key, page_label, icon in _nav_markets:
        is_active = st.session_state.current_page == page_key
        btn_type = "primary" if is_active else "secondary"
        if st.button(f"{icon}  {page_label}", key=f"nav_{page_key}",
                      use_container_width=True, type=btn_type):
            st.session_state.current_page = page_key
            st.rerun()

    # --- PORTFOLIO section ---
    st.markdown(_section_label("Portfolio"), unsafe_allow_html=True)
    _nav_portfolio = [("portfolio", "Positions", "\u25C8"), ("watchlist", "Watchlist", "\u25C9"),
                      ("alerts", "Alerts", "\u26A0")]
    for page_key, page_label, icon in _nav_portfolio:
        is_active = st.session_state.current_page == page_key
        btn_type = "primary" if is_active else "secondary"
        if st.button(f"{icon}  {page_label}", key=f"nav_{page_key}",
                      use_container_width=True, type=btn_type):
            st.session_state.current_page = page_key
            st.rerun()

    # --- ADMIN (if available) ---
    if AUTH_AVAILABLE and is_admin():
        st.markdown(_section_label("Admin"), unsafe_allow_html=True)
        is_active = st.session_state.current_page == "admin"
        btn_type = "primary" if is_active else "secondary"
        if st.button("\u2699  Admin Panel", key="nav_admin",
                      use_container_width=True, type=btn_type):
            st.session_state.current_page = "admin"
            st.rerun()

    st.markdown("---")

    # --- Mini Portfolio Widget ---
    positions = get_positions()
    if positions:
        st.markdown(_section_label("Portfolio"), unsafe_allow_html=True)
        live_prices = {}
        for pos in positions:
            try:
                sd = fetch_stock_data(pos["ticker"])
                price = sd.get("price", sd.get("regularMarketPrice", pos["cost_basis"]))
                live_prices[pos["ticker"]] = price
            except Exception:
                live_prices[pos["ticker"]] = pos["cost_basis"]

        metrics = calculate_portfolio_metrics(positions, live_prices)
        pnl_color = C_GREEN if metrics["total_pnl"] >= 0 else C_RED
        pnl_arrow = "+" if metrics["total_pnl"] >= 0 else ""
        pulse_cls = "data-pulse-green" if metrics["total_pnl"] >= 0 else "data-pulse-red"

        st.markdown(
            f'<div style="{_glass_card_style("12px")}">'
            f'<div style="font-size:0.65rem;color:{C_MUTED};margin-bottom:3px;text-transform:uppercase;'
            f'letter-spacing:0.1em;font-weight:600;">Total Value</div>'
            f'<div style="font-size:1.05rem;font-weight:700;color:{C_TEXT};">'
            f'SAR {metrics["total_value"]:,.0f}</div>'
            f'<div class="{pulse_cls}" style="font-size:0.78rem;color:{pnl_color};margin-top:2px;font-weight:600;">'
            f'{pnl_arrow}{metrics["total_pnl"]:,.0f} ({pnl_arrow}{metrics["total_pnl_pct"]:.1f}%)</div>'
            f'</div>',
            unsafe_allow_html=True
        )

        for p in metrics["positions"][:4]:
            p_color = C_GREEN if p["pnl"] >= 0 else C_RED
            p_arrow = "+" if p["pnl"] >= 0 else ""
            p_pulse = "data-pulse-green" if p["pnl"] >= 0 else "data-pulse-red"
            st.markdown(
                f'<div style="font-size:0.78rem;padding:3px 0;'
                f'border-bottom:1px solid {C_BORDER};">'
                f'<span style="color:{C_TEXT};font-weight:500;">{p["name"][:14]}</span> '
                f'<span class="{p_pulse}" style="color:{p_color};float:right;font-weight:600;">{p_arrow}{p["pnl_pct"]:.1f}%</span>'
                f'</div>',
                unsafe_allow_html=True
            )
        st.markdown("---")

    # --- Alerts ---
    watched = get_all_watched_tickers()
    if watched:
        import time as _time
        _alert_cache = st.session_state.get("_alert_cache", {})
        _cache_age = _time.time() - _alert_cache.get("ts", 0)
        if _cache_age > 900:
            raw_alerts = get_all_alerts(watched)
            if raw_alerts:
                process_monitor_alerts(raw_alerts)
            st.session_state["_alert_cache"] = {"ts": _time.time()}

        unread = get_unread_count()
        recent = get_recent_alerts(limit=4)

        if recent:
            badge = f" ({unread})" if unread > 0 else ""
            st.markdown(_section_label(f"Alerts{badge}"), unsafe_allow_html=True)
            for alert in recent:
                sev_color = {"major": C_RED, "moderate": C_ORANGE}.get(
                    alert.get("severity"), C_CYAN
                )
                read_opacity = "0.4" if alert.get("is_read") else "1.0"
                st.markdown(
                    f'<div style="font-size:0.75rem;margin-bottom:4px;padding:6px 10px;'
                    f'border-left:2px solid {sev_color};background:{C_CARD};'
                    f'border-radius:0 8px 8px 0;opacity:{read_opacity};">'
                    f'{alert["message"]}'
                    f'<br/><span style="font-size:0.6rem;color:{C_MUTED};">'
                    f'{alert.get("display_time", "")}</span></div>',
                    unsafe_allow_html=True
                )
            if unread > 0:
                if st.button("Mark all read", key="mark_read_btn", use_container_width=True):
                    mark_all_read()
                    st.rerun()
            st.markdown("---")

    st.markdown("---")

    # --- User info + logout ---
    if AUTH_AVAILABLE and is_authenticated():
        user = get_current_user()
        user_name = user.get("full_name", user.get("email", "Analyst")) if user else "Analyst"
        st.markdown(
            f'<div style="font-size:0.75rem;color:{C_TEXT2};padding:4px 0;">'
            f'\u2713 {user_name}</div>',
            unsafe_allow_html=True
        )
        if st.button("Logout", key="logout_btn", use_container_width=True):
            logout()
            st.rerun()
        st.markdown("---")

    # --- Report format selector ---
    st.markdown(_section_label("Report Format"), unsafe_allow_html=True)
    output_format = st.multiselect(
        "Format",
        ["Word (DOCX)", "PDF", "PowerPoint (PPTX)", "Excel (XLSX)"],
        default=["Word (DOCX)"],
        label_visibility="collapsed"
    )

    # Footer
    st.markdown(
        f"""
        <div style="position:fixed;bottom:12px;left:12px;right:12px;max-width:260px;">
            <hr style="border-color:{C_BORDER};margin-bottom:6px;" />
            <p style="font-size:0.55rem;color:{C_MUTED} !important;text-align:center;margin:0;
                      letter-spacing:0.02em;">
                TAM Capital | CMA Regulated<br>
                Confidential - Internal Use Only
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )


# ==========================================================
# HELPER FUNCTIONS — Ticker parsing, API calls, Analysis
# ==========================================================

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


def extract_multiple_tickers(message: str) -> list:
    """Extract multiple tickers from a comparison request."""
    lower = message.lower()
    is_compare = any(kw in lower for kw in [
        "compare", "vs", "versus", "against", "side by side",
        "head to head", "benchmark",
    ])
    if not is_compare:
        return []

    codes = re.findall(r'\b(\d{4})\b', message)
    if len(codes) >= 2:
        return [(resolve_ticker(code), code) for code in codes[:4]]

    tickers = re.findall(r'\((\w+(?:\.\w+)?)\)', message)
    if len(tickers) >= 2:
        return [(resolve_ticker(t), t) for t in tickers[:4]]

    upper_tickers = re.findall(r'\b([A-Z]{2,5})\b', message)
    skip = {"THE", "FOR", "AND", "BUT", "NOT", "ALL", "TAM", "EPS", "CEO",
            "ETF", "IPO", "ROE", "ROA", "FCF", "YOY", "QOQ", "FULL",
            "COMPARE", "VERSUS", "SIDE", "HEAD"}
    filtered = [t for t in upper_tickers if t not in skip]
    if len(filtered) >= 2:
        return [(resolve_ticker(t), t) for t in filtered[:4]]

    return []


# Saudi sector definitions
SAUDI_SECTORS = {
    "banks": {
        "name": "Saudi Banking Sector",
        "tickers": [("1120.SR", "Al Rajhi Bank"), ("1180.SR", "Al Inma Bank"),
                    ("1010.SR", "Riyad Bank"), ("1150.SR", "Alinma Bank")],
    },
    "petrochemicals": {
        "name": "Saudi Petrochemical Sector",
        "tickers": [("2010.SR", "SABIC"), ("2020.SR", "SABIC AN"),
                    ("2350.SR", "Saudi Kayan"), ("2060.SR", "Nat. Industrialization")],
    },
    "telecom": {
        "name": "Saudi Telecom Sector",
        "tickers": [("7010.SR", "STC"), ("7020.SR", "Etihad Etisalat"),
                    ("7030.SR", "Zain KSA")],
    },
    "retail": {
        "name": "Saudi Retail & Consumer Sector",
        "tickers": [("4001.SR", "Petromin"), ("4200.SR", "Aldawaa"),
                    ("3060.SR", "United Electronics"), ("2280.SR", "Almarai")],
    },
    "energy": {
        "name": "Saudi Energy Sector",
        "tickers": [("2222.SR", "Saudi Aramco"), ("4030.SR", "Bahri")],
    },
}


def detect_sector_request(message: str) -> str | None:
    """Detect if the user is asking for a sector-level analysis."""
    lower = message.lower()
    if not any(kw in lower for kw in [
        "sector", "industry", "banking sector", "banks sector",
        "petrochemical", "telecom", "retail", "energy sector",
        "overview", "landscape",
    ]):
        return None

    for key, info in SAUDI_SECTORS.items():
        if key in lower or info["name"].lower().split()[1] in lower:
            return key

    if any(w in lower for w in ["bank", "financial"]):
        return "banks"
    if any(w in lower for w in ["petrochem", "chemical", "sabic"]):
        return "petrochemicals"
    if any(w in lower for w in ["telecom", "telco", "stc", "mobile"]):
        return "telecom"
    if any(w in lower for w in ["retail", "consumer", "food"]):
        return "retail"
    if any(w in lower for w in ["energy", "oil", "gas", "aramco"]):
        return "energy"
    return None


def _call_with_retries(client, model: str, prompt: str, retries: int = 4) -> tuple:
    """Try a model with retries. Returns (text, model_used, input_tokens, output_tokens)."""
    import time
    import random
    for attempt in range(retries):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            in_tok = getattr(response.usage, 'input_tokens', 0) if hasattr(response, 'usage') else 0
            out_tok = getattr(response.usage, 'output_tokens', 0) if hasattr(response, 'usage') else 0
            return response.content[0].text, model, in_tok, out_tok
        except anthropic.RateLimitError:
            if attempt < retries - 1:
                base_wait = min(20 * (2 ** attempt), 90)
                wait = base_wait + random.uniform(1, 8)
                st.toast(f"API busy — waiting {int(wait)}s before retry ({attempt+1}/{retries-1})...")
                time.sleep(wait)
            else:
                raise
        except anthropic.APIStatusError as e:
            if e.status_code in (500, 502, 503, 529) and attempt < retries - 1:
                time.sleep(10 * (attempt + 1))
            else:
                raise
    raise anthropic.RateLimitError("Retries exhausted")


def call_claude(prompt: str, action: str = "research", ticker: str = "") -> str:
    """Call Claude API with fallback and token tracking."""
    client = anthropic.Anthropic(api_key=api_key)
    try:
        text, model_used, in_tok, out_tok = _call_with_retries(client, MODEL, prompt)
    except anthropic.RateLimitError:
        st.toast("Switching to faster model to avoid rate limits...")
        text, model_used, in_tok, out_tok = _call_with_retries(client, FALLBACK_MODEL, prompt)

    # Track token usage
    if TOKEN_TRACKER_AVAILABLE:
        try:
            user = st.session_state.get("user", {})
            user_id = user.get("id", "anonymous")
            track_tokens(
                user_id=user_id,
                model=model_used,
                input_tokens=in_tok,
                output_tokens=out_tok,
                action=action,
                ticker=ticker,
            )
        except Exception:
            pass

    return text


def generate_section(section_type: str, market_data_str: str, news_str: str, ticker: str = "") -> str:
    """Generate a single analysis section."""
    config = SECTION_CONFIG.get(section_type)
    if not config:
        return ""
    module = importlib.import_module(config["prompt_module"])
    prompt_template = getattr(module, config["prompt_var"])
    prompt = prompt_template.format(market_data=market_data_str, news_data=news_str)
    return call_claude(prompt, action=section_type, ticker=ticker)


# ==========================================================
# ANALYSIS PIPELINES
# ==========================================================

def _is_cancelled():
    """Check if user has requested analysis cancellation."""
    return st.session_state.get("cancel_analysis", False)


def run_full_analysis(ticker: str, company_name: str, user_message: str, formats: list) -> dict:
    """Run the complete analysis pipeline with cancellation support."""
    results = {"sections": {}, "charts": {}, "files": {}, "sources": None, "cancelled": False}
    collector = SourceCollector()
    st.session_state.analysis_running = True
    st.session_state.cancel_analysis = False

    # --- Cancel button (persists during entire analysis) ---
    cancel_col = st.empty()
    with cancel_col.container():
        if st.button("Stop Research", key="cancel_btn", type="secondary", use_container_width=True):
            st.session_state.cancel_analysis = True
            st.session_state.analysis_running = False

    with st.status("Collecting market intelligence...", expanded=True) as status:
        st.write("Fetching live market data...")
        stock_data = fetch_stock_data(ticker, collector=collector)
        if stock_data.get("name") and stock_data["name"] != ticker:
            company_name = stock_data["name"]

        if _is_cancelled():
            status.update(label="Cancelled", state="error")
            cancel_col.empty()
            results["cancelled"] = True
            st.session_state.analysis_running = False
            return results

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

        market_data_str = format_market_data_for_prompt(stock_data, technicals, hist, financials)
        status.update(label=f"Market data collected ({len(collector)} sources)", state="complete")

    if _is_cancelled():
        cancel_col.empty()
        results["cancelled"] = True
        st.session_state.analysis_running = False
        return results

    # --- Store stock_data for potential DCF use ---
    results["stock_data"] = stock_data

    # --- Interactive Plotly charts (if available) ---
    if PLOTLY_AVAILABLE and not hist.empty:
        with st.status("Building interactive charts...", expanded=False) as status:
            try:
                plotly_techs = calc_plotly_technicals(hist)
                results["plotly_charts"] = {
                    "candlestick": generate_candlestick_chart(hist, ticker, plotly_techs),
                    "rsi": generate_rsi_chart(hist),
                    "macd": generate_macd_chart(hist),
                }
            except Exception:
                results["plotly_charts"] = {}
            status.update(label="Interactive charts ready", state="complete")

    with st.status("Building visualizations...", expanded=False) as status:
        chart_dir = os.path.join(OUTPUT_DIR, "charts")
        charts = generate_all_charts(stock_data, technicals, hist, financials, dividends, chart_dir)
        results["charts"] = charts
        status.update(label=f"{len(charts)} charts generated", state="complete")

    if _is_cancelled():
        cancel_col.empty()
        results["cancelled"] = True
        st.session_state.analysis_running = False
        return results

    section_types = get_analysis_type_from_request(user_message)

    with st.status("Running multi-framework analysis...", expanded=True) as status:
        total = len(section_types)
        failed_sections = []
        for i, section_type in enumerate(section_types):
            # --- Check cancel before each section ---
            if _is_cancelled():
                st.warning(f"Research stopped after {i}/{total} sections.")
                break

            config = SECTION_CONFIG.get(section_type)
            if not config:
                continue
            st.write(f"[{i+1}/{total}] {config['title']}")
            try:
                import time as _t
                if i > 0:
                    _t.sleep(20)
                content = generate_section(section_type, market_data_str, news)
                results["sections"][config["section_key"]] = content
            except anthropic.RateLimitError:
                failed_sections.append(config['title'])
                st.warning(f"Skipped {config['title']} (rate limited)")
                _t.sleep(15)
                continue
            except Exception as e:
                failed_sections.append(config['title'])
                st.warning(f"{config['title']} failed: {str(e)}")
                continue

        if _is_cancelled():
            results["cancelled"] = True
            if results["sections"]:
                st.info(f"Partial results available ({len(results['sections'])} sections completed).")
            status.update(label=f"Stopped — {len(results['sections'])}/{total} sections", state="error")
        else:
            if failed_sections:
                st.warning(f"{len(failed_sections)} section(s) skipped: {', '.join(failed_sections)}")

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

    # --- Clean up cancel button ---
    cancel_col.empty()
    st.session_state.analysis_running = False

    # --- Skip file generation if cancelled with no content ---
    if results.get("cancelled") and not results["sections"]:
        return results

    with st.status("Preparing deliverables...", expanded=False) as status:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        results["sources"] = collector

        if "Word (DOCX)" in formats:
            try:
                docx_path = generate_docx_report(
                    company_name, ticker, results["sections"],
                    charts=results["charts"], output_dir=OUTPUT_DIR, sources=collector
                )
                results["files"]["docx"] = docx_path
            except Exception as e:
                st.warning(f"DOCX: {str(e)}")

        if "PDF" in formats:
            try:
                pdf_path = generate_pdf_report(
                    company_name, ticker, results["sections"],
                    charts=results["charts"], output_dir=OUTPUT_DIR, sources=collector
                )
                results["files"]["pdf"] = pdf_path
            except Exception:
                docx_for_pdf = results["files"].get("docx")
                if not docx_for_pdf:
                    try:
                        docx_for_pdf = generate_docx_report(
                            company_name, ticker, results["sections"],
                            charts=results["charts"], output_dir=OUTPUT_DIR, sources=collector
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
                    charts=results["charts"], output_dir=OUTPUT_DIR, sources=collector
                )
                results["files"]["pptx"] = pptx_path
            except Exception as e:
                st.warning(f"PPTX: {str(e)}")

        if "Excel (XLSX)" in formats:
            try:
                xlsx_path = generate_xlsx_report(
                    company_name, ticker, results["sections"],
                    charts=results["charts"], output_dir=OUTPUT_DIR, sources=collector
                )
                results["files"]["xlsx"] = xlsx_path
            except Exception as e:
                st.warning(f"XLSX: {str(e)}")

        try:
            save_report(company_name, ticker, results["sections"],
                        files=results.get("files", {}))
        except Exception:
            pass

        label = "Reports ready for download"
        if results.get("cancelled"):
            label = f"Partial reports generated ({len(results['sections'])} sections)"
        status.update(label=label, state="complete")

    return results


def run_comparison_analysis(stocks: list, user_message: str, formats: list) -> dict:
    """Run side-by-side comparison for multiple stocks."""
    comparison = {"stocks": {}, "files": {}}
    all_market_data = {}
    collector = SourceCollector()

    with st.status(f"Comparing {len(stocks)} stocks...", expanded=True) as status:
        for ticker, name in stocks:
            st.write(f"Fetching data for {name} ({ticker})...")
            stock_data = fetch_stock_data(ticker, collector=collector)
            real_name = stock_data.get("name", name)
            hist = fetch_price_history(ticker, collector=collector)
            technicals = calculate_technical_indicators(hist) if not hist.empty else {}
            financials = fetch_financials(ticker, collector=collector)
            dividends = fetch_dividend_history(ticker, collector=collector)
            market_data_str = format_market_data_for_prompt(stock_data, technicals, hist, financials)
            all_market_data[ticker] = {
                "name": real_name, "data_str": market_data_str,
                "stock_data": stock_data, "hist": hist,
                "technicals": technicals, "financials": financials, "dividends": dividends,
            }
        status.update(label="Data collected for all stocks", state="complete")

    with st.status("Running comparative analysis...", expanded=True) as status:
        combined_data = "\n\n===\n\n".join(
            f"[{info['name']} ({ticker})]\n{info['data_str']}"
            for ticker, info in all_market_data.items()
        )
        stock_names = ", ".join(
            f"{info['name']} ({ticker})" for ticker, info in all_market_data.items()
        )
        comparison_prompt = (
            f"You are a senior institutional equity analyst at TAM Capital, a CMA-regulated "
            f"asset manager in Saudi Arabia.\n\n"
            f"Provide a detailed COMPARATIVE ANALYSIS of: {stock_names}\n\n"
            f"Structure your response with these sections:\n"
            f"1. **Comparative Overview** — Brief positioning of each company\n"
            f"2. **Financial Metrics Comparison** — Side-by-side table of key metrics\n"
            f"3. **Valuation Analysis** — Which is undervalued/overvalued and why\n"
            f"4. **Growth Trajectory** — Revenue/earnings growth comparison\n"
            f"5. **Risk Profile** — Comparative risk assessment\n"
            f"6. **Investment Recommendation** — Clear ranking with rationale\n\n"
            f"Market data:\n{combined_data[:12000]}"
        )
        try:
            analysis = call_claude(comparison_prompt)
            comparison["analysis"] = analysis
        except Exception as e:
            comparison["analysis"] = f"Comparison analysis error: {str(e)}"
        status.update(label="Comparative analysis complete", state="complete")

    with st.status("Building comparison charts...", expanded=False) as status:
        for ticker, info in all_market_data.items():
            chart_dir = os.path.join(OUTPUT_DIR, "charts", ticker.replace(".", "_"))
            charts = generate_all_charts(
                info["stock_data"], info["technicals"], info["hist"],
                info["financials"], info["dividends"], chart_dir
            )
            comparison["stocks"][ticker] = {"name": info["name"], "charts": charts}
        status.update(label="Charts generated", state="complete")

    if any(fmt in formats for fmt in ["Word (DOCX)", "PDF", "Excel (XLSX)"]):
        with st.status("Preparing deliverables...", expanded=False) as status:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            comparison_sections = {"executive_summary": comparison.get("analysis", "")}
            combined_name = " vs ".join(info["name"] for _, info in comparison["stocks"].items())

            if "Word (DOCX)" in formats:
                try:
                    docx_path = generate_docx_report(
                        f"Comparison: {combined_name}", "COMPARE",
                        comparison_sections, output_dir=OUTPUT_DIR, sources=collector
                    )
                    comparison["files"]["docx"] = docx_path
                except Exception as e:
                    st.warning(f"DOCX: {str(e)}")

            if "Excel (XLSX)" in formats:
                try:
                    xlsx_path = generate_xlsx_report(
                        f"Comparison: {combined_name}", "COMPARE",
                        comparison_sections, output_dir=OUTPUT_DIR, sources=collector
                    )
                    comparison["files"]["xlsx"] = xlsx_path
                except Exception as e:
                    st.warning(f"XLSX: {str(e)}")

            comparison["sources"] = collector
            status.update(label="Reports ready", state="complete")

    return comparison


def run_sector_analysis(sector_key: str, user_message: str) -> dict:
    """Run a sector-level overview analysis."""
    sector = SAUDI_SECTORS[sector_key]
    result = {"name": sector["name"], "stocks": {}, "analysis": ""}
    collector = SourceCollector()

    with st.status(f"Analyzing {sector['name']}...", expanded=True) as status:
        all_data_parts = []
        for ticker, name in sector["tickers"]:
            st.write(f"Fetching {name} ({ticker})...")
            try:
                stock_data = fetch_stock_data(ticker, collector=collector)
                hist = fetch_price_history(ticker, period="1y", collector=collector)
                financials = fetch_financials(ticker, collector=collector)
                technicals = calculate_technical_indicators(hist) if not hist.empty else {}
                market_str = format_market_data_for_prompt(stock_data, technicals, hist, financials)
                all_data_parts.append(f"[{name} ({ticker})]\n{market_str}")
                result["stocks"][ticker] = {
                    "name": stock_data.get("name", name), "data": stock_data,
                }
            except Exception as e:
                st.write(f"  Skipped {name}: {str(e)}")

        st.write("Searching sector news...")
        sector_news = search_sector_news(sector["name"], collector=collector)
        status.update(label=f"Data collected for {len(result['stocks'])} stocks", state="complete")

    with st.status("Generating sector analysis...", expanded=True) as status:
        combined_data = "\n\n===\n\n".join(all_data_parts)
        sector_prompt = (
            f"You are a senior institutional research analyst at TAM Capital, "
            f"a CMA-regulated Saudi asset manager.\n\n"
            f"Provide a comprehensive SECTOR OVERVIEW for the **{sector['name']}** "
            f"on the Saudi Exchange (Tadawul).\n\n"
            f"Structure your analysis:\n"
            f"1. **Sector Overview** — Current state, size, and importance\n"
            f"2. **Key Players Comparison** — Table comparing market cap, revenue, P/E, ROE, dividend yield\n"
            f"3. **Sector Trends** — Growth drivers, headwinds, regulatory changes\n"
            f"4. **Valuation Heat Map** — Which stocks are cheap/expensive relative to peers\n"
            f"5. **Top Pick & Rationale** — Best investment opportunity in the sector\n"
            f"6. **Sector Outlook** — 6-12 month forward view\n\n"
            f"Recent news:\n{sector_news[:3000]}\n\n"
            f"Financial data:\n{combined_data[:10000]}"
        )
        try:
            analysis = call_claude(sector_prompt)
            result["analysis"] = analysis
        except Exception as e:
            result["analysis"] = f"Sector analysis error: {str(e)}"

        result["sources"] = collector
        status.update(label="Sector analysis complete", state="complete")

    return result


# ==========================================================
# DISPLAY HELPERS
# ==========================================================

def _display_download_buttons(files: dict, prefix: str = "dl"):
    """Render download buttons for generated files."""
    if not files:
        return
    st.markdown("---")
    st.markdown("#### Download Reports")
    cols = st.columns(len(files))
    ext_labels = {
        "docx": "Word Document", "pdf": "PDF Report",
        "pptx": "Presentation", "xlsx": "Excel Workbook"
    }
    for i, (fmt, path) in enumerate(files.items()):
        if os.path.exists(path):
            with cols[i]:
                with open(path, "rb") as f:
                    st.download_button(
                        label=f"{ext_labels.get(fmt, fmt.upper())}",
                        data=f.read(),
                        file_name=os.path.basename(path),
                        mime="application/octet-stream",
                        key=f"{prefix}_{fmt}_{datetime.now().timestamp()}"
                    )


def _display_sources(sources):
    """Render sources expander."""
    if sources and len(sources) > 0:
        st.markdown("---")
        with st.expander(f"Sources & References ({len(sources)} sources)"):
            st.markdown(sources.format_for_display())


def _display_comparison_view(old_report, new_report):
    """Display report comparison dashboard."""
    st.markdown("---")
    st.markdown(
        f"### Report Comparison\n"
        f"**{old_report['stock_name']}** ({old_report['date_display']})  vs  "
        f"**{new_report['stock_name']}** ({new_report['date_display']})"
    )

    metric_changes = compare_metrics(old_report["sections"], new_report["sections"])
    text_diffs = compare_text_sections(old_report["sections"], new_report["sections"])
    summary = build_comparison_summary(metric_changes, text_diffs)

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
        st.metric("Changed", summary["sections_changed"])
    with col4:
        largest = summary.get("largest_change")
        if largest and largest.get("change_pct") is not None:
            st.metric("Largest Move", largest["metric"], delta=f"{largest['change_pct']:+.1f}%")
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
            color = C_TEXT2
            if m["direction"] == "up":
                arrow = "&#9650;"
                color = C_GREEN
            elif m["direction"] == "down":
                arrow = "&#9660;"
                color = C_RED

            old_str = f"{m['old']:.2f}" if m["old"] is not None else "N/A"
            new_str = f"{m['new']:.2f}" if m["new"] is not None else "N/A"
            pct_str = f"{m['change_pct']:+.1f}%" if m["change_pct"] is not None else ""

            sev = m.get("severity", "")
            sev_colors = {"minor": C_CYAN, "moderate": C_ORANGE, "major": C_RED}
            sev_badge = (
                f"<span style='background:{sev_colors.get(sev, '#555')};color:white;"
                f"padding:1px 6px;border-radius:3px;font-size:0.65em;'>{sev}</span>"
            ) if sev and sev != "unknown" else ""

            rows_html += (
                f"<tr style='border-bottom:1px solid {C_BORDER};'>"
                f"<td style='padding:8px 14px;font-weight:600;color:{C_TEXT};'>{m['metric']}</td>"
                f"<td style='padding:8px 14px;text-align:right;color:{C_TEXT2};'>{old_str}</td>"
                f"<td style='padding:8px 14px;text-align:right;color:{C_TEXT2};'>{new_str}</td>"
                f"<td class='{'data-pulse-green' if m['direction'] == 'up' else 'data-pulse-red' if m['direction'] == 'down' else ''}'"
                f" style='padding:8px 14px;text-align:right;color:{color};'>"
                f"<span style='font-size:0.7em;'>{arrow}</span> {pct_str}</td>"
                f"<td style='padding:8px 14px;text-align:center;'>{sev_badge}</td>"
                f"</tr>"
            )

        st.markdown(
            f"""<table style="width:100%;border-collapse:collapse;font-size:0.85rem;
                 background:{C_CARD};border:1px solid {C_BORDER};border-radius:12px;overflow:hidden;">
            <thead><tr style="background:rgba(34,47,98,0.15);">
            <th style="padding:10px 14px;text-align:left;color:{C_TEXT};font-weight:600;
                font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em;">Metric</th>
            <th style="padding:10px 14px;text-align:right;color:{C_TEXT};font-weight:600;
                font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em;">Previous</th>
            <th style="padding:10px 14px;text-align:right;color:{C_TEXT};font-weight:600;
                font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em;">Current</th>
            <th style="padding:10px 14px;text-align:right;color:{C_TEXT};font-weight:600;
                font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em;">Change</th>
            <th style="padding:10px 14px;text-align:center;color:{C_TEXT};font-weight:600;
                font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em;">Severity</th>
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
                        diff_html += f'<div style="background:rgba(63,185,80,0.08);padding:4px 10px;margin:2px 0;border-left:2px solid {C_GREEN};font-size:0.82rem;border-radius:0 6px 6px 0;color:{C_TEXT2};">+ {text_esc}</div>'
                    elif typ == "removed":
                        diff_html += f'<div style="background:rgba(248,81,73,0.08);padding:4px 10px;margin:2px 0;border-left:2px solid {C_RED};font-size:0.82rem;border-radius:0 6px 6px 0;color:{C_TEXT2};">- {text_esc}</div>'
                    else:
                        diff_html += f'<div style="padding:4px 10px;margin:2px 0;font-size:0.82rem;color:{C_MUTED};">&nbsp; {text_esc}</div>'
                st.markdown(diff_html, unsafe_allow_html=True)


# ==========================================================
# PAGE: DASHBOARD
# ==========================================================

def render_dashboard():
    """Dashboard home — market overview + AI chat."""
    _render_branded_header("Market Overview", "Institutional-grade investment research")

    st.markdown("")

    # --- Feature Cards ---
    col1, col2, col3, col4 = st.columns(4)

    cards = [
        ("Equity Analysis", "Full Research Reports",
         "Goldman-style fundamentals, JPMorgan earnings, Morgan Stanley technicals"),
        ("Risk Intelligence", "News & Geopolitical Impact",
         "Real-time news assessment, war impact scenarios, stress testing"),
        ("Portfolio Tracking", "Live P&L Dashboard",
         "Position management, allocation metrics, rebalancing insights"),
        ("Multi-Format Export", "TAMS-Branded Reports",
         "Word, PDF, PowerPoint & Excel on TAM Capital letterhead"),
    ]

    for col, (label, title, desc) in zip([col1, col2, col3, col4], cards):
        with col:
            st.markdown(
                f"""
                <div style="{_glass_card_style('20px', '160px')}">
                    {_accent_label(label)}
                    <p style="color:{C_TEXT};font-size:0.9rem;font-weight:600;margin-bottom:6px;">
                        {title}</p>
                    <p style="color:{C_TEXT2};font-size:0.78rem;line-height:1.5;">
                        {desc}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.markdown("")

    # --- Morning Brief Widget ---
    if MORNING_BRIEF_AVAILABLE:
        user_name = "Analyst"
        if AUTH_AVAILABLE and is_authenticated():
            u = get_current_user()
            if u:
                user_name = u.get("full_name", u.get("email", "Analyst")).split()[0]
        today_str = datetime.now().strftime("%A, %B %d, %Y")
        st.markdown(
            f"""<div style="{_card_style('20px')}margin-bottom:16px;
                border-left:3px solid {C_ACCENT};">
                <span style="color:{C_TEXT};font-weight:700;font-size:1rem;">
                    Good morning, {user_name}</span>
                <p style="color:{C_TEXT2};font-size:0.85rem;margin-top:4px;">
                    {today_str} &mdash; Here's your market brief</p>
            </div>""",
            unsafe_allow_html=True
        )

        watched_tickers = get_all_watched_tickers()
        if watched_tickers:
            with st.expander("Generate Morning Brief", expanded=False):
                if st.button("Generate Today's Brief", key="gen_morning_brief",
                             use_container_width=True):
                    with st.spinner("Generating your morning brief..."):
                        try:
                            brief = generate_morning_brief(
                                watched_tickers[:10], api_key, MODEL
                            )
                            brief_html = format_brief_for_display(brief)
                            st.markdown(brief_html, unsafe_allow_html=True)
                        except Exception as e:
                            st.warning(f"Could not generate brief: {str(e)}")

    # --- Smart Suggestions ---
    if RECOMMENDATIONS_AVAILABLE:
        try:
            user_id = None
            if AUTH_AVAILABLE and is_authenticated():
                u = get_current_user()
                if u:
                    user_id = u.get("id")
            suggestions = get_smart_suggestions(user_id, max_suggestions=3)
            if suggestions:
                suggestions_html = generate_suggestions_html(suggestions)
                st.markdown(suggestions_html, unsafe_allow_html=True)
        except Exception:
            pass

    # --- Two-column: AI Chat + Watchlist/Recent ---
    chat_col, side_col = st.columns([3, 1])

    with chat_col:
        st.markdown(
            f"""<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
                <div style="width:8px;height:8px;border-radius:50%;background:{ACCENT_GRADIENT};
                     box-shadow:0 0 8px {C_ACCENT};"></div>
                <span style="color:{C_TEXT};font-weight:600;font-size:1rem;">AI Research Assistant</span>
            </div>""",
            unsafe_allow_html=True
        )

        # Chat history
        for msg_idx, msg in enumerate(st.session_state.messages):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg["role"] == "assistant" and "files" in msg:
                    _display_download_buttons(msg["files"], f"hist_{msg_idx}")

        # Comparison display
        compare_request = st.session_state.pop("compare_request", None)
        if compare_request:
            old_id, new_id = compare_request
            old_report = load_report(old_id)
            new_report = load_report(new_id)
            if old_report and new_report:
                _display_comparison_view(old_report, new_report)

        # Quick prompt from sidebar
        quick_prompt = st.session_state.pop("quick_prompt", None)

        # Preferences toggle + Chat input
        pref_col1, pref_col2 = st.columns([5, 1])
        with pref_col2:
            if st.button("Customize", key="dash_pref_toggle",
                          help="Set analysis preferences before running"):
                st.session_state.show_preferences = not st.session_state.show_preferences
                st.rerun()

        if st.session_state.show_preferences:
            _render_preferences_panel()

        user_input = st.chat_input("Ask about any stock, sector, or market topic...")
        prompt = quick_prompt or user_input

        if prompt:
            _handle_user_prompt(prompt)

    with side_col:
        # Watchlist quick access
        st.markdown(
            f"""<div style="display:flex;align-items:center;gap:6px;margin-bottom:10px;">
                <span style="color:{C_TEXT};font-weight:600;font-size:0.85rem;">Quick Research</span>
            </div>""",
            unsafe_allow_html=True
        )

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
                for idx, item in enumerate(active_wl["items"][:8]):
                    if st.button(f"{item['name']}", key=f"dash_wl_{idx}", use_container_width=True):
                        st.session_state["quick_prompt"] = (
                            f"Full report on {item['name']} ({item['ticker']})"
                        )
                        st.rerun()

        # Sector quick links
        st.markdown("")
        st.markdown(
            f'<p style="color:{C_MUTED};font-size:0.6rem;text-transform:uppercase;'
            f'letter-spacing:0.15em;margin-bottom:6px;font-weight:600;">Sectors</p>',
            unsafe_allow_html=True
        )
        for key, info in list(SAUDI_SECTORS.items())[:5]:
            if st.button(info["name"].replace("Saudi ", ""), key=f"dash_sec_{key}", use_container_width=True):
                st.session_state.current_page = "sectors"
                st.session_state["sector_prompt"] = f"sector overview {key}"
                st.rerun()

        # Report history
        st.markdown("")
        saved_reports = list_reports()
        if saved_reports:
            st.markdown(
                f'<p style="color:{C_MUTED};font-size:0.6rem;text-transform:uppercase;'
                f'letter-spacing:0.15em;margin-bottom:6px;font-weight:600;">Recent Reports</p>',
                unsafe_allow_html=True
            )
            for r in saved_reports[:5]:
                ver = f"v{r['version']}" if r.get("version") else ""
                st.markdown(
                    f'<div style="font-size:0.78rem;margin-bottom:6px;padding:6px 10px;'
                    f'background:{C_CARD};border-radius:8px;border:1px solid {C_BORDER};">'
                    f'<span style="color:{C_TEXT};font-weight:500;">{r["stock_name"]}</span> '
                    f'<span style="color:{C_ACCENT};font-size:0.7rem;font-weight:600;">{ver}</span>'
                    f'<br/><span style="color:{C_MUTED};font-size:0.65rem;">{r["date_display"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )

            # Compare
            if len(saved_reports) >= 2:
                with st.expander("Compare Reports"):
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
                        st.rerun()


# ==========================================================
# PAGE: RESEARCH (Dedicated chat-first page)
# ==========================================================

def _render_branded_header(title, subtitle=None, badge=None):
    """Render a branded header bar for any page."""
    logo_html = ""
    if LOGO_B64:
        logo_html = (
            f'<img src="data:image/png;base64,{LOGO_B64}" height="32"'
            f' style="opacity:0.9;" />'
        )
    badge_html = ""
    if badge:
        badge_html = f'<span class="tam-badge">{badge}</span>'
    sub_html = ""
    if subtitle:
        sub_html = f'<div class="tam-subtitle">{subtitle}</div>'
    st.markdown(
        f'<div class="tam-header-bar">'
        f'{logo_html}'
        f'<div><div class="tam-title">{title}</div>{sub_html}</div>'
        f'{badge_html}'
        f'</div>',
        unsafe_allow_html=True
    )


def _render_market_overview_empty_state():
    """Show market overview cards when no chat history — Research page empty state."""
    st.markdown(
        f'<div style="text-align:center;padding:2rem 0 1rem 0;">'
        f'<h2 style="color:{C_TEXT};font-weight:700;font-size:1.5rem;margin-bottom:4px;">'
        f'What would you like to research?</h2>'
        f'<p style="color:{C_TEXT2};font-size:0.9rem;">Ask about any Saudi-listed stock, sector, or market trend.</p>'
        f'</div>',
        unsafe_allow_html=True
    )

    # Quick action chips
    quick_actions = [
        "Analyze SABIC", "TASI market outlook", "Banking sector review",
        "Al Rajhi vs SNB", "Top dividend stocks", "Aramco earnings"
    ]
    chips_html = '<div style="text-align:center;margin-bottom:1.5rem;">'
    for action in quick_actions:
        chips_html += f'<span class="quick-chip">{action}</span>'
    chips_html += '</div>'
    st.markdown(chips_html, unsafe_allow_html=True)

    # Market overview cards
    st.markdown(_section_label("Market Snapshot"), unsafe_allow_html=True)
    try:
        tasi_data = fetch_stock_data("^TASI.SR") if "fetch_stock_data" in dir() else {}
        tasi_price = tasi_data.get("price", tasi_data.get("regularMarketPrice", "—"))
        tasi_change = tasi_data.get("regularMarketChangePercent", 0)
    except Exception:
        tasi_price = "—"
        tasi_change = 0

    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1:
        delta_class = "positive" if tasi_change >= 0 else "negative"
        delta_sign = "+" if tasi_change >= 0 else ""
        tasi_display = f"{tasi_price:,.0f}" if isinstance(tasi_price, (int, float)) else str(tasi_price)
        st.markdown(
            f'<div class="market-card">'
            f'<div class="market-card-label">TASI Index</div>'
            f'<div class="market-card-value">{tasi_display}</div>'
            f'<div class="market-card-delta {delta_class}">{delta_sign}{tasi_change:.2f}%</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    with mc2:
        st.markdown(
            f'<div class="market-card">'
            f'<div class="market-card-label">Aramco</div>'
            f'<div class="market-card-value">2222.SR</div>'
            f'<div class="market-card-delta" style="color:{C_TEXT2};">Saudi Oil Giant</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    with mc3:
        st.markdown(
            f'<div class="market-card">'
            f'<div class="market-card-label">Al Rajhi</div>'
            f'<div class="market-card-value">1120.SR</div>'
            f'<div class="market-card-delta" style="color:{C_TEXT2};">Banking Leader</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    with mc4:
        st.markdown(
            f'<div class="market-card">'
            f'<div class="market-card-label">SABIC</div>'
            f'<div class="market-card-value">2010.SR</div>'
            f'<div class="market-card-delta" style="color:{C_TEXT2};">Petrochemicals</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown('<div style="height:1rem;"></div>', unsafe_allow_html=True)


def render_research():
    """Full research chat interface."""
    # Branded header
    _render_branded_header("Research Terminal", "AI-powered investment research", "Live")

    # If no chat history, show the market overview empty state
    if not st.session_state.messages:
        _render_market_overview_empty_state()

    # Chat history
    for msg_idx, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and "files" in msg:
                _display_download_buttons(msg["files"], f"res_{msg_idx}")

    # Comparison display
    compare_request = st.session_state.pop("compare_request", None)
    if compare_request:
        old_id, new_id = compare_request
        old_report = load_report(old_id)
        new_report = load_report(new_id)
        if old_report and new_report:
            _display_comparison_view(old_report, new_report)

    # Preferences toggle
    res_pref_col1, res_pref_col2 = st.columns([5, 1])
    with res_pref_col2:
        if st.button("Customize", key="res_pref_toggle",
                      help="Set analysis preferences before running"):
            st.session_state.show_preferences = not st.session_state.show_preferences
            st.rerun()

    if st.session_state.show_preferences:
        _render_preferences_panel()

    quick_prompt = st.session_state.pop("quick_prompt", None)
    user_input = st.chat_input("Enter stock name, ticker, or question...")
    prompt = quick_prompt or user_input

    if prompt:
        _handle_user_prompt(prompt)


# ==========================================================
# PAGE: PORTFOLIO
# ==========================================================

def render_portfolio():
    """Portfolio dashboard with live metrics."""
    _render_branded_header("Portfolio", "Live positions and P&L tracking")

    positions = get_positions()

    if not positions:
        st.markdown(
            f"""<div style="{_glass_card_style('32px')};text-align:center;">
                <p style="color:{C_TEXT};font-size:1rem;font-weight:600;margin-bottom:8px;">
                    No positions yet</p>
                <p style="color:{C_TEXT2};font-size:0.85rem;">
                    Add positions from the sidebar to start tracking your portfolio.</p>
            </div>""",
            unsafe_allow_html=True
        )
    else:
        # Fetch live prices
        live_prices = {}
        with st.status("Fetching live prices...", expanded=False) as status:
            for pos in positions:
                try:
                    sd = fetch_stock_data(pos["ticker"])
                    price = sd.get("price", sd.get("regularMarketPrice", pos["cost_basis"]))
                    live_prices[pos["ticker"]] = price
                except Exception:
                    live_prices[pos["ticker"]] = pos["cost_basis"]
            status.update(label="Prices updated", state="complete")

        metrics = calculate_portfolio_metrics(positions, live_prices)
        pnl_color = C_GREEN if metrics["total_pnl"] >= 0 else C_RED
        pnl_sign = "+" if metrics["total_pnl"] >= 0 else ""

        # Summary metrics row
        m_cols = st.columns(4)
        with m_cols[0]:
            st.metric("Total Value", f"SAR {metrics['total_value']:,.0f}")
        with m_cols[1]:
            st.metric("Total Cost", f"SAR {metrics['total_cost']:,.0f}")
        with m_cols[2]:
            st.metric("Total P&L", f"SAR {metrics['total_pnl']:,.0f}",
                      delta=f"{pnl_sign}{metrics['total_pnl_pct']:.1f}%")
        with m_cols[3]:
            st.metric("Positions", str(len(positions)))

        st.markdown("")

        # Positions table
        if metrics["positions"]:
            rows_html = ""
            for p in metrics["positions"]:
                p_color = C_GREEN if p["pnl"] >= 0 else C_RED
                p_sign = "+" if p["pnl"] >= 0 else ""
                rows_html += (
                    f"<tr style='border-bottom:1px solid {C_BORDER};'>"
                    f"<td style='padding:10px 14px;color:{C_TEXT};font-weight:500;'>{p['name']}</td>"
                    f"<td style='padding:10px 14px;color:{C_TEXT2};'>{p['ticker']}</td>"
                    f"<td style='padding:10px 14px;color:{C_TEXT2};text-align:right;'>{p['shares']:.0f}</td>"
                    f"<td style='padding:10px 14px;color:{C_TEXT2};text-align:right;'>{p['cost_basis']:.2f}</td>"
                    f"<td style='padding:10px 14px;color:{C_TEXT2};text-align:right;'>{p['current_price']:.2f}</td>"
                    f"<td style='padding:10px 14px;color:{C_TEXT2};text-align:right;'>{p['market_value']:,.0f}</td>"
                    f"<td style='padding:10px 14px;color:{p_color};text-align:right;font-weight:600;'>"
                    f"{p_sign}{p['pnl']:,.0f} ({p_sign}{p['pnl_pct']:.1f}%)</td>"
                    f"<td style='padding:10px 14px;color:{C_TEXT2};text-align:right;'>{p['weight']:.1f}%</td>"
                    f"</tr>"
                )

            st.markdown(
                f"""<table style="width:100%;border-collapse:collapse;font-size:0.85rem;
                     background:{C_CARD};border:1px solid {C_BORDER};border-radius:14px;overflow:hidden;">
                <thead><tr style="background:rgba(34,47,98,0.15);">
                <th style="padding:10px 14px;text-align:left;color:{C_TEXT};font-size:0.7rem;text-transform:uppercase;letter-spacing:0.06em;">Name</th>
                <th style="padding:10px 14px;text-align:left;color:{C_TEXT};font-size:0.7rem;text-transform:uppercase;letter-spacing:0.06em;">Ticker</th>
                <th style="padding:10px 14px;text-align:right;color:{C_TEXT};font-size:0.7rem;text-transform:uppercase;letter-spacing:0.06em;">Shares</th>
                <th style="padding:10px 14px;text-align:right;color:{C_TEXT};font-size:0.7rem;text-transform:uppercase;letter-spacing:0.06em;">Cost</th>
                <th style="padding:10px 14px;text-align:right;color:{C_TEXT};font-size:0.7rem;text-transform:uppercase;letter-spacing:0.06em;">Price</th>
                <th style="padding:10px 14px;text-align:right;color:{C_TEXT};font-size:0.7rem;text-transform:uppercase;letter-spacing:0.06em;">Value</th>
                <th style="padding:10px 14px;text-align:right;color:{C_TEXT};font-size:0.7rem;text-transform:uppercase;letter-spacing:0.06em;">P&L</th>
                <th style="padding:10px 14px;text-align:right;color:{C_TEXT};font-size:0.7rem;text-transform:uppercase;letter-spacing:0.06em;">Weight</th>
                </tr></thead>
                <tbody>{rows_html}</tbody></table>""",
                unsafe_allow_html=True
            )

        # AI Commentary
        st.markdown("")
        if st.button("Generate AI Portfolio Commentary", key="port_commentary_btn", use_container_width=False):
            with st.status("Analyzing portfolio...", expanded=True) as status:
                portfolio_str = "\n".join(
                    f"{p['name']} ({p['ticker']}): {p['shares']:.0f} shares, "
                    f"cost {p['cost_basis']:.2f}, current {p['current_price']:.2f}, "
                    f"P&L {p['pnl']:+,.0f} ({p['pnl_pct']:+.1f}%), weight {p['weight']:.1f}%"
                    for p in metrics["positions"]
                )
                try:
                    commentary = call_claude(
                        f"You are a senior portfolio manager at TAM Capital.\n"
                        f"Provide a brief portfolio review and recommendations:\n\n"
                        f"Total Value: SAR {metrics['total_value']:,.0f}\n"
                        f"Total P&L: SAR {metrics['total_pnl']:,.0f} ({metrics['total_pnl_pct']:+.1f}%)\n\n"
                        f"Positions:\n{portfolio_str}\n\n"
                        f"Cover: concentration risk, rebalancing needs, and action items."
                    )
                    status.update(label="Complete", state="complete")
                    st.markdown("---")
                    st.markdown("#### Portfolio Commentary")
                    st.markdown(commentary[:2000])
                except Exception as e:
                    st.warning(f"Commentary error: {str(e)}")

    # --- Risk Analytics ---
    if RISK_AVAILABLE and positions and len(positions) >= 1:
        st.markdown("---")
        st.markdown("#### Risk Analytics")
        with st.expander("Portfolio Risk Metrics", expanded=False):
            with st.spinner("Calculating risk metrics..."):
                try:
                    # Fetch 1-year price history for each position
                    price_hist = {}
                    for pos in positions:
                        try:
                            h = fetch_price_history(pos["ticker"], period="1y")
                            if not h.empty:
                                price_hist[pos["ticker"]] = h
                        except Exception:
                            pass

                    if price_hist:
                        risk_data = calculate_portfolio_risk(positions, price_hist)
                        risk_charts = generate_risk_charts(risk_data, positions)

                        # Key metrics row
                        rc1, rc2, rc3, rc4 = st.columns(4)
                        with rc1:
                            var_val = risk_data.get("var_95_1day", 0)
                            st.metric("1-Day VaR (95%)", f"{var_val*100:.2f}%")
                        with rc2:
                            sharpe = risk_data.get("sharpe_ratio", 0)
                            st.metric("Sharpe Ratio", f"{sharpe:.2f}")
                        with rc3:
                            mdd = risk_data.get("max_drawdown", 0)
                            st.metric("Max Drawdown", f"{mdd*100:.1f}%")
                        with rc4:
                            beta = risk_data.get("portfolio_beta", 1)
                            st.metric("Portfolio Beta", f"{beta:.2f}")

                        # Charts in tabs
                        risk_tabs = st.tabs(["Drawdown", "Correlation", "Return Distribution", "Risk vs Return"])
                        chart_keys = ["drawdown", "correlation", "var_distribution", "risk_return"]
                        for tab, key in zip(risk_tabs, chart_keys):
                            with tab:
                                if key in risk_charts:
                                    st.plotly_chart(risk_charts[key], use_container_width=True,
                                                    key=f"risk_{key}_{id(risk_charts[key])}")
                    else:
                        st.info("Not enough price history to calculate risk metrics.")
                except Exception as e:
                    st.warning(f"Risk calculation error: {str(e)}")

    # Manage positions
    st.markdown("---")
    st.markdown("#### Manage Positions")
    add_cols = st.columns(4)
    with add_cols[0]:
        p_ticker = st.text_input("Ticker", placeholder="e.g. 2222", key="port_page_ticker")
    with add_cols[1]:
        p_shares = st.number_input("Shares", min_value=0.0, step=1.0, key="port_page_shares")
    with add_cols[2]:
        p_cost = st.number_input("Cost/share", min_value=0.0, step=0.01, key="port_page_cost")
    with add_cols[3]:
        st.markdown("<br/>", unsafe_allow_html=True)
        if st.button("Add Position", key="port_page_add_btn", use_container_width=True):
            if p_ticker and p_shares > 0 and p_cost > 0:
                resolved = resolve_ticker(p_ticker.strip())
                add_position(resolved, p_ticker.strip().upper(), p_shares, p_cost)
                st.rerun()

    if positions:
        rm_cols = st.columns([3, 1])
        with rm_cols[0]:
            rm_pos = st.selectbox(
                "Remove a position",
                [(p["id"], f"{p['name']} ({p['shares']:.0f} shares)") for p in positions],
                format_func=lambda x: x[1],
                key="port_page_rm_select",
            )
        with rm_cols[1]:
            st.markdown("<br/>", unsafe_allow_html=True)
            if st.button("Remove", key="port_page_rm_btn", use_container_width=True):
                remove_position(rm_pos[0])
                st.rerun()


# ==========================================================
# PAGE: SECTORS
# ==========================================================

def render_sectors():
    """Sector overview with drill-down."""
    _render_branded_header("Sectors", "Saudi market sector analysis")

    # Sector cards grid
    sector_items = list(SAUDI_SECTORS.items())
    row1 = sector_items[:3]
    row2 = sector_items[3:]

    for row in [row1, row2]:
        cols = st.columns(len(row) if row else 1)
        for col, (key, info) in zip(cols, row):
            with col:
                num_stocks = len(info["tickers"])
                ticker_names = ", ".join(name for _, name in info["tickers"][:3])
                st.markdown(
                    f"""<div style="{_glass_card_style('20px', '140px')}">
                        {_accent_label(f"{num_stocks} stocks")}
                        <p style="color:{C_TEXT};font-size:0.95rem;font-weight:600;margin-bottom:6px;">
                            {info['name'].replace('Saudi ', '')}</p>
                        <p style="color:{C_TEXT2};font-size:0.75rem;line-height:1.4;">
                            {ticker_names}</p>
                    </div>""",
                    unsafe_allow_html=True
                )
                if st.button(f"Analyze {key.title()}", key=f"sec_btn_{key}", use_container_width=True):
                    st.session_state["sector_prompt"] = f"sector overview {key}"
                    st.rerun()

    # Handle sector analysis request
    sector_prompt = st.session_state.pop("sector_prompt", None)
    if sector_prompt:
        sector_key = detect_sector_request(sector_prompt)
        if sector_key:
            st.markdown("---")
            try:
                result = run_sector_analysis(sector_key, sector_prompt)
                analysis = result.get("analysis", "")
                if analysis:
                    st.markdown(f"#### {result['name']}")
                    st.markdown(analysis[:4000])
                _display_sources(result.get("sources"))
            except Exception as e:
                st.error(f"Sector analysis error: {str(e)}")


# ==========================================================
# PAGE: COMPARISON
# ==========================================================

def render_comparison():
    """Multi-stock comparison tool."""
    _render_branded_header("Compare", "Multi-stock side-by-side analysis")

    st.markdown(
        f'<p style="color:{C_TEXT2};font-size:0.9rem;margin-bottom:16px;">'
        f'Compare multiple stocks side by side. Enter tickers separated by commas or use '
        f'"vs" (e.g., "Compare 2222 vs 1120 vs 7010").</p>',
        unsafe_allow_html=True
    )

    compare_input = st.text_input(
        "Enter comparison",
        placeholder='e.g. "Compare 2222 vs 1120" or "Aramco vs Al Rajhi"',
        key="cmp_page_input"
    )

    if st.button("Run Comparison", key="cmp_page_btn", use_container_width=False):
        if compare_input:
            # Force comparison detection
            query = compare_input if "compare" in compare_input.lower() else f"Compare {compare_input}"
            multi_stocks = extract_multiple_tickers(query)
            if multi_stocks:
                stock_labels = ", ".join(f"**{name}** `{ticker}`" for ticker, name in multi_stocks)
                st.markdown(f"Comparing: {stock_labels}")

                try:
                    results = run_comparison_analysis(multi_stocks, query, output_format)
                    analysis = results.get("analysis", "")
                    if analysis:
                        st.markdown("---")
                        st.markdown("#### Comparative Analysis")
                        st.markdown(analysis[:4000])

                    for ticker_key, stock_info in results.get("stocks", {}).items():
                        if stock_info.get("charts"):
                            st.markdown("---")
                            st.markdown(f"##### {stock_info['name']} Charts")
                            chart_cols = st.columns(min(len(stock_info["charts"]), 2))
                            for i, (name, path) in enumerate(stock_info["charts"].items()):
                                if os.path.exists(path):
                                    with chart_cols[i % 2]:
                                        st.image(path, caption=name.replace("_", " ").title())

                    _display_download_buttons(results.get("files", {}), "cmp_page")
                    _display_sources(results.get("sources"))

                except Exception as e:
                    st.error(f"Comparison error: {str(e)}")
            else:
                st.warning("Please enter at least 2 tickers to compare.")

    # Quick comparisons
    st.markdown("---")
    st.markdown("#### Quick Comparisons")
    quick_cmps = [
        ("Banks", "Compare 1120 vs 1180 vs 1010"),
        ("Telecom", "Compare 7010 vs 7020 vs 7030"),
        ("Energy", "Compare 2222 vs 2010 vs 2020"),
    ]
    qcols = st.columns(len(quick_cmps))
    for col, (label, query) in zip(qcols, quick_cmps):
        with col:
            if st.button(f"{label} Comparison", key=f"qcmp_{label}", use_container_width=True):
                st.session_state["cmp_page_auto"] = query
                st.rerun()

    auto_query = st.session_state.pop("cmp_page_auto", None)
    if auto_query:
        multi_stocks = extract_multiple_tickers(auto_query)
        if multi_stocks:
            stock_labels = ", ".join(f"**{name}** `{ticker}`" for ticker, name in multi_stocks)
            st.markdown(f"Comparing: {stock_labels}")
            try:
                results = run_comparison_analysis(multi_stocks, auto_query, output_format)
                analysis = results.get("analysis", "")
                if analysis:
                    st.markdown("---")
                    st.markdown("#### Comparative Analysis")
                    st.markdown(analysis[:4000])

                for ticker_key, stock_info in results.get("stocks", {}).items():
                    if stock_info.get("charts"):
                        st.markdown("---")
                        st.markdown(f"##### {stock_info['name']} Charts")
                        chart_cols = st.columns(min(len(stock_info["charts"]), 2))
                        for i, (name, path) in enumerate(stock_info["charts"].items()):
                            if os.path.exists(path):
                                with chart_cols[i % 2]:
                                    st.image(path, caption=name.replace("_", " ").title())

                _display_download_buttons(results.get("files", {}), "cmp_auto")
                _display_sources(results.get("sources"))
            except Exception as e:
                st.error(f"Comparison error: {str(e)}")


# ==========================================================
# PAGE: WATCHLIST
# ==========================================================

def render_watchlist():
    """Watchlist management page."""
    _render_branded_header("Watchlist", "Track stocks and set alerts")

    wl_list = get_watchlists()
    if not wl_list:
        try:
            create_watchlist("My Watchlist", "Default watchlist")
            for t, n in [("2020", "SABIC AN"), ("2222", "Aramco"),
                         ("1120", "Al Rajhi"), ("7010", "STC")]:
                add_ticker(get_default_watchlist()["id"], resolve_ticker(t), n)
        except Exception:
            pass
        wl_list = get_watchlists()

    active_wl = get_default_watchlist()
    if active_wl and active_wl.get("items"):
        items = active_wl["items"]

        # Watchlist cards
        cols_per_row = 3
        for row_start in range(0, len(items), cols_per_row):
            row_items = items[row_start:row_start + cols_per_row]
            cols = st.columns(cols_per_row)
            for i, item in enumerate(row_items):
                with cols[i]:
                    st.markdown(
                        f"""<div style="{_glass_card_style('16px')}">
                            <p style="color:{C_TEXT};font-weight:600;font-size:0.95rem;margin-bottom:2px;">
                                {item['name']}</p>
                            <p style="color:{C_MUTED};font-size:0.75rem;">{item['ticker']}</p>
                        </div>""",
                        unsafe_allow_html=True
                    )
                    if st.button(f"Analyze", key=f"wl_page_{row_start}_{i}", use_container_width=True):
                        st.session_state.current_page = "research"
                        st.session_state["quick_prompt"] = (
                            f"Full report on {item['name']} ({item['ticker']})"
                        )
                        st.rerun()

    # Add/remove controls
    st.markdown("---")
    st.markdown("#### Manage Watchlist")
    add_col, rm_col = st.columns(2)
    with add_col:
        new_ticker = st.text_input("Add ticker", key="wl_page_add", placeholder="e.g. 2222")
        if st.button("Add", key="wl_page_add_btn", use_container_width=True) and new_ticker:
            try:
                if active_wl:
                    resolved = resolve_ticker(new_ticker.strip())
                    add_ticker(active_wl["id"], resolved, new_ticker.strip().upper())
                    st.rerun()
            except ValueError as e:
                st.warning(str(e))
    with rm_col:
        if active_wl and active_wl.get("items"):
            rm_choice = st.selectbox(
                "Remove ticker",
                [i["ticker"] for i in active_wl["items"]],
                key="wl_page_rm_select"
            )
            if st.button("Remove", key="wl_page_rm_btn", use_container_width=True):
                remove_ticker(active_wl["id"], rm_choice)
                st.rerun()

    # --- Alert Rules ---
    if ALERT_RULES_AVAILABLE:
        st.markdown("---")
        st.markdown(
            f"""<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
                <span style="color:{C_TEXT};font-weight:700;font-size:1rem;">
                    \u26A0 Quick Alert Rules</span>
            </div>""",
            unsafe_allow_html=True
        )
        with st.expander("Configure Alert Rules", expanded=False):
            render_alert_rules_panel()


# ==========================================================
# PROMPT HANDLER — Routes user input to correct pipeline
# ==========================================================

def _render_preferences_panel():
    """Render the pre-analysis preferences panel as a glass card."""
    prefs = st.session_state.analysis_preferences
    st.markdown(
        f"""<div style="{_glass_card_style('20px')};margin-bottom:16px;">
            <div style="font-size:0.85rem;font-weight:600;color:{C_TEXT};margin-bottom:12px;">
                Customize your analysis</div>
            <div style="font-size:0.72rem;color:{C_TEXT2};margin-bottom:8px;">
                Set preferences below, or click <b>Quick Start</b> to use defaults.</div>
        </div>""",
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)
    with col1:
        prefs["horizon"] = st.selectbox(
            "Investment Horizon",
            ["Short-term (< 3 months)", "Medium-term (6-12 months)", "Long-term (1-3 years)"],
            index=1, key="pref_horizon"
        )
        prefs["language"] = st.selectbox(
            "Report Language",
            ["English", "Arabic", "Both (English + Arabic)"],
            index=0, key="pref_lang"
        )
    with col2:
        prefs["focus"] = st.multiselect(
            "Analysis Focus",
            ["Full Analysis", "Fundamentals Only", "Technicals Only",
             "Earnings Focus", "Dividend Focus", "Risk Assessment"],
            default=["Full Analysis"], key="pref_focus"
        )
        if DCF_AVAILABLE:
            prefs["include_dcf"] = st.checkbox("Include DCF Valuation", value=False, key="pref_dcf")

    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("Run Analysis", key="pref_run", type="primary", use_container_width=True):
            st.session_state.show_preferences = False
            return True
    with btn_col2:
        if st.button("Cancel", key="pref_cancel", use_container_width=True):
            st.session_state.show_preferences = False
            st.session_state.pending_prompt = None
            st.rerun()
    return False


def _display_plotly_charts(results: dict):
    """Display interactive Plotly charts if available."""
    plotly_charts = results.get("plotly_charts", {})
    if not plotly_charts:
        return

    st.markdown("---")
    st.markdown("#### Interactive Charts")
    tab_names = []
    tab_charts = []
    if "candlestick" in plotly_charts:
        tab_names.append("Price & Volume")
        tab_charts.append(plotly_charts["candlestick"])
    if "rsi" in plotly_charts:
        tab_names.append("RSI")
        tab_charts.append(plotly_charts["rsi"])
    if "macd" in plotly_charts:
        tab_names.append("MACD")
        tab_charts.append(plotly_charts["macd"])

    if tab_names:
        tabs = st.tabs(tab_names)
        for tab, chart in zip(tabs, tab_charts):
            with tab:
                st.plotly_chart(chart, use_container_width=True, key=f"plotly_{id(chart)}")


def _display_dcf_section(stock_data: dict, ticker: str):
    """Display DCF valuation model if available and requested."""
    if not DCF_AVAILABLE:
        return
    prefs = st.session_state.analysis_preferences
    if not prefs.get("include_dcf"):
        return

    st.markdown("---")
    st.markdown("#### DCF Valuation Model")

    try:
        model = DCFModel(stock_data)
        assumptions = get_default_assumptions(stock_data)
        result = model.calculate(assumptions)
        display = format_dcf_for_display(result)

        # Key metrics row
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Implied Price", display["implied_price"])
        with m2:
            upside = result["upside_pct"]
            st.metric("Upside / Downside", display["upside_pct"],
                       delta=f"{'Undervalued' if upside > 0 else 'Overvalued'}")
        with m3:
            st.metric("Enterprise Value", display["enterprise_value"])
        with m4:
            st.metric("WACC", f"{assumptions['wacc']*100:.1f}%")

        # Projected FCF table
        with st.expander("Projected Free Cash Flows", expanded=False):
            import pandas as pd
            fcf_df = pd.DataFrame({
                "Year": result["year_labels"],
                "Projected FCF (SAR M)": [f"{v/1e6:,.0f}" for v in result["projected_fcf"]],
            })
            st.dataframe(fcf_df, use_container_width=True, hide_index=True)

        # Sensitivity table
        with st.expander("Sensitivity Analysis (WACC vs Terminal Growth)", expanded=False):
            sens = model.sensitivity_table(assumptions)
            sens_df = pd.DataFrame(
                [[f"{v:,.1f}" if v and v > 0 else "N/A" for v in row] for row in sens["matrix"]],
                index=[f"{w*100:.1f}%" for w in sens["wacc_values"]],
                columns=[f"{g*100:.1f}%" for g in sens["terminal_values"]],
            )
            st.dataframe(sens_df, use_container_width=True)

        # Scenario analysis
        with st.expander("Scenario Analysis", expanded=False):
            scenarios = model.scenario_analysis(assumptions)
            s1, s2, s3 = st.columns(3)
            for col, (label, color) in zip(
                [s1, s2, s3],
                [("bull", C_GREEN), ("base", C_ACCENT), ("bear", C_RED)]
            ):
                with col:
                    sc = scenarios[label]
                    sc_display = format_dcf_for_display(sc)
                    st.markdown(
                        f'<div style="{_glass_card_style("16px")};border-left:3px solid {color};">'
                        f'<div style="font-size:0.75rem;font-weight:700;color:{color};'
                        f'text-transform:uppercase;margin-bottom:6px;">{label.title()} Case</div>'
                        f'<div style="font-size:1.1rem;font-weight:700;color:{C_TEXT};">'
                        f'{sc_display["implied_price"]}</div>'
                        f'<div style="font-size:0.75rem;color:{C_TEXT2};">'
                        f'{sc_display["upside_pct"]} vs current</div></div>',
                        unsafe_allow_html=True
                    )

    except Exception as e:
        st.warning(f"DCF model error: {str(e)}")


def _handle_user_prompt(prompt: str):
    """Process user input and route to the appropriate analysis pipeline."""
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if not api_key or api_key == "your_api_key_here":
        with st.chat_message("assistant"):
            st.error("API key not configured. Please update the .env file.")
            st.session_state.messages.append({
                "role": "assistant",
                "content": "API key not configured. Please update the .env file."
            })
        return

    # Portfolio analysis
    is_portfolio = any(kw in prompt.lower() for kw in [
        "portfolio", "my positions", "my holdings", "my stocks",
    ])
    if is_portfolio and get_positions():
        st.session_state.current_page = "portfolio"
        st.rerun()
        return

    # Sector analysis
    sector_key = detect_sector_request(prompt)
    if sector_key:
        with st.chat_message("assistant"):
            st.markdown(f"Running **{SAUDI_SECTORS[sector_key]['name']}** overview...")
            try:
                result = run_sector_analysis(sector_key, prompt)
                analysis = result.get("analysis", "")
                if analysis:
                    st.markdown("---")
                    st.markdown(f"#### {result['name']}")
                    st.markdown(analysis[:4000])
                _display_sources(result.get("sources"))
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"{result['name']} analysis complete.\n\n{analysis[:500]}"
                })
            except Exception as e:
                error_msg = f"Sector analysis error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
        return

    # Multi-stock comparison
    multi_stocks = extract_multiple_tickers(prompt)
    if multi_stocks:
        with st.chat_message("assistant"):
            stock_labels = ", ".join(f"**{name}** `{ticker}`" for ticker, name in multi_stocks)
            st.markdown(f"Running comparative analysis: {stock_labels}")
            try:
                results = run_comparison_analysis(multi_stocks, prompt, output_format)
                analysis = results.get("analysis", "")
                if analysis:
                    st.markdown("---")
                    st.markdown("#### Comparative Analysis")
                    st.markdown(analysis[:4000])

                for ticker_key, stock_info in results.get("stocks", {}).items():
                    if stock_info.get("charts"):
                        st.markdown("---")
                        st.markdown(f"##### {stock_info['name']} Charts")
                        chart_cols = st.columns(min(len(stock_info["charts"]), 2))
                        for i, (name, path) in enumerate(stock_info["charts"].items()):
                            if os.path.exists(path):
                                with chart_cols[i % 2]:
                                    st.image(path, caption=name.replace("_", " ").title())

                _display_download_buttons(results.get("files", {}), "cmp")
                _display_sources(results.get("sources"))

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Comparison complete: {stock_labels}\n\n{analysis[:500]}",
                    "files": results.get("files", {})
                })
            except Exception as e:
                error_msg = f"Comparison error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
        return

    # Single stock or general question
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
        # --- Pre-analysis preferences check ---
        if st.session_state.show_preferences:
            with st.chat_message("assistant"):
                confirmed = _render_preferences_panel()
                if not confirmed:
                    return
                # Fall through to run analysis with preferences applied

        # Run analysis
        with st.chat_message("assistant"):
            st.markdown(f"Initiating analysis for **{company_name or ticker}** `{ticker}`")

            # Inject preferences into prompt if customized
            prefs = st.session_state.analysis_preferences
            pref_context = ""
            if prefs.get("horizon") and prefs["horizon"] != "Medium-term (6-12 months)":
                pref_context += f" Focus on {prefs['horizon'].lower()} perspective."
            if prefs.get("focus") and "Full Analysis" not in prefs["focus"]:
                pref_context += f" Emphasize: {', '.join(prefs['focus'])}."
            enhanced_prompt = prompt + pref_context if pref_context else prompt

            try:
                results = run_full_analysis(ticker, company_name or ticker, enhanced_prompt, output_format)

                # Handle cancellation
                if results.get("cancelled") and not results["sections"]:
                    st.warning("Research cancelled. No sections were completed.")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"Research cancelled for {company_name} ({ticker})."
                    })
                    return

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

                # --- Interactive Plotly Charts ---
                _display_plotly_charts(results)

                # --- Static charts fallback ---
                if results["charts"]:
                    if not results.get("plotly_charts"):
                        st.markdown("---")
                    chart_cols = st.columns(min(len(results["charts"]), 2))
                    for i, (name, path) in enumerate(results["charts"].items()):
                        if os.path.exists(path):
                            with chart_cols[i % 2]:
                                st.image(path, caption=name.replace("_", " ").title())

                # --- DCF Valuation ---
                _display_dcf_section(results.get("stock_data", {}), ticker)

                # --- Peer Benchmarking ---
                if PEERS_AVAILABLE:
                    sector_key, sector_name = get_sector_for_ticker(ticker)
                    if sector_key:
                        with st.expander(f"Peer Comparison — {sector_name}", expanded=False):
                            with st.spinner("Loading peer data..."):
                                try:
                                    peers = get_peers(ticker)
                                    all_tickers = [(ticker, company_name)] + peers
                                    metrics_df = fetch_peer_metrics(all_tickers)
                                    if not metrics_df.empty:
                                        rankings_df = calculate_peer_rankings(metrics_df)
                                        heatmap = generate_peer_heatmap(metrics_df, rankings_df, ticker)
                                        st.plotly_chart(heatmap, use_container_width=True,
                                                        key=f"peer_heat_{ticker}")
                                        table_html = generate_peer_comparison_table(metrics_df, ticker)
                                        st.markdown(table_html, unsafe_allow_html=True)
                                except Exception as e:
                                    st.warning(f"Peer comparison error: {str(e)}")

                # --- Financial Statements ---
                if FINANCIALS_VIEWER_AVAILABLE:
                    with st.expander("Financial Statements (5-Year)", expanded=False):
                        with st.spinner("Loading financial data..."):
                            try:
                                fin_data = generate_financial_overview(ticker)
                                fin_tabs = st.tabs(["Income Statement", "Balance Sheet", "Cash Flow"])
                                for tab, key in zip(fin_tabs, ["income_html", "balance_html", "cashflow_html"]):
                                    with tab:
                                        html = fin_data.get(key, "")
                                        if html:
                                            st.markdown(html, unsafe_allow_html=True)
                                        else:
                                            st.info("Data not available for this ticker.")
                            except Exception as e:
                                st.warning(f"Financial data error: {str(e)}")

                # --- Predictive Signals ---
                if SIGNALS_AVAILABLE:
                    with st.expander("AI Predictive Signals (Experimental)", expanded=False):
                        try:
                            signals = get_all_signals(ticker)
                            badges_html = generate_signal_badges_html(signals)
                            st.markdown(badges_html, unsafe_allow_html=True)
                        except Exception as e:
                            st.warning(f"Signal generation error: {str(e)}")

                # --- Sentiment Extract & Store ---
                if SENTIMENT_AVAILABLE and not results.get("cancelled"):
                    try:
                        report_text = " ".join(
                            str(v) for v in results.get("sections", {}).values() if v
                        )
                        if report_text:
                            scores = extract_sentiment(report_text, ticker)
                            store_sentiment(ticker, scores)
                            with st.expander("Sentiment Analysis", expanded=False):
                                fig = generate_sentiment_chart(ticker)
                                if fig:
                                    st.plotly_chart(fig, use_container_width=True)
                    except Exception:
                        pass

                # --- Research Notes ---
                if NOTES_AVAILABLE:
                    with st.expander("Research Notes", expanded=False):
                        user_id = None
                        if AUTH_AVAILABLE and is_authenticated():
                            u = get_current_user()
                            if u:
                                user_id = u.get("id")
                        render_notes_panel(ticker, user_id or "default")

                _display_download_buttons(results.get("files", {}), "dl")
                _display_sources(results.get("sources"))

                # --- Activity & Audit Logging ---
                if ACTIVITY_AVAILABLE:
                    try:
                        uid = None
                        if AUTH_AVAILABLE and is_authenticated():
                            u = get_current_user()
                            if u:
                                uid = u.get("id")
                        track_activity(uid, "analyze", ticker=ticker)
                    except Exception:
                        pass
                if AUDIT_AVAILABLE:
                    try:
                        uid = None
                        if AUTH_AVAILABLE and is_authenticated():
                            u = get_current_user()
                            if u:
                                uid = u.get("id")
                        log_audit(uid, "report_generate", resource_type="report", details={"ticker": ticker})
                    except Exception:
                        pass

                cancelled_tag = " (partial — stopped early)" if results.get("cancelled") else ""
                summary_text = f"Analysis complete for **{company_name}** ({ticker}){cancelled_tag}.\n\n"
                if exec_summary:
                    summary_text += exec_summary[:500]

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": summary_text,
                    "files": results.get("files", {})
                })

            except anthropic.RateLimitError:
                error_msg = "The AI API is temporarily busy. Please wait 30 seconds and try again."
                st.warning(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
            except Exception as e:
                err_str = str(e)
                if "rate" in err_str.lower() or "429" in err_str or "Too Many" in err_str:
                    error_msg = "The AI API is temporarily busy. Please wait 30 seconds and try again."
                else:
                    error_msg = f"Error during analysis: {err_str}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})


# ==========================================================
# ALERTS PAGE
# ==========================================================
def render_alerts():
    """Centralized alert management page."""
    _render_branded_header("Alerts", "Monitor and manage your alert rules")

    if ALERT_RULES_AVAILABLE:
        tab_names = ["Alert Rules", "Alert History"]
        if SCHEDULES_AVAILABLE:
            tab_names.append("Scheduled Reports")
        all_tabs = st.tabs(tab_names)
        rules_tab = all_tabs[0]
        history_tab = all_tabs[1]
        schedule_tab = all_tabs[2] if SCHEDULES_AVAILABLE else None
        with rules_tab:
            render_alert_rules_panel()
        with history_tab:
            recent = get_recent_alerts(limit=50)
            if recent:
                for alert in recent:
                    sev_color = {"major": C_RED, "moderate": C_ORANGE}.get(
                        alert.get("severity"), C_ACCENT2
                    )
                    st.markdown(
                        f'<div style="{_glass_card_style("12px")}border-left:3px solid {sev_color};">'
                        f'<span style="color:{C_TEXT};font-weight:500;">{alert["message"]}</span>'
                        f'<br/><span style="font-size:0.7rem;color:{C_MUTED};">'
                        f'{alert.get("display_time", "")}</span></div>',
                        unsafe_allow_html=True
                    )
            else:
                st.info("No alerts yet. Configure alert rules to start monitoring.")
        if schedule_tab:
            with schedule_tab:
                user_id = "default"
                if AUTH_AVAILABLE and is_authenticated():
                    u = get_current_user()
                    if u:
                        user_id = u.get("id", "default")
                render_schedule_panel(user_id)
    else:
        st.info("Alert rules module not available. Check dependencies.")


# ==========================================================
# PAGE ROUTER
# ==========================================================

page = st.session_state.current_page

# Landing page gate: show landing on first visit
if LANDING_AVAILABLE and st.session_state.get("show_landing", True):
    render_landing_page()
# Auth gate: disabled for now — will re-enable once email verification is working
# elif AUTH_AVAILABLE and not is_authenticated():
#     render_login_page()
else:
    if page == "dashboard":
        render_dashboard()
    elif page == "research":
        render_research()
    elif page == "portfolio":
        render_portfolio()
    elif page == "sectors":
        render_sectors()
    elif page == "comparison":
        render_comparison()
    elif page == "watchlist":
        render_watchlist()
    elif page == "alerts":
        render_alerts()
    elif page == "admin":
        if ADMIN_AVAILABLE:
            render_admin()
        else:
            st.warning("Admin panel not available.")
    else:
        render_dashboard()
