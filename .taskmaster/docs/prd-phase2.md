# Product Requirements Document — Phase 2
# TAMS Research Agent — Platform Evolution
# Version 2.0 | Author: Mohammed Malki (COO/CDO, TAM Capital)
# Date: March 31, 2026

---

## 1. OVERVIEW

### 1.1 Context
Phase 1 of TAMS Research Agent is complete: a Streamlit-based AI equity research platform with Claude-powered analysis, 4 export formats (DOCX, PDF, PPTX, XLSX), portfolio tracking, watchlists, sector analysis, multi-stock comparison, report versioning, and the TAM Liquid Glass UI. The platform currently runs as a single-user Streamlit app with JSON file storage.

### 1.2 Phase 2 Vision
Transform TAMS Research Agent from a single-user research tool into a multi-user intelligent platform with persistent database storage, user authentication, admin management, real-time alerts, interactive analytics, and machine learning that adapts to each analyst's workflow.

### 1.3 Target Users
- Primary: TAM Capital equities research team (5-15 analysts)
- Admin: Mohammed Malki (Super Admin) + team leads
- Future: Expandable to TAM Capital clients

### 1.4 Current Tech Stack (Streamlit)
- Frontend/Backend: Streamlit (Python) with custom CSS (TAM Liquid Glass theme)
- AI: Anthropic Claude API (Opus 4 primary, Sonnet 4 fallback)
- Data: Yahoo Finance (yfinance), DuckDuckGo search
- Storage: JSON files (watchlist_data/, report_history/)
- Export: python-docx, python-pptx, reportlab, openpyxl
- Deployment: Streamlit Cloud (tamresearcher.streamlit.app)

---

## 2. PHASE 2 ARCHITECTURE CHANGES

### 2.1 Database Migration: JSON to Supabase (PostgreSQL)
**Priority: CRITICAL — must be done first, everything else depends on it.**

Migrate all data from JSON flat files to Supabase (hosted PostgreSQL + Auth + Realtime).

#### Database Schema:

**users table:**
- id (UUID, PK)
- email (unique)
- full_name
- role (enum: super_admin, admin, analyst, viewer)
- avatar_url
- preferences (JSONB — theme, default watchlist, notification settings)
- created_at, updated_at, last_login_at

**watchlists table:**
- id (UUID, PK)
- user_id (FK → users)
- name, description
- is_default (boolean)
- created_at, updated_at

**watchlist_items table:**
- id (UUID, PK)
- watchlist_id (FK → watchlists)
- ticker, company_name
- alert_rules (JSONB — price targets, volume thresholds, news keywords)
- added_at

**portfolio_positions table:**
- id (UUID, PK)
- user_id (FK → users)
- ticker, company_name
- shares (decimal), cost_basis (decimal)
- date_added, notes

**reports table:**
- id (UUID, PK)
- user_id (FK → users)
- ticker, company_name
- version (integer)
- sections (JSONB)
- metadata (JSONB — sources, generation time, model used)
- files (JSONB — paths to DOCX/PDF/PPTX/XLSX)
- change_summary (text)
- status (enum: draft, published, archived)
- created_at

**alerts table:**
- id (UUID, PK)
- user_id (FK → users)
- ticker
- alert_type (enum: price_target, volume_spike, news_trigger, earnings, technical_signal)
- severity (enum: info, warning, critical)
- message (text)
- context (JSONB — price, volume, trigger details)
- is_read (boolean)
- created_at

**alert_rules table:**
- id (UUID, PK)
- user_id (FK → users)
- ticker (nullable — null means apply to all)
- rule_type (enum: price_above, price_below, volume_spike, pct_change, news_keyword, technical)
- parameters (JSONB — threshold, keywords, indicator settings)
- is_active (boolean)
- last_triggered_at
- created_at

**research_notes table:**
- id (UUID, PK)
- user_id (FK → users)
- ticker
- report_id (FK → reports, nullable)
- content (text)
- tags (text array)
- created_at, updated_at

**chat_sessions table:**
- id (UUID, PK)
- user_id (FK → users)
- title
- messages (JSONB array)
- created_at, updated_at

**user_activity table (for ML):**
- id (UUID, PK)
- user_id (FK → users)
- action_type (enum: search, analyze, view_report, export, add_watchlist, view_chart, set_alert)
- ticker (nullable)
- metadata (JSONB — page, duration, parameters)
- created_at

