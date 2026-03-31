-- Supabase PostgreSQL Schema for Stock Research App
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==================== USERS TABLE ====================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'analyst' CHECK (role IN ('super_admin', 'admin', 'analyst', 'viewer')),
    avatar_url TEXT,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_created_at ON users(created_at DESC);

-- ==================== WATCHLISTS TABLE ====================
CREATE TABLE watchlists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_watchlists_user_id ON watchlists(user_id);
CREATE INDEX idx_watchlists_is_default ON watchlists(user_id, is_default);
CREATE UNIQUE INDEX idx_watchlists_user_default ON watchlists(user_id) WHERE is_default = TRUE;

-- ==================== WATCHLIST_ITEMS TABLE ====================
CREATE TABLE watchlist_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    watchlist_id UUID NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    company_name TEXT DEFAULT '',
    alert_rules JSONB DEFAULT '{}',
    added_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_watchlist_items_watchlist_id ON watchlist_items(watchlist_id);
CREATE INDEX idx_watchlist_items_ticker ON watchlist_items(ticker);
CREATE INDEX idx_watchlist_items_added_at ON watchlist_items(added_at DESC);

-- ==================== PORTFOLIO_POSITIONS TABLE ====================
CREATE TABLE portfolio_positions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    company_name TEXT DEFAULT '',
    shares DECIMAL NOT NULL DEFAULT 0,
    cost_basis DECIMAL NOT NULL DEFAULT 0,
    date_added TIMESTAMPTZ DEFAULT NOW(),
    notes TEXT DEFAULT ''
);

CREATE INDEX idx_portfolio_positions_user_id ON portfolio_positions(user_id);
CREATE INDEX idx_portfolio_positions_ticker ON portfolio_positions(ticker);
CREATE INDEX idx_portfolio_positions_date_added ON portfolio_positions(date_added DESC);

-- ==================== REPORTS TABLE ====================
CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    ticker TEXT NOT NULL,
    company_name TEXT DEFAULT '',
    version INTEGER DEFAULT 1,
    sections JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    files JSONB DEFAULT '{}',
    change_summary TEXT DEFAULT '',
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_reports_user_id ON reports(user_id);
CREATE INDEX idx_reports_ticker ON reports(ticker);
CREATE INDEX idx_reports_status ON reports(status);
CREATE INDEX idx_reports_created_at ON reports(created_at DESC);
CREATE INDEX idx_reports_ticker_version ON reports(ticker, version DESC);

-- ==================== ALERTS TABLE ====================
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    alert_type TEXT NOT NULL CHECK (alert_type IN ('price_target', 'volume_spike', 'news_trigger', 'earnings', 'technical_signal')),
    severity TEXT DEFAULT 'info' CHECK (severity IN ('info', 'warning', 'critical')),
    message TEXT NOT NULL,
    context JSONB DEFAULT '{}',
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_alerts_user_id ON alerts(user_id);
CREATE INDEX idx_alerts_ticker ON alerts(ticker);
CREATE INDEX idx_alerts_alert_type ON alerts(alert_type);
CREATE INDEX idx_alerts_is_read ON alerts(user_id, is_read);
CREATE INDEX idx_alerts_created_at ON alerts(created_at DESC);
CREATE INDEX idx_alerts_severity ON alerts(severity);

-- ==================== ALERT_RULES TABLE ====================
CREATE TABLE alert_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ticker TEXT,
    rule_type TEXT NOT NULL CHECK (rule_type IN ('price_above', 'price_below', 'volume_spike', 'pct_change', 'news_keyword', 'technical')),
    parameters JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    last_triggered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_alert_rules_user_id ON alert_rules(user_id);
CREATE INDEX idx_alert_rules_ticker ON alert_rules(ticker);
CREATE INDEX idx_alert_rules_is_active ON alert_rules(user_id, is_active);
CREATE INDEX idx_alert_rules_rule_type ON alert_rules(rule_type);

-- ==================== RESEARCH_NOTES TABLE ====================
CREATE TABLE research_notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    report_id UUID REFERENCES reports(id) ON DELETE SET NULL,
    content TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    is_pinned BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_research_notes_user_id ON research_notes(user_id);
