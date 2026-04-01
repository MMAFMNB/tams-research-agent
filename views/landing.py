"""TAM Capital Research Terminal — Native Streamlit Landing Page.

All CTA buttons use native st.button() so they work reliably.
No iframe needed.
"""

import streamlit as st
import base64
import os


# TAM Brand colors — Light theme
C_DEEP = "#222F62"
C_ACCENT = "#1A6DB6"
C_TURQUOISE = "#6CB9B6"
C_GREEN = "#16A34A"
C_BG = "#F8FAFC"
C_CARD = "#FFFFFF"
C_TEXT = "#0F172A"
C_TEXT2 = "#475569"
C_MUTED = "#94A3B8"
C_BORDER = "#E2E8F0"


def _get_logo_b64():
    logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "tams_logo.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""


def render_landing_page():
    """Render a clean, professional landing page with native Streamlit components."""

    logo_b64 = _get_logo_b64()

    # Full-width light styling
    st.markdown(f"""<style>
        #MainMenu, header[data-testid="stHeader"], footer,
        .stDeployButton, div[data-testid="stToolbar"] {{display:none!important;}}
        section[data-testid="stSidebar"] {{display:none!important;}}
        .block-container {{max-width:1100px!important; padding-top:1rem!important;}}
        .stApp {{background: {C_BG} !important;}}

        .stButton > button[kind="primary"] {{
            background: linear-gradient(135deg, {C_ACCENT}, {C_TURQUOISE}) !important;
            border: none !important;
            color: white !important;
            padding: 0.7rem 2.5rem !important;
            font-size: 1.05rem !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
            transition: all 0.2s ease !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
        }}
        .stButton > button[kind="primary"]:hover {{
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 12px rgba(26,109,182,0.25) !important;
        }}
        .stButton > button[kind="secondary"] {{
            background: {C_CARD} !important;
            border: 1px solid {C_BORDER} !important;
            color: {C_TEXT} !important;
            padding: 0.6rem 2rem !important;
            font-size: 0.95rem !important;
            font-weight: 500 !important;
            border-radius: 8px !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
        }}
        .stButton > button[kind="secondary"]:hover {{
            background: {C_BG} !important;
            border-color: #CBD5E1 !important;
        }}
        div[data-testid="stVerticalBlock"] > div {{
            gap: 0.3rem;
        }}
    </style>""", unsafe_allow_html=True)

    # ===== NAVBAR =====
    nav_cols = st.columns([3, 1, 1, 1, 2])
    with nav_cols[0]:
        if logo_b64:
            st.markdown(
                f'<img src="data:image/png;base64,{logo_b64}" height="44" '
                f'style="opacity:0.9;margin-top:8px;" />',
                unsafe_allow_html=True
            )
        else:
            st.markdown(f"<h3 style='color:{C_TEXT};margin:0;'>TAM CAPITAL</h3>", unsafe_allow_html=True)
    with nav_cols[1]:
        st.markdown(f"<p style='color:{C_TEXT2};text-align:center;padding-top:14px;font-size:0.9rem;'>Features</p>", unsafe_allow_html=True)
    with nav_cols[2]:
        st.markdown(f"<p style='color:{C_TEXT2};text-align:center;padding-top:14px;font-size:0.9rem;'>About</p>", unsafe_allow_html=True)
    with nav_cols[4]:
        if st.button("Get Started", type="primary", key="nav_cta"):
            st.session_state.show_landing = False
            st.rerun()

    st.markdown("<div style='height:2rem;'></div>", unsafe_allow_html=True)

    # ===== HERO SECTION =====
    st.markdown(f"""
    <div style="text-align:center; padding: 3rem 0 1rem 0;">
        <h1 style="font-size:3.2rem; font-weight:800; color:{C_TEXT}; line-height:1.15; margin-bottom:1rem;">
            Invest Smarter.<br/>
            Research for <span style="color:{C_TURQUOISE}; font-style:italic; font-family:Georgia,serif;">Saudi Markets</span>
        </h1>
        <p style="font-size:1.15rem; color:{C_TEXT2}; max-width:600px; margin:0 auto 0.5rem auto; line-height:1.6;">
            Institutional-grade research and AI-powered insights for Saudi Arabia's fastest-growing investors.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # CTA buttons row
    _, btn_col1, btn_col2, _ = st.columns([2, 1.3, 1.3, 2])
    with btn_col1:
        if st.button("Start Research", type="primary", key="hero_cta", use_container_width=True):
            st.session_state.show_landing = False
            st.rerun()
    with btn_col2:
        if st.button("Learn More", type="secondary", key="hero_learn", use_container_width=True):
            pass  # Scrolls to features section (no-op for now)

    # Built by TAM
    st.markdown(f"""
    <div style="text-align:center; padding-top:1.5rem;">
        <span style="color:{C_TEXT2}; font-size:0.85rem;">Built by TAM Capital</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:3rem;'></div>", unsafe_allow_html=True)

    # ===== FEATURES SECTION =====
    st.markdown(f"""
    <div style="text-align:center; margin-bottom:1.5rem;">
        <p style="color:{C_TURQUOISE}; font-size:0.8rem; font-weight:600; letter-spacing:3px; text-transform:uppercase; margin-bottom:0.3rem;">PLATFORM FEATURES</p>
        <h2 style="color:{C_TEXT}; font-size:2rem; font-weight:700;">Everything You Need</h2>
    </div>
    """, unsafe_allow_html=True)

    features = [
        ("📊", "AI Equity Analysis",
         "Goldman-style fundamentals, JPMorgan earnings analysis, Morgan Stanley technicals — all generated by Claude AI."),
        ("🌍", "Risk Intelligence",
         "Real-time news assessment, geopolitical impact scenarios, and stress testing for Saudi market events."),
        ("💼", "Portfolio Tracking",
         "Live P&L dashboard, position management, allocation metrics, and rebalancing insights."),
        ("📄", "Multi-Format Export",
         "Word, PDF, PowerPoint & Excel reports on TAM Capital branded letterhead, ready for clients."),
        ("🔒", "Enterprise Security",
         "CMA-regulated platform with role-based access control, audit logging, and encrypted credentials."),
        ("⚡", "Real-Time Data",
         "Live Tadawul prices, 5-year audited financials, dividend history, and technical indicators."),
    ]

    for i in range(0, len(features), 3):
        cols = st.columns(3)
        for j, col in enumerate(cols):
            if i + j < len(features):
                icon, title, desc = features[i + j]
                with col:
                    st.markdown(f"""
                    <div style="background:{C_CARD}; border:1px solid {C_BORDER}; border-radius:12px;
                                padding:1.5rem; min-height:180px; box-shadow:0 1px 3px rgba(0,0,0,0.06);
                                transition:all 0.2s ease;">
                        <div style="font-size:2rem; margin-bottom:0.6rem;">{icon}</div>
                        <h4 style="color:{C_TEXT}; font-size:1rem; font-weight:600; margin-bottom:0.4rem;">{title}</h4>
                        <p style="color:{C_TEXT2}; font-size:0.85rem; line-height:1.5;">{desc}</p>
                    </div>
                    """, unsafe_allow_html=True)

    st.markdown("<div style='height:3rem;'></div>", unsafe_allow_html=True)

    # ===== BOTTOM CTA SECTION =====
    st.markdown(f"""
    <div style="text-align:center; background: {C_CARD};
                border-radius:12px; padding:3rem 2rem; border:1px solid {C_BORDER};
                box-shadow:0 1px 3px rgba(0,0,0,0.06);">
        <h2 style="color:{C_TEXT}; font-size:1.8rem; font-weight:700; margin-bottom:0.5rem;">
            Ready to Transform Your Research?
        </h2>
        <p style="color:{C_TEXT2}; font-size:1rem; margin-bottom:0.3rem;">
            AI-powered investment research built for the Saudi market.
        </p>
    </div>
    """, unsafe_allow_html=True)

    _, cta_col, _ = st.columns([3, 2, 3])
    with cta_col:
        if st.button("Get Started Free", type="primary", key="bottom_cta", use_container_width=True):
            st.session_state.show_landing = False
            st.rerun()

    # ===== FOOTER =====
    st.markdown(f"""
    <div style="text-align:center; padding:3rem 0 1rem 0; margin-top:2rem;
                border-top:1px solid {C_BORDER};">
        <p style="color:{C_TEXT2}; font-size:0.8rem;">
            © 2026 TAM Capital. All rights reserved. | CMA Regulated
        </p>
    </div>
    """, unsafe_allow_html=True)