**ai_sentiment_scores table (for ML):**
- id (UUID, PK)
- ticker
- report_id (FK → reports, nullable)
- score (float, -1.0 to 1.0)
- category (enum: overall, management_tone, financial_health, growth_outlook, risk_level)
- model_version (text)
- created_at

#### Migration Tasks:
1. Set up Supabase project and configure connection
2. Create all tables with proper indexes and RLS (Row Level Security) policies
3. Write migration script to move existing JSON data into Supabase
4. Create a data access layer (DAL) module — `data/supabase_client.py` — that replaces all JSON read/write operations
5. Update all imports in app.py and data modules to use the new DAL
6. Add connection pooling and error handling
7. Test full workflow end-to-end with Supabase backend
8. Keep JSON as fallback for local development without Supabase

---

### 2.2 User Authentication & Admin Panel
**Priority: CRITICAL — required before multi-user features.**

#### Authentication (Supabase Auth):
- Email/password login with Supabase Auth
- Magic link (passwordless) option for convenience
- Session management with Supabase JWT tokens
- Streamlit integration: login page renders before any app content
- "Remember me" persistent sessions
- Password reset flow via email
- Invite-only registration (admin sends invite link)

#### Role-Based Access Control:
| Role | Permissions |
|------|------------|
| super_admin | Everything + user management + system config + API key management |
| admin | User management + all analyst features + report approval |
| analyst | Research, portfolio, watchlists, alerts, export, notes |
| viewer | Read-only: view published reports, dashboards, no generation |

#### Admin Panel (new page: /admin):
- **User Management**: invite new users, edit roles, deactivate accounts, reset passwords
- **Usage Dashboard**: reports generated per user, API calls consumed, most researched tickers, active sessions
- **System Config**: API key management (Anthropic, future integrations), default model selection, alert thresholds
- **Audit Log**: timestamped log of all user actions (report generation, exports, logins, admin changes)
- **Team Overview**: active users, last login times, feature adoption metrics

#### Login UI:
- TAM Liquid Glass styled login page with TAM logo
- Email + password fields with glass card design
- "Forgot password" and magic link options
- Animated background (same floating orbs as main app)

---

### 2.3 Morning Brief & Intelligent Alerts
**Priority: HIGH**

#### Morning Brief (AI-Generated Daily Digest):
- Runs daily at configurable time (default 7:00 AM AST)
- Scans all tickers across user's watchlists and portfolio
- For each ticker, checks: overnight price movement, recent news (last 24h), upcoming events (earnings, dividends)
- Claude generates a concise brief: "3 things you need to know today"
- Brief is stored as a special report type and shown on Dashboard
- Optional: email delivery of morning brief as HTML email

#### Implementation:
- Background scheduler using APScheduler or Supabase Edge Functions
- New prompt module: `prompts/morning_brief.py` — concise, actionable format
- Dashboard widget: "Good morning, [Name]. Here's your brief for [Date]"
- Brief sections: Market Pulse (TASI index summary), Watchlist Movers, News Highlights, Upcoming Events, AI Insights (pattern-based observations)

#### Custom Alert Rules Builder:
- UI for creating alert rules per ticker or globally:
  - **Price Target**: alert when price crosses above/below a threshold
  - **Percentage Change**: alert on daily move exceeding X%
  - **Volume Spike**: alert when volume exceeds X multiple of 20-day average
  - **News Keyword**: alert when DuckDuckGo finds news matching keywords for a ticker
  - **Technical Signal**: alert when RSI crosses 30/70, MACD crossover, MA crossover
- Each rule has: ticker, condition, threshold, notification preference (in-app, email, both)
- Alert cooldown: configurable minimum interval between repeat alerts (default 4 hours)

#### Alert Dashboard (enhanced):
- Centralized alert feed with severity badges (info/warning/critical)
- Filter by ticker, type, severity, date range
- One-click "Analyze this" — opens research chat pre-loaded with alert context
- Mark as read / dismiss / snooze
- Alert history with search
- Unread badge count in navigation sidebar

#### Notification Delivery:
- In-app: real-time toast notifications via Streamlit + alert badge in nav
- Email: HTML-formatted alert emails via Supabase Edge Functions or SendGrid
- Future: Telegram bot integration (optional)

---

### 2.4 Interactive Charts & DCF Model Builder
**Priority: HIGH**

