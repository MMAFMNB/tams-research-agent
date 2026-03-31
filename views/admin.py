"""TAM Research — Admin Panel (Real Data)."""
import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

try:
    import plotly.graph_objects as go
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

from auth.rbac import require_role, is_super_admin
from auth.login import get_all_users, update_user_role, toggle_user_status

# Token tracker
try:
    from data.token_tracker import (
        get_token_summary, get_all_token_usage, get_top_consumers
    )
    TOKEN_TRACKER = True
except ImportError:
    TOKEN_TRACKER = False

# Activity tracker
try:
    from data.activity_tracker import (
        get_activity_summary, get_ticker_frequency, get_feature_adoption
    )
    ACTIVITY_TRACKER = True
except ImportError:
    ACTIVITY_TRACKER = False

# Audit logger
try:
    from data.audit_logger import get_audit_log, get_audit_summary
    AUDIT_AVAILABLE = True
except ImportError:
    AUDIT_AVAILABLE = False

# TAM brand colors
C_BG = "#070B14"
C_TEXT = "#E6EDF3"
C_TEXT2 = "#8B949E"
C_ACCENT = "#1A6DB6"
C_DEEP = "#222F62"
C_TURQUOISE = "#6CB9B6"
C_GREEN = "#22C55E"
C_RED = "#EF4444"
C_ORANGE = "#F59E0B"
C_CARD = "rgba(26,38,78,0.15)"
C_GLASS = "rgba(34,47,98,0.12)"
C_BORDER = "rgba(108,185,182,0.08)"


def render_admin():
    """Render the admin panel with real data."""
    require_role("super_admin", "admin")

    # TAM Liquid Glass CSS
    st.markdown(f"""<style>
    .glass-card {{
        background: {C_GLASS};
        backdrop-filter: blur(24px);
        -webkit-backdrop-filter: blur(24px);
        border: 1px solid {C_BORDER};
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 16px;
    }}
    .metric-big {{
        font-size: 2.2rem;
        font-weight: 700;
        color: {C_TEXT};
        margin: 0;
    }}
    .metric-label {{
        font-size: 0.8rem;
        color: {C_TEXT2};
        margin: 0;
    }}
    .metric-delta {{
        font-size: 0.85rem;
        font-weight: 600;
    }}
    .delta-up {{ color: {C_GREEN}; }}
    .delta-down {{ color: {C_RED}; }}
    .user-row {{
        background: {C_GLASS};
        border: 1px solid {C_BORDER};
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 8px;
    }}
    .badge {{
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }}
    .badge-admin {{ background: rgba(26,109,182,0.2); color: {C_ACCENT}; }}
    .badge-analyst {{ background: rgba(108,185,182,0.2); color: {C_TURQUOISE}; }}
    .badge-viewer {{ background: rgba(139,148,158,0.2); color: {C_TEXT2}; }}
    .badge-super {{ background: rgba(34,197,94,0.2); color: {C_GREEN}; }}
    .badge-active {{ background: rgba(34,197,94,0.15); color: {C_GREEN}; }}
    .badge-inactive {{ background: rgba(239,68,68,0.15); color: {C_RED}; }}
    </style>""", unsafe_allow_html=True)

    # Header
    st.markdown(f"""<div style="margin-bottom:24px;">
        <h1 style="color:{C_TEXT};margin:0;font-size:1.8rem;font-weight:700;">Admin Dashboard</h1>
        <p style="color:{C_TEXT2};margin:4px 0 0 0;">User management, token usage, and platform analytics</p>
    </div>""", unsafe_allow_html=True)

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "Overview", "Users", "Token Usage", "Audit Log"
    ])

    with tab1:
        _render_overview_tab()

    with tab2:
        _render_users_tab()

    with tab3:
        _render_token_usage_tab()

    with tab4:
        _render_audit_log_tab()