CREATE INDEX idx_research_notes_ticker ON research_notes(ticker);
CREATE INDEX idx_research_notes_report_id ON research_notes(report_id);
CREATE INDEX idx_research_notes_is_pinned ON research_notes(user_id, is_pinned);
CREATE INDEX idx_research_notes_created_at ON research_notes(created_at DESC);

-- ==================== CHAT_SESSIONS TABLE ====================
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT DEFAULT 'New Session',
    messages JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_chat_sessions_created_at ON chat_sessions(created_at DESC);

-- ==================== USER_ACTIVITY TABLE ====================
CREATE TABLE user_activity (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL CHECK (action_type IN ('search', 'analyze', 'view_report', 'export', 'add_watchlist', 'view_chart', 'set_alert', 'login', 'dcf_run')),
    ticker TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_user_activity_user_id ON user_activity(user_id);
CREATE INDEX idx_user_activity_action_type ON user_activity(action_type);
CREATE INDEX idx_user_activity_ticker ON user_activity(ticker);
CREATE INDEX idx_user_activity_created_at ON user_activity(created_at DESC);

-- ==================== AI_SENTIMENT_SCORES TABLE ====================
CREATE TABLE ai_sentiment_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticker TEXT NOT NULL,
    report_id UUID REFERENCES reports(id) ON DELETE SET NULL,
    score REAL NOT NULL CHECK (score >= -1.0 AND score <= 1.0),
    category TEXT NOT NULL CHECK (category IN ('overall', 'management_tone', 'financial_health', 'growth_outlook', 'risk_level')),
    model_version TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ai_sentiment_ticker ON ai_sentiment_scores(ticker);
CREATE INDEX idx_ai_sentiment_report_id ON ai_sentiment_scores(report_id);
CREATE INDEX idx_ai_sentiment_category ON ai_sentiment_scores(category);
CREATE INDEX idx_ai_sentiment_created_at ON ai_sentiment_scores(created_at DESC);

-- ==================== AUDIT_LOG TABLE ====================
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    resource TEXT DEFAULT '',
    details JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at DESC);

-- ==================== MORNING_BRIEFS TABLE ====================
CREATE TABLE morning_briefs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    tickers_covered TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_morning_briefs_user_id ON morning_briefs(user_id);
CREATE INDEX idx_morning_briefs_created_at ON morning_briefs(created_at DESC);

-- ==================== ROW LEVEL SECURITY POLICIES ====================

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE watchlists ENABLE ROW LEVEL SECURITY;
ALTER TABLE watchlist_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio_positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE alert_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_activity ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_sentiment_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE morning_briefs ENABLE ROW LEVEL SECURITY;

-- Users: Users can only read their own data, admins can read all
CREATE POLICY "Users can read own data" ON users
    FOR SELECT USING (auth.uid() = id OR EXISTS (
        SELECT 1 FROM users WHERE id = auth.uid() AND role IN ('admin', 'super_admin')
    ));

CREATE POLICY "Super admin can read all users" ON users
    FOR SELECT USING (EXISTS (
        SELECT 1 FROM users WHERE id = auth.uid() AND role = 'super_admin'
    ));

CREATE POLICY "Users can update own preferences" ON users
    FOR UPDATE USING (auth.uid() = id) WITH CHECK (auth.uid() = id);

-- Watchlists: Users can only see their own watchlists
CREATE POLICY "Users can read own watchlists" ON watchlists
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create watchlists" ON watchlists
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own watchlists" ON watchlists
    FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own watchlists" ON watchlists
    FOR DELETE USING (auth.uid() = user_id);

-- Watchlist Items: Users can only see items in their watchlists
CREATE POLICY "Users can read own watchlist items" ON watchlist_items
    FOR SELECT USING (EXISTS (
        SELECT 1 FROM watchlists WHERE id = watchlist_items.watchlist_id AND user_id = auth.uid()
    ));

CREATE POLICY "Users can add items to own watchlists" ON watchlist_items
    FOR INSERT WITH CHECK (EXISTS (
        SELECT 1 FROM watchlists WHERE id = watchlist_items.watchlist_id AND user_id = auth.uid()
    ));