#### Interactive Technical Charts (Plotly):
Replace static Matplotlib charts with interactive Plotly charts:
- **Candlestick chart** with volume bars overlay
- **Technical indicator overlays** (user toggleable):
  - Moving Averages: MA20, MA50, MA200 (with crossover highlighting)
  - Bollinger Bands (20-period, 2 std dev)
  - RSI (14-period) in separate subplot
  - MACD + Signal + Histogram in separate subplot
  - Fibonacci retracement levels (auto-calculated from recent swing high/low)
- **Time range selector**: 1W, 1M, 3M, 6M, 1Y, 5Y, MAX
- **Drawing tools**: horizontal line, trend line (via Plotly annotations)
- **Zoom, pan, crosshair** with price/date readout
- **Dark theme** matching TAM Liquid Glass (transparent background, TAM accent colors)
- **Comparison mode**: overlay multiple tickers on same chart (normalized or absolute)

#### Implementation:
- New module: `data/interactive_charts.py` — Plotly chart generators
- Use `st.plotly_chart()` with `use_container_width=True`
- Chart config stored in session state (selected indicators, time range)
- Charts embedded in Research, Portfolio, Sectors, and Compare pages

#### DCF Model Builder:
Interactive discounted cash flow calculator:
- **Input Panel** (glass card with form fields):
  - Revenue growth rate (next 5 years, editable per year)
  - Operating margin trajectory
  - WACC (auto-calculated from beta + risk-free rate + equity risk premium, or manual override)
  - Terminal growth rate
  - Tax rate
  - Shares outstanding (auto-filled from Yahoo Finance)
- **Output Panel**:
  - Projected free cash flows (5-year table)
  - Terminal value calculation
  - Enterprise value → Equity value → Implied share price
  - Upside/downside vs. current price (with color coding)
- **Sensitivity Table**: 2D matrix showing implied price across different WACC and terminal growth rate combinations
- **Scenario Analysis**: Bull / Base / Bear cases with one-click toggle
- **AI Commentary**: Claude interprets the DCF result in context of the company's fundamentals

#### Implementation:
- New module: `data/dcf_model.py` — DCF calculation engine
- New page section or dedicated tab within Research page
- All calculations run client-side (Python) for instant feedback
- Export DCF model to Excel with formatted sensitivity table
- Save DCF assumptions per ticker for comparison over time

#### Additional Analytics (Peer Benchmarking Enhancement):
- **Heat Map**: sector peer comparison with color-coded metric rankings
- **Risk Metrics**: Portfolio-level VaR (95%), Sharpe ratio, max drawdown, correlation matrix
- **Financial Statement Viewer**: 5-year interactive income statement / balance sheet / cash flow tables with growth rates and margin calculations

---

### 2.5 ML & Behavior Learning System
**Priority: MEDIUM — builds over time, starts collecting data immediately.**

#### Usage Analytics & Tracking:
- Track every user action in `user_activity` table:
  - Which tickers are researched (frequency, recency)
  - Which pages are visited and for how long
  - Which export formats are used
  - Which alert types are configured
  - Search queries and chat messages (anonymized for ML)
- Admin dashboard widget: usage heatmap, top tickers, feature adoption funnel

#### Personalized Recommendations Engine:
- **Ticker Affinity Model**: weighted score per ticker per user based on:
  - Research frequency (higher weight for recent)
  - Watchlist inclusion
  - Portfolio holdings
  - Alert rules set
  - Report exports
- **Smart Suggestions** on Dashboard:
  - "SABIC earnings are in 3 days — want to refresh your analysis?"
  - "Oil prices dropped 4% — you track 3 energy stocks. Review?"
  - "You haven't checked STC in 30 days — its P/E changed significantly"
- **Related Tickers**: "Analysts who research ARAMCO also look at SABIC and Maaden"
- Implementation: collaborative filtering using user_activity data, cosine similarity between user behavior vectors

#### Sentiment Trend Database:
- Every AI-generated report extracts a sentiment score (-1.0 to 1.0) per category:
  - Overall sentiment
  - Management tone (from earnings analysis)
  - Financial health
  - Growth outlook
  - Risk level
- Scores stored in `ai_sentiment_scores` with timestamp
- **Sentiment Chart**: time-series visualization of sentiment evolution per ticker
- **Sentiment Alerts**: notify when sentiment shifts significantly between reports
- **Cross-ticker Sentiment**: compare sentiment trends across sector peers