# =====================================================================
#  TAB 1 — OVERVIEW
# =====================================================================
def _render_overview_tab():
    """Executive overview with KPIs."""

    # Load real data
    users = get_all_users()
    active_users = [u for u in users if u.get("status") == "active"]
    new_this_week = [u for u in users if _is_recent(u.get("created_at"), days=7)]

    token_data = get_token_summary(30) if TOKEN_TRACKER else {}
    token_data_7 = get_token_summary(7) if TOKEN_TRACKER else {}

    # KPI cards row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""<div class="glass-card" style="text-align:center;">
            <p class="metric-label">Total Users</p>
            <p class="metric-big">{len(users)}</p>
            <p class="metric-delta delta-up">+{len(new_this_week)} this week</p>
        </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown(f"""<div class="glass-card" style="text-align:center;">
            <p class="metric-label">Active Users</p>
            <p class="metric-big">{len(active_users)}</p>
            <p class="metric-delta" style="color:{C_TURQUOISE};">{_pct(len(active_users), len(users))}% of total</p>
        </div>""", unsafe_allow_html=True)

    with col3:
        total_tokens = token_data.get("total_tokens", 0)
        st.markdown(f"""<div class="glass-card" style="text-align:center;">
            <p class="metric-label">Tokens Used (30d)</p>
            <p class="metric-big">{_fmt_tokens(total_tokens)}</p>
            <p class="metric-delta" style="color:{C_ORANGE};">${token_data.get('total_cost_usd', 0):.2f} est. cost</p>
        </div>""", unsafe_allow_html=True)

    with col4:
        total_requests = token_data.get("total_requests", 0)
        st.markdown(f"""<div class="glass-card" style="text-align:center;">
            <p class="metric-label">API Requests (30d)</p>
            <p class="metric-big">{total_requests:,}</p>
            <p class="metric-delta" style="color:{C_TURQUOISE};">{token_data_7.get('total_requests', 0)} last 7d</p>
        </div>""", unsafe_allow_html=True)

    # Charts row
    if PLOTLY_AVAILABLE and TOKEN_TRACKER:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"**Daily Token Usage (30 days)**")
            daily = token_data.get("daily_trend", [])
            if daily:
                fig = go.Figure(data=[
                    go.Bar(
                        x=[d["date"] for d in daily],
                        y=[d["tokens"] for d in daily],
                        marker=dict(color=C_TURQUOISE, opacity=0.8),
                        hovertemplate="<b>%{x}</b><br>Tokens: %{y:,.0f}<extra></extra>"
                    )
                ])
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color=C_TEXT, size=11),
                    margin=dict(l=0, r=0, t=10, b=30),
                    height=300,
                    xaxis=dict(showgrid=False),
                    yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            else:
                st.info("No token usage data yet. Data will appear after users run research queries.")

        with col2:
            st.markdown(f"**Top Token Consumers**")
            top = get_top_consumers(top_n=8, days=30) if TOKEN_TRACKER else []
            if top:
                # Map user IDs to names
                user_map = {u.get("id", ""): u.get("full_name", u.get("email", "Unknown")) for u in users}
                labels = [user_map.get(t["user_id"], t["user_id"][:12]) for t in top]
                values = [t["tokens"] for t in top]

                fig = go.Figure(data=[
                    go.Bar(
                        y=labels[::-1],
                        x=values[::-1],
                        orientation='h',
                        marker=dict(color=C_ACCENT),
                        text=[_fmt_tokens(v) for v in values[::-1]],
                        textposition='outside',
                        hovertemplate="<b>%{y}</b><br>Tokens: %{x:,.0f}<extra></extra>"
                    )
                ])
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color=C_TEXT, size=11),
                    margin=dict(l=0, r=60, t=10, b=10),
                    height=300,
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False),
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            else:
                st.info("No token usage data yet.")

    # Recent signups
    st.markdown(f"**Recent Sign-ups**")
    recent_users = sorted(users, key=lambda u: u.get("created_at", ""), reverse=True)[:10]
    if recent_users:
        for u in recent_users:
            role = u.get("role", "viewer")
            badge_class = f"badge-{role}" if role != "super_admin" else "badge-super"
            created = _format_time(u.get("created_at"))
            company = u.get("company", "")
            company_str = f" — {company}" if company else ""
            st.markdown(f"""<div class="user-row" style="display:flex;align-items:center;justify-content:space-between;">
                <div>
                    <span style="color:{C_TEXT};font-weight:600;">{u.get('full_name', 'Unknown')}</span>
                    <span style="color:{C_TEXT2};font-size:0.85rem;margin-left:8px;">{u.get('email', '')}{company_str}</span>
                </div>
                <div>
                    <span class="badge {badge_class}">{role}</span>
                    <span style="color:{C_TEXT2};font-size:0.8rem;margin-left:12px;">{created}</span>
                </div>
            </div>""", unsafe_allow_html=True)
    else:
        st.info("No users yet. Share the app link with your team to get started!")