CREATE POLICY "Users can delete own watchlist items" ON watchlist_items
    FOR DELETE USING (EXISTS (
        SELECT 1 FROM watchlists WHERE id = watchlist_items.watchlist_id AND user_id = auth.uid()
    ));

-- Portfolio Positions: Users can only see their own positions
CREATE POLICY "Users can read own positions" ON portfolio_positions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can add positions" ON portfolio_positions
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own positions" ON portfolio_positions
    FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own positions" ON portfolio_positions
    FOR DELETE USING (auth.uid() = user_id);

-- Reports: Users can see their own reports, admins can see all
CREATE POLICY "Users can read own reports" ON reports
    FOR SELECT USING (auth.uid() = user_id OR user_id IS NULL);

CREATE POLICY "Admins can read all reports" ON reports
    FOR SELECT USING (EXISTS (
        SELECT 1 FROM users WHERE id = auth.uid() AND role IN ('admin', 'super_admin')
    ));

CREATE POLICY "Users can create reports" ON reports
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own reports" ON reports
    FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Alerts: Users can only see their own alerts
CREATE POLICY "Users can read own alerts" ON alerts
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create alerts" ON alerts
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own alerts" ON alerts
    FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own alerts" ON alerts
    FOR DELETE USING (auth.uid() = user_id);

-- Alert Rules: Users can only manage their own rules
CREATE POLICY "Users can read own rules" ON alert_rules
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create rules" ON alert_rules
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own rules" ON alert_rules
    FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own rules" ON alert_rules
    FOR DELETE USING (auth.uid() = user_id);

-- Research Notes: Users can only see their own notes
CREATE POLICY "Users can read own notes" ON research_notes
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create notes" ON research_notes
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own notes" ON research_notes
    FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own notes" ON research_notes
    FOR DELETE USING (auth.uid() = user_id);

-- Chat Sessions: Users can only see their own sessions
CREATE POLICY "Users can read own sessions" ON chat_sessions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create sessions" ON chat_sessions
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own sessions" ON chat_sessions
    FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own sessions" ON chat_sessions
    FOR DELETE USING (auth.uid() = user_id);

-- User Activity: Users can only log their own activity
CREATE POLICY "Users can log own activity" ON user_activity
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can read own activity" ON user_activity
    FOR SELECT USING (auth.uid() = user_id OR EXISTS (
        SELECT 1 FROM users WHERE id = auth.uid() AND role IN ('admin', 'super_admin')
    ));

-- AI Sentiment Scores: Readable by all authenticated users
CREATE POLICY "Authenticated users can read sentiment scores" ON ai_sentiment_scores
    FOR SELECT USING (auth.role() = 'authenticated');

-- Audit Log: Append-only for all, readable only by admins
CREATE POLICY "All users can insert audit logs" ON audit_log
    FOR INSERT WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "Super admin can read audit logs" ON audit_log
    FOR SELECT USING (EXISTS (
        SELECT 1 FROM users WHERE id = auth.uid() AND role = 'super_admin'
    ));

-- Morning Briefs: Users can only see their own briefs
CREATE POLICY "Users can read own briefs" ON morning_briefs
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create briefs" ON morning_briefs
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- ==================== SEED DATA ====================

-- Insert super admin user
INSERT INTO users (id, email, full_name, role, preferences)
VALUES (
    uuid_generate_v4(),
    'mmalki@tamcapital.sa',
    'Mohammed Malki',
    'super_admin',
    '{"theme": "dark", "notifications_enabled": true, "email_digest": "weekly"}'
)
ON CONFLICT (email) DO NOTHING;

-- ==================== FUNCTIONS ====================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at columns
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_watchlists_updated_at BEFORE UPDATE ON watchlists
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_reports_updated_at BEFORE UPDATE ON reports
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_alert_rules_updated_at BEFORE UPDATE ON alert_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_research_notes_updated_at BEFORE UPDATE ON research_notes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_chat_sessions_updated_at BEFORE UPDATE ON chat_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