#### Predictive Signals (Experimental):
- **Earnings Surprise Probability**: based on historical earnings vs. estimates pattern + current sentiment
- **Momentum Score**: composite of price momentum + volume trend + sentiment trend
- **Risk Signal**: early warning combining VaR spike + sentiment decline + volume anomaly
- These are displayed as "AI Signals" badges on ticker cards (confidence level shown)
- Clearly labeled as experimental/AI-generated, not investment advice
- CMA compliance disclaimer on all predictive outputs

---

### 2.6 Workflow & Collaboration Enhancements
**Priority: MEDIUM**

#### Research Notes:
- Attach timestamped notes to any ticker
- Rich text (markdown) with tagging support
- Notes searchable across all tickers
- Notes visible on report detail and ticker overview
- "Pin" important notes to top of ticker page

#### Scheduled Reports:
- Configure recurring report generation:
  - Weekly watchlist refresh (regenerate reports for all watched tickers)
  - Monthly portfolio review (comprehensive portfolio analysis)
  - Custom: any ticker on any schedule (daily/weekly/monthly)
- Uses APScheduler or Supabase cron
- Generated reports auto-stored, email notification sent

#### Audit Trail:
- Every action logged: report generation, export, login, setting change, alert trigger
- Audit log viewable by admin
- Filterable by user, action type, date range
- Supports CMA regulatory compliance requirements

---

## 3. IMPLEMENTATION ORDER

### Phase 2A — Foundation (Week 1-2):
1. Supabase project setup and schema creation
2. Data access layer (DAL) module
3. Migrate JSON data to Supabase
4. Supabase Auth integration (login page, session management)
5. Role-based access control middleware
6. Admin panel (user management, basic usage stats)

### Phase 2B — Intelligence (Week 3-4):
7. Interactive Plotly charts (replace Matplotlib)
8. Enhanced technical indicators
9. Custom alert rules builder UI
10. Alert dashboard enhancements
11. Morning brief system (scheduler + prompt + dashboard widget)
12. Email notification delivery

### Phase 2C — Analytics (Week 5-6):
13. DCF model builder (calculation engine + UI)
14. Sensitivity analysis table
15. Risk metrics (VaR, Sharpe, drawdown)
16. Peer benchmarking heat map
17. Financial statement interactive viewer

### Phase 2D — Intelligence Layer (Week 7-8):
18. User activity tracking system
19. Sentiment scoring extraction and storage
20. Personalized recommendation engine
21. Smart suggestions on dashboard
22. Sentiment trend charts
23. Predictive signals (experimental)

### Phase 2E — Collaboration (Week 9-10):
24. Research notes system
25. Scheduled report generation
26. Audit trail logging
27. Enhanced admin dashboard with ML insights

---

## 4. NON-FUNCTIONAL REQUIREMENTS

### Performance
- Supabase queries < 200ms for standard operations
- Interactive charts render < 1 second
- DCF recalculation < 500ms on input change
- Morning brief generation < 90 seconds
- Support 15 concurrent user sessions

### Security
- Supabase Row Level Security (RLS) on all tables
- JWT session tokens with configurable expiry
- API keys stored in Supabase Vault, never in client code
- All admin actions require super_admin or admin role
- Audit log tamper-proof (append-only)

### CMA Compliance
- All AI-generated content includes disclaimer: "This analysis is AI-generated and does not constitute investment advice. TAM Capital is regulated by the Capital Market Authority (CMA) of Saudi Arabia."
- Predictive signals clearly labeled as experimental
- Audit trail meets regulatory record-keeping requirements
- Report exports include generation metadata (timestamp, model, data sources)

### Deployment
- Streamlit Cloud for frontend (existing)
- Supabase cloud for database + auth + edge functions
- Environment variables for all API keys
- Migration scripts idempotent and reversible

---

## 5. SUCCESS METRICS

| Metric | Target |
|--------|--------|
| Database migration | Zero data loss, all features working with Supabase |
| User onboarding | 5+ analysts active within first week |
| Morning brief adoption | 80%+ of analysts read their daily brief |
| Alert engagement | Average 3+ custom alert rules per analyst |
| DCF usage | 50%+ of reports include DCF analysis |
| Sentiment tracking | Sentiment scores available for all researched tickers |
| ML recommendations | 30%+ click-through on smart suggestions |
| Report generation time | < 60 seconds (unchanged from Phase 1) |
| Platform uptime | 99.5%+ during Saudi market hours (10am-3pm AST) |