# =====================================================================
#  TAB 2 — USERS
# =====================================================================
def _render_users_tab():
    """User management tab with real data."""
    st.subheader("User Management")

    users = get_all_users()

    # Filter bar
    col_search, col_role, col_status = st.columns([2, 1, 1])
    with col_search:
        search = st.text_input("Search users", placeholder="Name or email...", key="user_search",
                               label_visibility="collapsed")
    with col_role:
        role_filter = st.selectbox("Role", ["All", "super_admin", "admin", "analyst", "viewer"],
                                   key="user_role_filter")
    with col_status:
        status_filter = st.selectbox("Status", ["All", "active", "inactive"], key="user_status_filter")

    # Apply filters
    filtered = users
    if search:
        search_lower = search.lower()
        filtered = [u for u in filtered
                    if search_lower in u.get("full_name", "").lower()
                    or search_lower in u.get("email", "").lower()]
    if role_filter != "All":
        filtered = [u for u in filtered if u.get("role") == role_filter]
    if status_filter != "All":
        filtered = [u for u in filtered if u.get("status") == status_filter]

    # Summary
    st.markdown(f"<p style='color:{C_TEXT2};font-size:0.85rem;'>Showing {len(filtered)} of {len(users)} users</p>",
                unsafe_allow_html=True)

    # User table
    for idx, user in enumerate(filtered):
        role = user.get("role", "viewer")
        status = user.get("status", "active")
        badge_role = f"badge-{role}" if role != "super_admin" else "badge-super"
        badge_status = "badge-active" if status == "active" else "badge-inactive"
        tokens = user.get("token_usage", 0)
        last_login = _format_time(user.get("last_login"))
        created = _format_time(user.get("created_at"))
        company = user.get("company", "")

        col1, col2, col3, col4, col5, col6 = st.columns([2.5, 1.5, 1.2, 1.2, 1, 1])

        with col1:
            st.markdown(f"""<div>
                <span style="color:{C_TEXT};font-weight:600;">{user.get('full_name', 'Unknown')}</span><br>
                <span style="color:{C_TEXT2};font-size:0.8rem;">{user.get('email', '')}</span>
                {"<br><span style='color:" + C_TEXT2 + ";font-size:0.75rem;'>" + company + "</span>" if company else ""}
            </div>""", unsafe_allow_html=True)

        with col2:
            new_role = st.selectbox(
                "Role",
                options=["viewer", "analyst", "admin", "super_admin"],
                index=["viewer", "analyst", "admin", "super_admin"].index(role),
                key=f"role_{user.get('id', idx)}",
                label_visibility="collapsed"
            )
            if new_role != role:
                update_user_role(user.get("id"), new_role)
                st.rerun()

        with col3:
            st.markdown(f"""<div style="text-align:center;">
                <span style="color:{C_TURQUOISE};font-weight:600;">{_fmt_tokens(tokens)}</span><br>
                <span style="color:{C_TEXT2};font-size:0.7rem;">tokens</span>
            </div>""", unsafe_allow_html=True)

        with col4:
            st.markdown(f"""<div style="text-align:center;">
                <span style="color:{C_TEXT};font-size:0.85rem;">{last_login}</span><br>
                <span style="color:{C_TEXT2};font-size:0.7rem;">last login</span>
            </div>""", unsafe_allow_html=True)

        with col5:
            st.markdown(f'<span class="badge {badge_status}">{status}</span>', unsafe_allow_html=True)

        with col6:
            is_active = status == "active"
            btn_label = "Deactivate" if is_active else "Activate"
            if st.button(btn_label, key=f"toggle_{user.get('id', idx)}", use_container_width=True):
                toggle_user_status(user.get("id"), not is_active)
                st.rerun()

        st.divider()


