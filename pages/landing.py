"""TAM Capital Research Terminal — Landing Page.

A premium marketing-style landing page inspired by tamcapital.sa,
featuring hero section with animated gradient mesh, feature cards,
stats counters, CMA badge, and a clear CTA to enter the terminal.
"""

import streamlit as st
import base64
import os


def _get_logo_b64():
    """Get TAM logo as base64."""
    logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "tam_logo.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""


def render_landing_page():
    """Render the full landing page with hero, features, stats, and CTA."""

    logo_b64 = _get_logo_b64()
    logo_img = (
        f'<img src="data:image/png;base64,{logo_b64}" height="52" '
        f'style="filter:brightness(0) invert(1);opacity:0.95;" />'
        if logo_b64
        else '<span style="font-size:1.6rem;font-weight:800;letter-spacing:-0.03em;">TAM CAPITAL</span>'
    )

    # Hide Streamlit default elements for clean landing page
    st.markdown(
        """
        <style>
        /* Hide Streamlit header/footer for landing page */
        #MainMenu {visibility: hidden;}
        header[data-testid="stHeader"] {display: none !important;}
        footer {display: none !important;}
        .stDeployButton {display: none !important;}
        div[data-testid="stToolbar"] {display: none !important;}
        section[data-testid="stSidebar"] {display: none !important;}
        .block-container {padding-top: 0 !important; max-width: 100% !important;}

        /* ===== LANDING PAGE STYLES ===== */

        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

        .landing-root {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            color: #E6EDF3;
            overflow-x: hidden;
        }

        /* --- Animated Gradient Mesh Background --- */
        .hero-section {
            position: relative;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 60px 24px;
            background: linear-gradient(135deg, #070B14 0%, #0E1A2E 30%, #1A2B55 60%, #222F62 100%);
            overflow: hidden;
        }

        .hero-section::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(ellipse at 20% 50%, rgba(26, 109, 182, 0.15) 0%, transparent 50%),
                        radial-gradient(ellipse at 80% 20%, rgba(108, 185, 182, 0.12) 0%, transparent 40%),
                        radial-gradient(ellipse at 50% 80%, rgba(34, 47, 98, 0.20) 0%, transparent 50%);
            animation: meshFloat 20s ease-in-out infinite;
            pointer-events: none;
        }

        @keyframes meshFloat {
            0%, 100% { transform: translate(0, 0) rotate(0deg); }
            25% { transform: translate(2%, -3%) rotate(1deg); }
            50% { transform: translate(-1%, 2%) rotate(-0.5deg); }
            75% { transform: translate(-2%, -1%) rotate(0.5deg); }
        }

        /* Glowing orb effects */
        .hero-orb {
            position: absolute;
            border-radius: 50%;
            filter: blur(80px);
            opacity: 0.4;
            pointer-events: none;
            animation: orbPulse 8s ease-in-out infinite;
        }
        .hero-orb-1 {
            width: 400px; height: 400px;
            background: radial-gradient(circle, #1A6DB6, transparent);
            top: 10%; right: 10%;
            animation-delay: 0s;
        }
        .hero-orb-2 {
            width: 300px; height: 300px;
            background: radial-gradient(circle, #6CB9B6, transparent);
            bottom: 15%; left: 5%;
            animation-delay: 3s;
        }
        .hero-orb-3 {
            width: 250px; height: 250px;
            background: radial-gradient(circle, #22C55E, transparent);
            top: 50%; left: 45%;
            animation-delay: 5s;
            opacity: 0.2;
        }

        @keyframes orbPulse {
            0%, 100% { transform: scale(1); opacity: 0.3; }
            50% { transform: scale(1.15); opacity: 0.5; }
        }

        /* Hero content */
        .hero-content {
            position: relative;
            z-index: 2;
            max-width: 900px;
        }

        .hero-logo {
            margin-bottom: 32px;
            opacity: 0;
            animation: fadeSlideUp 0.8s ease forwards;
        }

        .hero-badge {
            display: inline-block;
            padding: 6px 18px;
            background: rgba(108, 185, 182, 0.12);
            border: 1px solid rgba(108, 185, 182, 0.25);
            border-radius: 100px;
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.15em;
            text-transform: uppercase;
            color: #6CB9B6;
            margin-bottom: 28px;
            opacity: 0;
            animation: fadeSlideUp 0.8s ease 0.15s forwards;
        }

        .hero-title {
            font-size: clamp(2.2rem, 5vw, 3.8rem);
            font-weight: 900;
            letter-spacing: -0.04em;
            line-height: 1.1;
            margin-bottom: 20px;
            opacity: 0;
            animation: fadeSlideUp 0.8s ease 0.3s forwards;
        }

        .hero-title .gradient-text {
            background: linear-gradient(135deg, #5B9BD5 0%, #6CB9B6 50%, #22C55E 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .hero-subtitle {
            font-size: clamp(1rem, 2vw, 1.25rem);
            color: #8B949E;
            max-width: 640px;
            margin: 0 auto 40px;
            line-height: 1.65;
            font-weight: 400;
            opacity: 0;
            animation: fadeSlideUp 0.8s ease 0.45s forwards;
        }

        .hero-cta-group {
            display: flex;
            gap: 16px;
            justify-content: center;
            flex-wrap: wrap;
            opacity: 0;
            animation: fadeSlideUp 0.8s ease 0.6s forwards;
        }

        .cta-primary {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            padding: 16px 36px;
            background: linear-gradient(135deg, #1A6DB6 0%, #6CB9B6 100%);
            color: white;
            font-weight: 700;
            font-size: 1rem;
            border-radius: 14px;
            text-decoration: none;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 8px 32px rgba(26, 109, 182, 0.3);
            cursor: pointer;
            border: none;
        }
        .cta-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 40px rgba(26, 109, 182, 0.45);
        }

        .cta-secondary {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            padding: 16px 36px;
            background: rgba(34, 47, 98, 0.25);
            backdrop-filter: blur(12px);
            color: #E6EDF3;
            font-weight: 600;
            font-size: 1rem;
            border-radius: 14px;
            border: 1px solid rgba(108, 185, 182, 0.15);
            text-decoration: none;
            transition: all 0.3s ease;
            cursor: pointer;
        }
        .cta-secondary:hover {
            background: rgba(34, 47, 98, 0.40);
            border-color: rgba(108, 185, 182, 0.30);
        }

        @keyframes fadeSlideUp {
            from { opacity: 0; transform: translateY(24px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* --- Stats Bar --- */
        .stats-bar {
            display: flex;
            justify-content: center;
            gap: 48px;
            flex-wrap: wrap;
            margin-top: 64px;
            padding-top: 40px;
            border-top: 1px solid rgba(108, 185, 182, 0.08);
            opacity: 0;
            animation: fadeSlideUp 0.8s ease 0.75s forwards;
        }

        .stat-item {
            text-align: center;
        }
        .stat-value {
            font-size: 1.8rem;
            font-weight: 800;
            background: linear-gradient(135deg, #5B9BD5, #6CB9B6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.03em;
        }
        .stat-label {
            font-size: 0.72rem;
            color: #4A5568;
            text-transform: uppercase;
            letter-spacing: 0.15em;
            font-weight: 600;
            margin-top: 4px;
        }

        /* --- Features Section --- */
        .features-section {
            background: #070B14;
            padding: 100px 24px;
        }

        .section-header {
            text-align: center;
            max-width: 700px;
            margin: 0 auto 64px;
        }
        .section-eyebrow {
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.2em;
            text-transform: uppercase;
            color: #6CB9B6;
            margin-bottom: 12px;
        }
        .section-title {
            font-size: clamp(1.6rem, 3.5vw, 2.4rem);
            font-weight: 800;
            letter-spacing: -0.03em;
            margin-bottom: 16px;
        }
        .section-desc {
            font-size: 1rem;
            color: #8B949E;
            line-height: 1.65;
        }

        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 24px;
            max-width: 1200px;
            margin: 0 auto;
        }

        .feature-card {
            background: rgba(26, 38, 78, 0.12);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(108, 185, 182, 0.06);
            border-radius: 20px;
            padding: 32px;
            transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }
        .feature-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, transparent, #1A6DB6, #6CB9B6, transparent);
            opacity: 0;
            transition: opacity 0.35s ease;
        }
        .feature-card:hover {
            background: rgba(26, 38, 78, 0.22);
            border-color: rgba(108, 185, 182, 0.15);
            transform: translateY(-4px);
        }
        .feature-card:hover::before {
            opacity: 1;
        }

        .feature-icon {
            width: 48px;
            height: 48px;
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.4rem;
            margin-bottom: 18px;
        }
        .fi-blue { background: rgba(26, 109, 182, 0.15); }
        .fi-teal { background: rgba(108, 185, 182, 0.15); }
        .fi-green { background: rgba(34, 197, 94, 0.15); }
        .fi-purple { background: rgba(139, 92, 246, 0.15); }

        .feature-title {
            font-size: 1.05rem;
            font-weight: 700;
            margin-bottom: 8px;
            letter-spacing: -0.01em;
        }
        .feature-desc {
            font-size: 0.88rem;
            color: #8B949E;
            line-height: 1.6;
        }

        /* --- CMA Section --- */
        .cma-section {
            background: linear-gradient(135deg, #0E1A2E 0%, #1A2B55 50%, #222F62 100%);
            padding: 80px 24px;
            text-align: center;
        }

        .cma-badge {
            width: 72px;
            height: 72px;
            background: linear-gradient(135deg, #22C55E, #16A34A);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 24px;
            font-size: 2rem;
            box-shadow: 0 8px 32px rgba(34, 197, 94, 0.25);
        }

        .cma-title {
            font-size: 1.6rem;
            font-weight: 800;
            margin-bottom: 16px;
        }
        .cma-text {
            color: #8B949E;
            max-width: 700px;
            margin: 0 auto;
            line-height: 1.7;
            font-size: 0.95rem;
        }

        /* --- Final CTA Section --- */
        .final-cta {
            background: #070B14;
            padding: 100px 24px;
            text-align: center;
        }

        .final-cta-title {
            font-size: clamp(1.8rem, 4vw, 2.8rem);
            font-weight: 900;
            letter-spacing: -0.04em;
            margin-bottom: 16px;
        }
        .final-cta-desc {
            color: #8B949E;
            font-size: 1.1rem;
            margin-bottom: 40px;
        }

        /* --- Footer --- */
        .landing-footer {
            background: #05080F;
            padding: 40px 24px;
            text-align: center;
            border-top: 1px solid rgba(108, 185, 182, 0.06);
        }
        .footer-text {
            font-size: 0.75rem;
            color: #4A5568;
            line-height: 1.8;
        }
        .footer-text a {
            color: #6CB9B6;
            text-decoration: none;
        }

        /* Nav bar on top */
        .landing-nav {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 100;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 40px;
            background: rgba(7, 11, 20, 0.7);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid rgba(108, 185, 182, 0.06);
        }
        .nav-logo img {
            height: 36px;
            filter: brightness(0) invert(1);
            opacity: 0.9;
        }
        .nav-links {
            display: flex;
            gap: 32px;
            align-items: center;
        }
        .nav-links a {
            color: #8B949E;
            text-decoration: none;
            font-size: 0.85rem;
            font-weight: 500;
            transition: color 0.2s;
        }
        .nav-links a:hover {
            color: #E6EDF3;
        }

        /* Scroll animation triggers */
        .scroll-reveal {
            opacity: 0;
            transform: translateY(30px);
            transition: all 0.6s ease;
        }
        .scroll-reveal.visible {
            opacity: 1;
            transform: translateY(0);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # The full landing page as a single HTML block
    st.markdown(
        f"""
        <div class="landing-root">

            <!-- ===== HERO SECTION ===== -->
            <div class="hero-section">
                <div class="hero-orb hero-orb-1"></div>
                <div class="hero-orb hero-orb-2"></div>
                <div class="hero-orb hero-orb-3"></div>

                <div class="hero-content">
                    <div class="hero-logo">{logo_img}</div>
                    <div class="hero-badge">CMA Licensed &bull; AI-Powered Research</div>
                    <h1 class="hero-title">
                        Invest Smarter.<br/>
                        <span class="gradient-text">Research with Purpose.</span>
                    </h1>
                    <p class="hero-subtitle">
                        Institutional-grade equity research for the Saudi market.
                        Powered by AI, built for TAM Capital analysts.
                        Goldman-style reports in seconds, not days.
                    </p>

                    <div class="stats-bar">
                        <div class="stat-item">
                            <div class="stat-value">200+</div>
                            <div class="stat-label">Tadawul Tickers</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">8</div>
                            <div class="stat-label">Sector Coverage</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">5yr</div>
                            <div class="stat-label">Financial History</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">&lt;60s</div>
                            <div class="stat-label">Full Report Time</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- ===== FEATURES SECTION ===== -->
            <div class="features-section">
                <div class="section-header">
                    <div class="section-eyebrow">Platform Capabilities</div>
                    <h2 class="section-title">Everything You Need for<br/>Saudi Market Research</h2>
                    <p class="section-desc">
                        From fundamental analysis to AI-driven signals &mdash;
                        a complete toolkit for the modern investment professional.
                    </p>
                </div>

                <div class="features-grid">
                    <div class="feature-card">
                        <div class="feature-icon fi-blue">\U0001F4CA</div>
                        <div class="feature-title">Deep Equity Analysis</div>
                        <div class="feature-desc">
                            Fundamental, technical, and earnings analysis modeled after
                            Goldman Sachs, JPMorgan, and Morgan Stanley research frameworks.
                        </div>
                    </div>
                    <div class="feature-card">
                        <div class="feature-icon fi-teal">\U0001F4C8</div>
                        <div class="feature-title">Interactive Charts</div>
                        <div class="feature-desc">
                            Plotly-powered candlestick, RSI, MACD, and multi-ticker
                            comparison charts with real-time Tadawul data.
                        </div>
                    </div>
                    <div class="feature-card">
                        <div class="feature-icon fi-green">\U0001F4B0</div>
                        <div class="feature-title">DCF Valuation Engine</div>
                        <div class="feature-desc">
                            Built-in discounted cash flow model with sensitivity analysis,
                            scenario testing, and Saudi-specific WACC assumptions.
                        </div>
                    </div>
                    <div class="feature-card">
                        <div class="feature-icon fi-purple">\U0001F916</div>
                        <div class="feature-title">AI Morning Brief</div>
                        <div class="feature-desc">
                            Daily AI-generated market briefing covering your watchlist
                            with news impact assessment and actionable insights.
                        </div>
                    </div>
                    <div class="feature-card">
                        <div class="feature-icon fi-blue">\U0001F6E1</div>
                        <div class="feature-title">Portfolio Risk Analytics</div>
                        <div class="feature-desc">
                            Value-at-Risk, Sharpe ratio, max drawdown, and correlation
                            matrix for your Saudi equity portfolio.
                        </div>
                    </div>
                    <div class="feature-card">
                        <div class="feature-icon fi-teal">\U0001F3AF</div>
                        <div class="feature-title">Peer Benchmarking</div>
                        <div class="feature-desc">
                            Compare any stock against sector peers across 16 financial
                            metrics with quartile heatmaps spanning 8 Tadawul sectors.
                        </div>
                    </div>
                    <div class="feature-card">
                        <div class="feature-icon fi-green">\U0001F514</div>
                        <div class="feature-title">Smart Alert Engine</div>
                        <div class="feature-desc">
                            Custom alert rules for price targets, volume spikes,
                            technical signals, and news keywords with real-time monitoring.
                        </div>
                    </div>
                    <div class="feature-card">
                        <div class="feature-icon fi-purple">\U0001F4C4</div>
                        <div class="feature-title">Multi-Format Export</div>
                        <div class="feature-desc">
                            Export TAM-branded research reports as Word, PDF, PowerPoint,
                            or Excel with professional formatting and letterhead.
                        </div>
                    </div>
                </div>
            </div>

            <!-- ===== CMA SECTION ===== -->
            <div class="cma-section">
                <div class="cma-badge">\u2713</div>
                <h2 class="cma-title">Licensed by the Capital Market Authority</h2>
                <p class="cma-text">
                    TAM Capital is a Saudi closed joint-stock company licensed by the
                    Capital Market Authority (CMA) of the Kingdom of Saudi Arabia.
                    License No. 12-24297. Investment management, fund operation, and
                    arrangement in securities business.
                </p>
            </div>

            <!-- ===== FINAL CTA ===== -->
            <div class="final-cta">
                <h2 class="final-cta-title">Ready to Transform Your Research?</h2>
                <p class="final-cta-desc">
                    Enter the terminal and start generating institutional-grade analysis.
                </p>
            </div>

            <!-- ===== FOOTER ===== -->
            <div class="landing-footer">
                <p class="footer-text">
                    &copy; 2025 TAM Capital. All rights reserved.
                    CMA License No. 12-24297<br/>
                    <a href="https://tamcapital.sa">tamcapital.sa</a>
                    &nbsp;&bull;&nbsp;
                    Riyadh, Kingdom of Saudi Arabia
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Streamlit button to enter the terminal (placed after the HTML)
    st.markdown("")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            "Launch Research Terminal  \u2192",
            key="enter_terminal_btn",
            use_container_width=True,
            type="primary",
        ):
            st.session_state.show_landing = False
            st.rerun()
