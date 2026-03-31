"""TAM Capital Research Terminal — World-Class Landing Page.

Inspired by Cirform AI Finance aesthetic:
- Electric light streak hero animations (diagonal fiber optic rays)
- Floating glass revenue card with market data
- Serif accent typography (Playfair Display)
- Animated scroll indicator
- Avatar group showcase
- Interactive particle constellation canvas
- Live TASI ticker ribbon
- Parallax scroll sections with intersection observer
- Animated counter stats
- 3D tilt feature cards with glow
- Bilingual AR/EN toggle
- Interactive mini chart demo (canvas)
- Smooth scroll reveal animations
"""

import streamlit as st
import base64
import os


def _get_logo_b64():
    logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "tams_logo.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""


def render_landing_page():
    """Render the full animated landing page with Cirform design."""

    logo_b64 = _get_logo_b64()
    logo_src = f"data:image/png;base64,{logo_b64}" if logo_b64 else ""

    # Hide Streamlit chrome for immersive experience
    st.markdown(
        """<style>
        #MainMenu, header[data-testid="stHeader"], footer,
        .stDeployButton, div[data-testid="stToolbar"],
        section[data-testid="stSidebar"] { display:none!important; }
        .block-container { padding:0!important; max-width:100%!important; }
        .stMainBlockContainer { padding:0!important; }
        iframe { border: none; }
        </style>""",
        unsafe_allow_html=True,
    )

    html = f'''<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Playfair+Display:ital@1&display=swap" rel="stylesheet"/>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
html{{scroll-behavior:smooth;overflow-x:hidden;}}
body{{
  font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;
  background:#050810;color:#E6EDF3;overflow-x:hidden;
  -webkit-font-smoothing:antialiased;
}}
/* RTL support */
[dir="rtl"] body {{ direction: rtl; text-align: right; }}
[dir="rtl"] .nav-links {{ flex-direction: row-reverse; }}
[dir="rtl"] .feature-card {{ text-align: right; }}
[dir="rtl"] .stat-item {{ text-align: center; }}

/* ===== NAVIGATION ===== */
.nav{{
  position:fixed;top:0;left:0;right:0;z-index:1000;
  display:flex;justify-content:space-between;align-items:center;
  padding:18px 48px;
  background:rgba(5,8,16,0.4);
  backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);
  border-bottom:1px solid rgba(108,185,182,0.06);
  transition:all 0.4s cubic-bezier(0.4,0,0.2,1);
}}
.nav.scrolled{{
  padding:12px 48px;
  background:rgba(5,8,16,0.85);
  box-shadow:0 8px 32px rgba(0,0,0,0.4);
}}
.nav-logo img{{height:32px;filter:brightness(0) invert(1);opacity:0.92;transition:all 0.3s;}}
.nav-logo span{{font-size:1.3rem;font-weight:800;letter-spacing:-0.03em;color:#fff;}}
.nav-links{{display:flex;gap:28px;align-items:center;}}
.nav-links a{{
  color:rgba(230,237,243,0.6);text-decoration:none;font-size:0.82rem;
  font-weight:500;letter-spacing:0.02em;transition:all 0.25s;position:relative;
}}
.nav-links a:hover{{color:#E6EDF3;}}
.nav-links a::after{{
  content:'';position:absolute;bottom:-4px;left:0;width:0;height:1.5px;
  background:linear-gradient(90deg,#1A6DB6,#6CB9B6);transition:width 0.3s;
}}
.nav-links a:hover::after{{width:100%;}}
.nav-cta{{
  padding:10px 24px;background:linear-gradient(135deg,#1A6DB6,#6CB9B6);
  color:#fff;font-weight:700;font-size:0.82rem;border-radius:12px;
  border:none;cursor:pointer;transition:all 0.3s;letter-spacing:0.01em;
}}
.nav-cta:hover{{transform:translateY(-1px);box-shadow:0 6px 24px rgba(26,109,182,0.4);}}
.lang-toggle{{
  padding:6px 14px;background:rgba(108,185,182,0.08);border:1px solid rgba(108,185,182,0.15);
  border-radius:8px;color:#6CB9B6;font-size:0.75rem;font-weight:600;cursor:pointer;
  transition:all 0.25s;
}}
.lang-toggle:hover{{background:rgba(108,185,182,0.18);}}

/* ===== TICKER RIBBON ===== */
.ticker-ribbon{{
  position:fixed;top:64px;left:0;right:0;z-index:999;
  background:rgba(5,8,16,0.7);backdrop-filter:blur(12px);
  border-bottom:1px solid rgba(108,185,182,0.04);
  overflow:hidden;height:32px;display:flex;align-items:center;
}}
.ticker-track{{
  display:flex;gap:48px;animation:tickerScroll 40s linear infinite;
  white-space:nowrap;
}}
@keyframes tickerScroll{{
  0%{{transform:translateX(0);}}
  100%{{transform:translateX(-50%);}}
}}
.ticker-item{{
  font-size:0.72rem;font-weight:600;letter-spacing:0.02em;
  display:flex;gap:8px;align-items:center;
}}
.ticker-symbol{{color:#8B949E;}}
.ticker-price{{color:#E6EDF3;}}
.ticker-change.up{{color:#22C55E;}}
.ticker-change.down{{color:#FF6B6B;}}

/* ===== HERO SECTION WITH LIGHT STREAKS ===== */
.hero{{
  position:relative;height:900px;width:100%;overflow:hidden;
  margin-top:96px;display:flex;flex-direction:column;justify-content:center;
  align-items:center;
}}

/* Electric Light Streaks Background */
.hero-bg{{
  position:absolute;top:0;left:0;right:0;bottom:0;
  background:#070B14;
}}

.light-streak{{
  position:absolute;opacity:0.5;
}}

.streak-1{{
  top:-20%;left:-10%;width:800px;height:20px;
  background:linear-gradient(135deg,transparent,#1A6DB6,#6CB9B6,transparent);
  transform:skewY(-45deg);
  animation:streakFlow1 6s ease-in-out infinite;
}}

.streak-2{{
  top:20%;right:-15%;width:900px;height:25px;
  background:linear-gradient(135deg,transparent,#6CB9B6,#E879F9,transparent);
  transform:skewY(-45deg);
  animation:streakFlow2 8s ease-in-out 1s infinite;
}}

.streak-3{{
  bottom:15%;left:-5%;width:1000px;height:30px;
  background:linear-gradient(135deg,transparent,#E879F9,#1A6DB6,transparent);
  transform:skewY(-45deg);
  animation:streakFlow3 7s ease-in-out 2s infinite;
}}

@keyframes streakFlow1{{
  0%{{transform:translateX(-100%) skewY(-45deg);opacity:0;}}
  50%{{opacity:0.5;}}
  100%{{transform:translateX(150vw) skewY(-45deg);opacity:0;}}
}}

@keyframes streakFlow2{{
  0%{{transform:translateX(100%) skewY(-45deg);opacity:0;}}
  50%{{opacity:0.5;}}
  100%{{transform:translateX(-50vw) skewY(-45deg);opacity:0;}}
}}

@keyframes streakFlow3{{
  0%{{transform:translateX(-150%) skewY(-45deg);opacity:0;}}
  50%{{opacity:0.5;}}
  100%{{transform:translateX(100vw) skewY(-45deg);opacity:0;}}
}}

/* Revenue Card - Floating Glass */
.revenue-card{{
  position:absolute;top:60px;right:40px;
  background:rgba(26,109,182,0.08);backdrop-filter:blur(12px);
  border:1px solid rgba(108,185,182,0.15);
  padding:24px;border-radius:20px;
  width:280px;animation:floatCard 4s ease-in-out infinite;
  z-index:10;
}}

@keyframes floatCard{{
  0%,100%{{transform:translateY(0px);}}
  50%{{transform:translateY(-15px);}}
}}

.revenue-label{{
  font-size:0.75rem;color:#8B949E;font-weight:600;letter-spacing:0.05em;
  text-transform:uppercase;margin-bottom:8px;
}}

.revenue-value{{
  font-size:2.4rem;font-weight:900;color:#E6EDF3;letter-spacing:-0.02em;
  margin-bottom:6px;
}}

.revenue-change{{
  color:#22C55E;font-size:1rem;font-weight:700;margin-bottom:12px;
  display:flex;align-items:center;gap:4px;
}}

.revenue-subtitle{{
  font-size:0.7rem;color:#4A5568;font-weight:500;
}}

/* Hero Content */
.hero-content{{
  position:relative;z-index:5;text-align:center;max-width:900px;padding:0 40px;
}}

.hero-title{{
  font-size:clamp(3rem,6vw,5rem);font-weight:900;line-height:1.15;
  letter-spacing:-0.02em;margin-bottom:20px;color:#E6EDF3;
}}

.hero-title-accent{{
  font-family:'Playfair Display',serif;font-style:italic;
  color:#6CB9B6;font-size:inherit;font-weight:400;
}}

.hero-subtitle{{
  font-size:1.3rem;color:#8B949E;font-weight:400;line-height:1.6;
  margin-bottom:40px;
}}

/* Scroll Indicator */
.scroll-indicator{{
  position:absolute;bottom:40px;left:50%;transform:translateX(-50%);
  z-index:10;display:flex;flex-direction:column;align-items:center;gap:8px;
  animation:bounce 2s ease-in-out infinite;
}}

.scroll-text{{
  font-size:0.75rem;font-weight:600;color:#6CB9B6;letter-spacing:0.05em;
  text-transform:uppercase;
}}

.scroll-arrow{{
  font-size:1.2rem;color:#6CB9B6;
}}

@keyframes bounce{{
  0%,100%{{transform:translateY(0);}}
  50%{{transform:translateY(6px);}}
}}

/* Avatar Group */
.avatar-group{{
  display:flex;align-items:center;gap:-8px;justify-content:center;
  margin-top:40px;padding:20px;
}}

.avatar{{
  width:44px;height:44px;border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  font-weight:700;font-size:0.85rem;color:#fff;
  border:2px solid #050810;margin-left:-12px;
}}

.avatar:first-child{{margin-left:0;}}

.avatar.a1{{background:linear-gradient(135deg,#1A6DB6,#6CB9B6);}}
.avatar.a2{{background:linear-gradient(135deg,#E879F9,#FF6B6B);}}
.avatar.a3{{background:linear-gradient(135deg,#22C55E,#1A6DB6);}}

.avatar-text{{
  margin-left:16px;font-size:0.85rem;color:#8B949E;font-weight:500;
}}

/* Canvas for Particle Constellation */
#particleCanvas{{
  position:absolute;top:0;left:0;width:100%;height:100%;
}}

/* ===== SECTIONS ===== */
.section{{
  position:relative;padding:100px 48px;
}}

.section-bg{{
  position:absolute;top:0;left:0;width:100%;height:100%;background:inherit;
}}

.section-content{{
  position:relative;z-index:2;max-width:1400px;margin:0 auto;
}}

/* ===== FEATURES SECTION ===== */
.features-section{{
  background:#070B14;
}}

.section-title{{
  font-size:2.8rem;font-weight:900;text-align:center;
  margin-bottom:60px;letter-spacing:-0.01em;
  color:#E6EDF3;
}}

.features-grid{{
  display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));
  gap:28px;
}}

.feature-card{{
  position:relative;padding:32px;border-radius:20px;
  background:linear-gradient(135deg,rgba(34,197,94,0.05),rgba(26,109,182,0.05));
  border:1px solid rgba(108,185,182,0.1);
  cursor:pointer;transition:all 0.4s cubic-bezier(0.4,0,0.2,1);
  overflow:hidden;
}}

.feature-card::before{{
  content:'';position:absolute;top:0;left:0;right:0;bottom:0;
  background:radial-gradient(circle at var(--mouse-x,50%) var(--mouse-y,50%),
    rgba(108,185,182,0.15) 0%,transparent 60%);
  opacity:0;transition:opacity 0.3s;pointer-events:none;
}}

.feature-card:hover{{
  border-color:rgba(108,185,182,0.3);
  transform:translateY(-4px);
}}

.feature-card:hover::before{{opacity:1;}}

.feature-icon{{
  font-size:2.8rem;margin-bottom:16px;
}}

.feature-title{{
  font-size:1.3rem;font-weight:700;margin-bottom:12px;
  color:#E6EDF3;
}}

.feature-desc{{
  font-size:0.95rem;color:#8B949E;line-height:1.6;
}}

/* ===== STATS BAR ===== */
.stats-section{{
  background:#222F62;padding:60px 48px;
}}

.stats-container{{
  max-width:1400px;margin:0 auto;
  display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
  gap:40px;text-align:center;
}}

.stat-item{{
  animation:slideUp 0.8s ease-out forwards;
}}

.stat-item:nth-child(2){{animation-delay:0.1s;}}
.stat-item:nth-child(3){{animation-delay:0.2s;}}
.stat-item:nth-child(4){{animation-delay:0.3s;}}

@keyframes slideUp{{
  from{{opacity:0;transform:translateY(20px);}}
  to{{opacity:1;transform:translateY(0);}}
}}

.stat-number{{
  font-size:2.8rem;font-weight:900;color:#22C55E;letter-spacing:-0.01em;
  margin-bottom:8px;
}}

.stat-label{{
  font-size:0.9rem;color:#A0AEC0;font-weight:500;
}}

/* ===== DEMO SECTION ===== */
.demo-section{{
  background:#050810;padding:100px 48px;
}}

.demo-container{{
  max-width:1200px;margin:0 auto;
  display:grid;grid-template-columns:1fr 1fr;gap:60px;align-items:center;
}}

.demo-content h3{{
  font-size:2.2rem;font-weight:900;margin-bottom:20px;color:#E6EDF3;
}}

.demo-content p{{
  font-size:1.05rem;color:#8B949E;line-height:1.8;margin-bottom:24px;
}}

.demo-list{{
  list-style:none;
}}

.demo-list li{{
  font-size:0.95rem;color:#A0AEC0;margin-bottom:16px;
  padding-left:28px;position:relative;
}}

.demo-list li::before{{
  content:'✓';position:absolute;left:0;color:#22C55E;font-weight:bold;
}}

#demoChart{{
  width:100%;height:300px;border-radius:12px;
  background:rgba(34,44,98,0.4);border:1px solid rgba(108,185,182,0.1);
}}

/* ===== CMA BADGE SECTION ===== */
.badge-section{{
  background:#222F62;padding:80px 48px;text-align:center;
}}

.badge-title{{
  font-size:1.8rem;font-weight:700;margin-bottom:40px;color:#E6EDF3;
}}

.badge-container{{
  display:flex;justify-content:center;gap:40px;flex-wrap:wrap;
  max-width:1200px;margin:0 auto;
}}

.badge-item{{
  display:flex;flex-direction:column;align-items:center;gap:12px;
  padding:24px;background:rgba(26,109,182,0.1);border-radius:16px;
  border:1px solid rgba(108,185,182,0.15);
}}

.badge-icon{{
  font-size:3rem;
}}

.badge-text{{
  font-size:0.95rem;font-weight:600;color:#A0AEC0;
}}

/* ===== FINAL CTA ===== */
.cta-section{{
  background:linear-gradient(135deg,#222F62,#070B14);
  padding:100px 48px;text-align:center;
}}

.cta-title{{
  font-size:2.6rem;font-weight:900;margin-bottom:20px;
  color:#E6EDF3;letter-spacing:-0.01em;
}}

.cta-subtitle{{
  font-size:1.1rem;color:#8B949E;margin-bottom:40px;
  max-width:700px;margin-left:auto;margin-right:auto;
}}

#finalCta{{
  padding:14px 40px;background:linear-gradient(135deg,#1A6DB6,#6CB9B6);
  color:#fff;font-weight:700;font-size:0.95rem;
  border:none;border-radius:12px;cursor:pointer;
  transition:all 0.3s;letter-spacing:0.01em;
}}

#finalCta:hover{{
  transform:translateY(-2px);
  box-shadow:0 12px 32px rgba(26,109,182,0.4);
}}

/* ===== FOOTER ===== */
footer{{
  background:#050810;border-top:1px solid rgba(108,185,182,0.06);
  padding:40px 48px;text-align:center;
}}

.footer-text{{
  font-size:0.85rem;color:#4A5568;line-height:1.8;
}}

.footer-links{{
  display:flex;justify-content:center;gap:24px;margin-top:16px;
  flex-wrap:wrap;
}}

.footer-links a{{
  color:#6CB9B6;text-decoration:none;font-weight:500;
  transition:color 0.25s;
}}

.footer-links a:hover{{color:#E6EDF3;}}

/* ===== SCROLL REVEAL ===== */
.reveal{{
  opacity:0;transform:translateY(20px);
  transition:opacity 0.8s ease-out,transform 0.8s ease-out;
}}

.reveal.active{{
  opacity:1;transform:translateY(0);
}}

/* ===== RESPONSIVE ===== */
@media(max-width:768px){{
  .nav{{padding:16px 24px;}}
  .nav-links{{gap:16px;}}
  .nav-links a,.nav-cta{{font-size:0.75rem;}}
  .hero{{height:600px;margin-top:96px;}}
  .hero-title{{font-size:2.2rem;}}
  .revenue-card{{width:220px;right:20px;top:40px;padding:16px;}}
  .revenue-value{{font-size:1.8rem;}}
  .demo-container{{grid-template-columns:1fr;gap:40px;}}
  .badge-container{{flex-direction:column;align-items:center;}}
  .section{{padding:60px 24px;}}
  .section-title{{font-size:2rem;}}
  .features-grid{{gap:20px;}}
  .feature-card{{padding:24px;}}
}}

@media(max-width:480px){{
  .nav{{padding:12px 16px;}}
  .nav-logo span{{font-size:1rem;}}
  .nav-links{{gap:12px;}}
  .hero{{height:500px;}}
  .hero-title{{font-size:1.6rem;}}
  .hero-subtitle{{font-size:1rem;}}
  .revenue-card{{display:none;}}
  .avatar-group{{flex-direction:column;gap:12px;}}
  .section{{padding:40px 16px;}}
  .section-title{{font-size:1.4rem;margin-bottom:32px;}}
  .demo-container{{padding:0;}}
  .cta-title{{font-size:1.6rem;}}
  .badge-container{{gap:16px;}}
}}
</style>
</head>
<body>

<!-- Navigation -->
<nav class="nav" id="navbar">
  <div class="nav-logo">
    {'<img src="' + logo_src + '" alt="TAM Capital" style="height:36px;"/>' if logo_src else '<span style="font-size:1.4rem;font-weight:700;letter-spacing:1px;color:#fff;">TAM<span style="color:#6CB9B6;">Capital</span></span>'}
  </div>
  <div class="nav-links">
    <a href="#features" data-en="Features" data-ar="المميزات">Features</a>
    <a href="#about" data-en="About" data-ar="حول">About</a>
    <a href="#demo" data-en="Demo" data-ar="عرض">Demo</a>
  </div>
  <div style="display:flex;align-items:center;gap:16px;">
    <button class="lang-toggle" onclick="toggleLang()" data-en="AR" data-ar="EN">AR</button>
    <button class="nav-cta" id="navEnterBtn" data-en="Sign Up" data-ar="اشترك">Sign Up</button>
  </div>
</nav>

<!-- Ticker Ribbon -->
<div class="ticker-ribbon">
  <div class="ticker-track" id="tickerTrack">
    <span class="ticker-item">
      <span class="ticker-symbol">TASI</span>
      <span class="ticker-price">12,450.30</span>
      <span class="ticker-change up">+0.6%</span>
    </span>
    <span class="ticker-item">
      <span class="ticker-symbol">SABIC</span>
      <span class="ticker-price">98.40</span>
      <span class="ticker-change down">-0.3%</span>
    </span>
    <span class="ticker-item">
      <span class="ticker-symbol">STC</span>
      <span class="ticker-price">142.80</span>
      <span class="ticker-change up">+1.2%</span>
    </span>
    <span class="ticker-item">
      <span class="ticker-symbol">Al Rajhi</span>
      <span class="ticker-price">168.20</span>
      <span class="ticker-change up">+0.8%</span>
    </span>
  </div>
  <div class="ticker-track" id="tickerTrack2" style="animation:tickerScroll 40s linear infinite 20s;">
    <span class="ticker-item">
      <span class="ticker-symbol">TASI</span>
      <span class="ticker-price">12,450.30</span>
      <span class="ticker-change up">+0.6%</span>
    </span>
    <span class="ticker-item">
      <span class="ticker-symbol">SABIC</span>
      <span class="ticker-price">98.40</span>
      <span class="ticker-change down">-0.3%</span>
    </span>
    <span class="ticker-item">
      <span class="ticker-symbol">STC</span>
      <span class="ticker-price">142.80</span>
      <span class="ticker-change up">+1.2%</span>
    </span>
    <span class="ticker-item">
      <span class="ticker-symbol">Al Rajhi</span>
      <span class="ticker-price">168.20</span>
      <span class="ticker-change up">+0.8%</span>
    </span>
  </div>
</div>

<!-- Hero Section -->
<section class="hero">
  <div class="hero-bg">
    <div class="light-streak streak-1"></div>
    <div class="light-streak streak-2"></div>
    <div class="light-streak streak-3"></div>
  </div>

  <canvas id="particleCanvas"></canvas>

  <div class="revenue-card">
    <div class="revenue-label">📈 TASI Index</div>
    <div class="revenue-value">12,450.30</div>
    <div class="revenue-change">+0.6% ▲</div>
    <div class="revenue-subtitle">Last 30 days</div>
  </div>

  <div class="hero-content">
    <h1 class="hero-title" data-en="Invest Smarter.<br/>Research for <span class='hero-title-accent'>Saudi Markets</span>" data-ar="استثمر بذكاء.<br/>أبحاث <span class='hero-title-accent'>الأسواق السعودية</span>">
      Invest Smarter.
      <br/>
      Research for <span class="hero-title-accent">Saudi Markets</span>
    </h1>
    <p class="hero-subtitle" data-en="Institutional-grade research and AI-powered insights for Saudi Arabia's fastest-growing investors." data-ar="بحث بمستوى مؤسسي ورؤى مدعومة بالذكاء الاصطناعي للمستثمرين الأسرع نموا في المملكة العربية السعودية.">
      Institutional-grade research and AI-powered insights for Saudi Arabia's fastest-growing investors.
    </p>

    <div class="avatar-group">
      <div class="avatar a1">MM</div>
      <div class="avatar a2">AS</div>
      <div class="avatar a3">KH</div>
      <div class="avatar-text" data-en="Built by TAM Capital" data-ar="من تطوير رأس مال TAM">Built by TAM Capital</div>
    </div>

    <button id="heroCta" style="
      margin-top:28px;padding:16px 48px;font-size:1.05rem;font-weight:600;
      background:linear-gradient(135deg,#1A6DB6,#6CB9B6);color:#fff;
      border:none;border-radius:50px;cursor:pointer;letter-spacing:0.5px;
      transition:all .3s ease;box-shadow:0 4px 24px rgba(26,109,182,0.4);
    " onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 8px 32px rgba(26,109,182,0.6)'"
       onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='0 4px 24px rgba(26,109,182,0.4)'"
       data-en="Start Research" data-ar="ابدأ البحث">Start Research</button>
  </div>

  <div class="scroll-indicator">
    <span class="scroll-text" data-en="SCROLL" data-ar="انزلق">SCROLL</span>
    <span class="scroll-arrow">↓</span>
  </div>
</section>

<!-- Features Section -->
<section class="features-section">
  <div class="section-content">
    <h2 class="section-title reveal" data-en="Why Choose TAM Capital?" data-ar="لماذا تختار رأس مال TAM؟">Why Choose TAM Capital?</h2>
    <div class="features-grid">
      <div class="feature-card reveal">
        <div class="feature-icon">📊</div>
        <h3 class="feature-title" data-en="Real-Time Analytics" data-ar="تحليلات فورية">Real-Time Analytics</h3>
        <p class="feature-desc" data-en="Live market data and portfolio tracking powered by proprietary algorithms." data-ar="تتبع السوق المباشر والمحفظة مدعومة بخوارزميات خاصة بنا.">Live market data and portfolio tracking powered by proprietary algorithms.</p>
      </div>
      <div class="feature-card reveal">
        <div class="feature-icon">🤖</div>
        <h3 class="feature-title" data-en="AI-Powered Research" data-ar="بحث مدعوم بالذكاء الاصطناعي">AI-Powered Research</h3>
        <p class="feature-desc" data-en="Intelligent analysis across 500+ Saudi companies and securities." data-ar="تحليل ذكي عبر أكثر من 500 شركة سعودية وأوراق مالية.">Intelligent analysis across 500+ Saudi companies and securities.</p>
      </div>
      <div class="feature-card reveal">
        <div class="feature-icon">🔒</div>
        <h3 class="feature-title" data-en="Enterprise Security" data-ar="أمان المستوى الأول">Enterprise Security</h3>
        <p class="feature-desc" data-en="ISO 27001 certified with 256-bit encryption and SOC 2 compliance." data-ar="معتمد ISO 27001 مع تشفير 256 بت والامتثال SOC 2.">ISO 27001 certified with 256-bit encryption and SOC 2 compliance.</p>
      </div>
      <div class="feature-card reveal">
        <div class="feature-icon">📈</div>
        <h3 class="feature-title" data-en="Performance Tracking" data-ar="تتبع الأداء">Performance Tracking</h3>
        <p class="feature-desc" data-en="Monitor returns and benchmark against regional indices." data-ar="مراقبة العائدات والمقارنة مع المؤشرات الإقليمية.">Monitor returns and benchmark against regional indices.</p>
      </div>
      <div class="feature-card reveal">
        <div class="feature-icon">💬</div>
        <h3 class="feature-title" data-en="Expert Guidance" data-ar="إرشادات الخبراء">Expert Guidance</h3>
        <p class="feature-desc" data-en="24/7 analyst support in Arabic and English." data-ar="دعم المحللين 24/7 باللغة العربية والإنجليزية.">24/7 analyst support in Arabic and English.</p>
      </div>
      <div class="feature-card reveal">
        <div class="feature-icon">🌍</div>
        <h3 class="feature-title" data-en="Global Insights" data-ar="رؤى عالمية">Global Insights</h3>
        <p class="feature-desc" data-en="International market trends impacting the Kingdom." data-ar="اتجاهات السوق الدولية التي تؤثر على المملكة.">International market trends impacting the Kingdom.</p>
      </div>
    </div>
  </div>
</section>

<!-- Spacer between features and demo -->
<div style="height:40px;"></div>

<!-- Demo Section -->
<section class="demo-section">
  <div class="section-content">
    <div class="demo-container">
      <div class="demo-content">
        <h3 data-en="Interactive Portfolio Dashboard" data-ar="لوحة معلومات المحفظة التفاعلية">Interactive Portfolio Dashboard</h3>
        <p data-en="Experience real-time portfolio visualization with actionable insights." data-ar="اختبر تصور المحفظة في الوقت الفعلي مع رؤى قابلة للتنفيذ.">Experience real-time portfolio visualization with actionable insights.</p>
        <ul class="demo-list">
          <li data-en="Real-time price updates" data-ar="تحديثات الأسعار المباشرة">Real-time price updates</li>
          <li data-en="Sector allocation charts" data-ar="رسوم بيانية لتوزيع القطاع">Sector allocation charts</li>
          <li data-en="Risk assessment tools" data-ar="أدوات تقييم المخاطر">Risk assessment tools</li>
          <li data-en="Performance benchmarking" data-ar="قياس الأداء">Performance benchmarking</li>
        </ul>
      </div>
      <div>
        <canvas id="demoChart"></canvas>
      </div>
    </div>
  </div>
</section>

<!-- CMA Badge Section -->
<section class="badge-section" id="about">
  <h2 class="badge-title" data-en="Trusted by Regulators & Investors" data-ar="موثوق من قبل الجهات المنظمة والمستثمرين">Trusted by Regulators &amp; Investors</h2>
  <div class="badge-container">
    <div class="badge-item reveal">
      <div class="badge-icon">✅</div>
      <div class="badge-text" data-en="CMA Authorized" data-ar="المرخصة من هيئة التخصصات الصحية">CMA Authorized</div>
    </div>
    <div class="badge-item reveal">
      <div class="badge-icon">🔐</div>
      <div class="badge-text" data-en="ISO 27001 Certified" data-ar="معتمد ISO 27001">ISO 27001 Certified</div>
    </div>
    <div class="badge-item reveal">
      <div class="badge-icon">🏆</div>
      <div class="badge-text" data-en="SOC 2 Compliant" data-ar="متوافق SOC 2">SOC 2 Compliant</div>
    </div>
  </div>
</section>

<!-- Final CTA -->
<section class="cta-section">
  <h2 class="cta-title" data-en="Ready to Transform Your Investments?" data-ar="هل أنت مستعد لتحويل استثماراتك؟">Ready to Transform Your Investments?</h2>
  <p class="cta-subtitle" data-en="AI-powered research built for the Saudi market." data-ar="أبحاث مدعومة بالذكاء الاصطناعي مصممة للسوق السعودي.">AI-powered research built for the Saudi market.</p>
  <button id="finalCta" data-en="Get Started Free" data-ar="ابدأ مجانا">Get Started Free</button>
</section>

<!-- Footer -->
<footer>
  <p class="footer-text">
    <span data-en="© 2026 TAM Capital. All rights reserved." data-ar="© 2026 رأس مال TAM. جميع الحقوق محفوظة.">© 2026 TAM Capital. All rights reserved.</span>
  </p>
  <div class="footer-links">
    <a href="#" data-en="Privacy Policy" data-ar="سياسة الخصوصية">Privacy Policy</a>
    <a href="#" data-en="Terms of Service" data-ar="شروط الخدمة">Terms of Service</a>
    <a href="#" data-en="Contact Us" data-ar="اتصل بنا">Contact Us</a>
  </div>
</footer>

<script>
// ===== LANGUAGE TOGGLE =====
let currentLang='en';
function toggleLang(){{
  currentLang=currentLang==='en'?'ar':'en';
  document.querySelectorAll('[data-en][data-ar]').forEach(el=>{{
    const val=currentLang==='en'?el.getAttribute('data-en'):el.getAttribute('data-ar');
    if(val.includes('<')){{el.innerHTML=val;}}else{{el.textContent=val;}}
  }});
  document.documentElement.dir=currentLang==='ar'?'rtl':'ltr';
  document.documentElement.lang=currentLang;
}}

// ===== NAVBAR SCROLL =====
window.addEventListener('scroll',()=>{{
  const nav=document.getElementById('navbar');
  nav.classList.toggle('scrolled',window.scrollY>50);
}});

// ===== PARTICLE CONSTELLATION =====
const canvas=document.getElementById('particleCanvas');
const ctx=canvas.getContext('2d');
let particles=[];
let mouseX=window.innerWidth/2;
let mouseY=window.innerHeight/2;

function resizeCanvas(){{
  const hero=document.querySelector('.hero');
  canvas.width=hero.clientWidth;
  canvas.height=hero.clientHeight;
}}

class Particle{{
  constructor(){{
    this.x=Math.random()*canvas.width;
    this.y=Math.random()*canvas.height;
    this.vx=(Math.random()-0.5)*0.5;
    this.vy=(Math.random()-0.5)*0.5;
    this.radius=Math.random()*1.5+0.5;
    this.color='rgba(108,185,182,'+(Math.random()*0.5+0.3)+')';
  }}
  update(){{
    this.x+=this.vx;
    this.y+=this.vy;
    const dx=mouseX-this.x;
    const dy=mouseY-this.y;
    const distance=Math.sqrt(dx*dx+dy*dy);
    if(distance<150){{
      this.x-=(dx/distance)*1.5;
      this.y-=(dy/distance)*1.5;
    }}
    if(this.x<0||this.x>canvas.width)this.vx*=-1;
    if(this.y<0||this.y>canvas.height)this.vy*=-1;
  }}
  draw(){{
    ctx.beginPath();ctx.arc(this.x,this.y,this.radius,0,Math.PI*2);
    ctx.fillStyle=this.color;ctx.fill();
  }}
}}

function initParticles(){{
  particles=[];
  for(let i=0;i<40;i++)particles.push(new Particle());
}}

function drawConnections(){{
  for(let i=0;i<particles.length;i++){{
    for(let j=i+1;j<particles.length;j++){{
      const dx=particles[i].x-particles[j].x;
      const dy=particles[i].y-particles[j].y;
      const distance=Math.sqrt(dx*dx+dy*dy);
      if(distance<120){{
        ctx.strokeStyle='rgba(108,185,182,'+(0.2*(1-distance/120))+')';
        ctx.lineWidth=1;ctx.beginPath();
        ctx.moveTo(particles[i].x,particles[i].y);
        ctx.lineTo(particles[j].x,particles[j].y);ctx.stroke();
      }}
    }}
  }}
}}

function animate(){{
  ctx.clearRect(0,0,canvas.width,canvas.height);
  particles.forEach(p=>{{p.update();p.draw();}});
  drawConnections();
  requestAnimationFrame(animate);
}}

canvas.addEventListener('mousemove',e=>{{
  const rect=canvas.getBoundingClientRect();
  mouseX=e.clientX-rect.left;
  mouseY=e.clientY-rect.top;
}});

resizeCanvas();
initParticles();
animate();
window.addEventListener('resize',()=>{{resizeCanvas();initParticles();}});

// ===== FEATURE CARD MOUSE GLOW =====
document.querySelectorAll('.feature-card').forEach(card=>{{
  card.addEventListener('mousemove',e=>{{
    const rect=card.getBoundingClientRect();
    const x=e.clientX-rect.left;
    const y=e.clientY-rect.top;
    card.style.setProperty('--mouse-x',x+'px');
    card.style.setProperty('--mouse-y',y+'px');
  }});
}});

// ===== SCROLL REVEAL =====
const observer=new IntersectionObserver(entries=>{{
  entries.forEach(entry=>{{
    if(entry.isIntersecting)entry.target.classList.add('active');
  }});
}},{{threshold:0.1}});

document.querySelectorAll('.reveal').forEach(el=>observer.observe(el));

// (Counter animation removed — no fake stats)

// ===== DEMO CHART ANIMATION =====
function drawDemoChart(){{
  const demoCanvas=document.getElementById('demoChart');
  if(!demoCanvas)return;
  const demoCtx=demoCanvas.getContext('2d');
  const rect=demoCanvas.getBoundingClientRect();
  demoCanvas.width=demoCanvas.offsetWidth;
  demoCanvas.height=demoCanvas.offsetHeight;

  const data=[25,40,35,50,65,58,72,85,78,92];
  const padding=30;
  const graphWidth=demoCanvas.width-2*padding;
  const graphHeight=demoCanvas.height-2*padding;
  const maxValue=Math.max(...data);
  const stepX=graphWidth/(data.length-1);

  // Grid
  demoCtx.strokeStyle='rgba(108,185,182,0.1)';
  demoCtx.lineWidth=1;
  for(let i=0;i<=5;i++){{
    const y=padding+i*(graphHeight/5);
    demoCtx.beginPath();demoCtx.moveTo(padding,y);
    demoCtx.lineTo(demoCanvas.width-padding,y);demoCtx.stroke();
  }}

  // Line
  demoCtx.strokeStyle='#6CB9B6';
  demoCtx.lineWidth=2;
  demoCtx.beginPath();
  data.forEach((val,i)=>{{
    const x=padding+i*stepX;
    const y=demoCanvas.height-padding-(val/maxValue)*graphHeight;
    i===0?demoCtx.moveTo(x,y):demoCtx.lineTo(x,y);
  }});
  demoCtx.stroke();

  // Points
  demoCtx.fillStyle='#1A6DB6';
  data.forEach((val,i)=>{{
    const x=padding+i*stepX;
    const y=demoCanvas.height-padding-(val/maxValue)*graphHeight;
    demoCtx.beginPath();demoCtx.arc(x,y,4,0,Math.PI*2);demoCtx.fill();
  }});
}}

drawDemoChart();
window.addEventListener('resize',drawDemoChart);

// ===== CTA BUTTON NAVIGATION =====
function enterApp(){{
  // Navigate the top-level window to add ?enter=true
  window.top.location.href = window.top.location.pathname + '?enter=true';
}}
document.getElementById('finalCta').addEventListener('click', enterApp);
document.getElementById('navEnterBtn').addEventListener('click', enterApp);
document.getElementById('heroCta').addEventListener('click', enterApp);
</script>
</body>
</html>'''

    # Render as iframe component for full control
    import urllib.parse
    encoded = urllib.parse.quote(html)
    st.components.v1.html(html, height=3800, scrolling=True)

    # Streamlit button below the iframe as reliable fallback
    st.markdown("")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            "Enter Research Terminal",
            key="fallback_button",
            use_container_width=True,
            type="primary",
        ):
            st.session_state.show_landing = False
            st.rerun()