# =====================================================================
#  TAB 3 — TOKEN USAGE
# =====================================================================
def _render_token_usage_tab():
    """Detailed token usage analytics."""
    st.subheader("Token Usage Analytics")

    if not TOKEN_TRACKER:
        st.warning("Token tracker module not available.")
        return

    # Time range selector
    days = st.selectbox("Time Range", [7, 14, 30, 60, 90], index=2,
                        format_func=lambda d: f"Last {d} days", key="token_days")

    summary = get_token_summary(days)
    users = get_all_users()
    user_map = {u.get("id", ""): u.get("full_name", u.get("email", "Unknown")) for u in users}

    # KPI row
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Tokens", _fmt_tokens(summary.get("total_tokens", 0)))
    with col2:
        st.metric("Input Tokens", _fmt_tokens(summary.get("total_input", 0)))
    with col3:
        st.metric("Output Tokens", _fmt_tokens(summary.get("total_output", 0)))
    with col4:
        st.metric("Est. Cost (USD)", f"${summary.get('total_cost_usd', 0):.2f}")
    with col5:
        st.metric("API Requests", f"{summary.get('total_requests', 0):,}")

    if PLOTLY_AVAILABLE:
        col1, col2 = st.columns(2)

        # Daily trend chart
        with col1:
            st.markdown("**Daily Token Consumption**")
            daily = summary.get("daily_trend", [])
            if daily:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=[d["date"] for d in daily],
                    y=[d["tokens"] for d in daily],
                    mode='lines+markers',
                    line=dict(color=C_TURQUOISE, width=2),
                    marker=dict(size=6),
                    fill='tozeroy',
                    fillcolor='rgba(108,185,182,0.1)',
                    hovertemplate="<b>%{x}</b><br>Tokens: %{y:,.0f}<extra></extra>"
                ))
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color=C_TEXT, size=11),
                    margin=dict(l=0, r=0, t=10, b=30),
                    height=300,
                    xaxis=dict(showgrid=False),
                    yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            else:
                st.info("No data for this period.")

        # By model breakdown
        with col2:
            st.markdown("**Usage by Model**")
            by_model = summary.get("by_model", {})
            if by_model:
                models = list(by_model.keys())
                tokens = [by_model[m]["tokens"] for m in models]
                colors = [C_TURQUOISE, C_ACCENT, C_GREEN, C_ORANGE, C_RED]

                fig = go.Figure(data=[go.Pie(
                    labels=models,
                    values=tokens,
                    hole=0.55,
                    marker=dict(colors=colors[:len(models)]),
                    textinfo='label+percent',
                    textfont=dict(size=11, color=C_TEXT),
                    hovertemplate="<b>%{label}</b><br>Tokens: %{value:,.0f}<br>%{percent}<extra></extra>"
                )])
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color=C_TEXT, size=11),
                    margin=dict(l=0, r=0, t=10, b=10),
                    height=300,
                    showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            else:
                st.info("No data for this period.")

        # By action breakdown
        st.markdown("**Usage by Action Type**")
        by_action = summary.get("by_action", {})
        if by_action:
            actions = list(by_action.keys())
            tokens = [by_action[a]["tokens"] for a in actions]
            requests = [by_action[a]["requests"] for a in actions]
            costs = [round(by_action[a]["cost"], 4) for a in actions]

            fig = go.Figure(data=[
                go.Bar(
                    x=actions,
                    y=tokens,
                    marker=dict(color=C_ACCENT, opacity=0.85),
                    text=[_fmt_tokens(t) for t in tokens],
                    textposition='outside',
                    hovertemplate="<b>%{x}</b><br>Tokens: %{y:,.0f}<extra></extra>"
                )
            ])
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color=C_TEXT, size=11),
                margin=dict(l=0, r=0, t=10, b=30),
                height=280,
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # Per-user breakdown table
    st.markdown("**Per-User Token Breakdown**")
    by_user = summary.get("by_user", {})
    if by_user:
        rows = []
        for uid, data in by_user.items():
            name = user_map.get(uid, uid[:16])
            rows.append({
                "User": name,
                "Tokens": f"{data['tokens']:,}",
                "Requests": data["requests"],
                "Est. Cost": f"${data['cost']:.4f}",
                "Avg/Request": f"{data['tokens'] // max(data['requests'], 1):,}",
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No token usage recorded yet.")


# =====================================================================
#  TAB 4 — AUDIT LOG
# =====================================================================
def _render_audit_log_tab():
    """Render audit log with real data from audit_logger."""
    st.subheader("Audit Log")

    if not AUDIT_AVAILABLE:
        st.warning("Audit logger module not available.")
        return

    # Filters
    col1, col2, col3 = st.columns([1.5, 1, 1])

    with col1:
        days = st.slider("Days back", 1, 90, 7, key="audit_days")

    with col2:
        action_filter = st.selectbox(
            "Action Type",
            options=["All", "search", "analyze", "export", "login", "dcf_run", "view_report"],
            key="audit_action"
        )

    with col3:
        if st.button("Export CSV", use_container_width=True):
            start = datetime.now() - timedelta(days=days)
            logs = get_audit_log(start_date=start, limit=5000)
            if logs:
                df = pd.DataFrame(logs)
                csv = df.to_csv(index=False)
                st.download_button("Download", csv,
                                   f"audit_log_{datetime.now().strftime('%Y%m%d')}.csv",
                                   "text/csv")

    # Get logs
    start = datetime.now() - timedelta(days=days)
    logs = get_audit_log(start_date=start, limit=200)

    if action_filter != "All":
        logs = [l for l in logs if l.get("action") == action_filter]

    if not logs:
        st.info("No audit log entries for this period.")
        return

    st.markdown(f"<p style='color:{C_TEXT2};font-size:0.85rem;'>Showing {len(logs)} entries</p>",
                unsafe_allow_html=True)

    users = get_all_users()
    user_map = {u.get("id", ""): u.get("full_name", u.get("email", "Unknown")) for u in users}

    # Table header
    col1, col2, col3, col4, col5 = st.columns([2, 1.5, 1.2, 2, 2])
    with col1:
        st.markdown(f"<b style='color:{C_TURQUOISE};font-size:0.85rem;'>Timestamp</b>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<b style='color:{C_TURQUOISE};font-size:0.85rem;'>User</b>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<b style='color:{C_TURQUOISE};font-size:0.85rem;'>Action</b>", unsafe_allow_html=True)
    with col4:
        st.markdown(f"<b style='color:{C_TURQUOISE};font-size:0.85rem;'>Resource</b>", unsafe_allow_html=True)
    with col5:
        st.markdown(f"<b style='color:{C_TURQUOISE};font-size:0.85rem;'>Details</b>", unsafe_allow_html=True)

    st.divider()

    for log in logs[:100]:
        col1, col2, col3, col4, col5 = st.columns([2, 1.5, 1.2, 2, 2])

        with col1:
            ts = log.get("timestamp", "")[:19]
            st.text(ts)
        with col2:
            uid = log.get("user_id", "")
            name = user_map.get(uid, log.get("user_email", uid[:12]))
            st.text(name)
        with col3:
            action = log.get("action", "")
            color = {
                "search": C_ACCENT,
                "analyze": C_TURQUOISE,
                "export": C_GREEN,
                "login": C_TEXT2,
                "dcf_run": C_ORANGE,
            }.get(action, C_TEXT)
            st.markdown(f'<span style="color:{color}">{action}</span>', unsafe_allow_html=True)
        with col4:
            st.text(log.get("resource", log.get("ticker", "")))
        with col5:
            details = log.get("details", log.get("metadata", ""))
            if isinstance(details, dict):
                details = str(details)[:80]
            st.caption(str(details)[:80])


# =====================================================================
#  HELPERS
# =====================================================================
def _fmt_tokens(n: int) -> str:
    """Format token count for display."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _pct(part: int, total: int) -> str:
    """Calculate percentage."""
    if total == 0:
        return "0"
    return f"{(part / total) * 100:.0f}"


def _is_recent(iso_str: str, days: int = 7) -> bool:
    """Check if an ISO date string is within the last N days."""
    if not iso_str:
        return False
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00").replace("+00:00", ""))
        return dt > datetime.now() - timedelta(days=days)
    except Exception:
        return False


def _format_time(iso_str: str) -> str:
    """Format an ISO datetime to a human-readable relative time."""
    if not iso_str:
        return "Never"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00").replace("+00:00", ""))
        diff = datetime.now() - dt
        if diff.total_seconds() < 60:
            return "Just now"
        if diff.total_seconds() < 3600:
            return f"{int(diff.total_seconds() / 60)}m ago"
        if diff.total_seconds() < 86400:
            return f"{int(diff.total_seconds() / 3600)}h ago"
        if diff.days == 1:
            return "Yesterday"
        if diff.days < 7:
            return f"{diff.days}d ago"
        return dt.strftime("%b %d, %Y")
    except Exception:
        return str(iso_str)[:10]
