"""TAM Research — Admin Panel."""
import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
from auth.rbac import require_role, is_super_admin
import plotly.graph_objects as go
import plotly.express as px

# TAM brand colors
C_BG = "#070B14"
C_TEXT = "#E6EDF3"
C_TEXT2 = "#8B949E"
C_ACCENT = "#1A6DB6"
C_DEEP = "#222F62"
C_TURQUOISE = "#6CB9B6"
C_GREEN = "#22C55E"
C_RED = "#EF4444"
C_CARD = "rgba(26,38,78,0.15)"
C_GLASS = "rgba(34,47,98,0.12)"
C_BORDER = "rgba(108,185,182,0.08)"


def render_admin():
    """Render the admin panel."""
    require_role("super_admin", "admin")

    st.set_page_config(page_title="Admin — TAM Research", layout="wide")

    # TAM Liquid Glass CSS
    st.markdown(f"""<style>
    [data-testid="stAppViewContainer"] {{
        background: linear-gradient(135deg, {C_BG} 0%, #0f1829 100%);
    }}

    .glass-card {{
        background: {C_GLASS};
        backdrop-filter: blur(24px);
        -webkit-backdrop-filter: blur(24px);
        border: 1px solid {C_BORDER};
        border-radius: 16px;
        padding: 24px;
    }}

    .metric-card {{
        background: {C_GLASS};
        border: 1px solid {C_BORDER};
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
    }}

    .table-container {{
        background: {C_GLASS};
        border: 1px solid {C_BORDER};
        border-radius: 12px;
        padding: 16px;
    }}
    </style>""", unsafe_allow_html=True)

    # Header
    st.markdown(f"""<div style="
        background: {C_GLASS};
        border-bottom: 1px solid {C_BORDER};
        padding: 20px;
        border-radius: 0;
        margin: -40px -40px 20px -40px;
    ">
        <h1 style="color:{C_TEXT};margin:0;font-size:2rem;">Admin Panel</h1>
        <p style="color:{C_TEXT2};margin:4px 0 0 0;">System administration and user management</p>
    </div>""", unsafe_allow_html=True)

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Users", "Usage Stats", "System Config", "Audit Log"])

    with tab1:
        _render_users_tab()

    with tab2:
        _render_usage_stats_tab()

    with tab3:
        _render_system_config_tab()

    with tab4:
        _render_audit_log_tab()


def _render_users_tab():
    """Render Users management tab."""
    st.subheader("User Management")

    col1, col2 = st.columns([3, 1])

    with col2:
        if st.button("+ Invite User", use_container_width=True, type="primary"):
            st.session_state.show_invite_form = True

    # Invite form
    if st.session_state.get("show_invite_form"):
        st.markdown(f"""<div class="glass-card">""", unsafe_allow_html=True)
        st.markdown("**Invite New User**")

        invite_email = st.text_input("Email address", placeholder="analyst@tamcapital.sa", key="invite_email")
        invite_role = st.selectbox("Role",
            options=["analyst", "admin", "viewer"],
            index=0,
            key="invite_role"
        )

        col_invite, col_cancel = st.columns(2)
        with col_invite:
            if st.button("Send Invite", use_container_width=True):
                if invite_email:
                    _send_user_invite(invite_email, invite_role)
                    st.success(f"Invitation sent to {invite_email}")
                    st.session_state.show_invite_form = False
                    st.rerun()
                else:
                    st.warning("Enter an email address")
        with col_cancel:
            if st.button("Cancel", use_container_width=True):
                st.session_state.show_invite_form = False
                st.rerun()

        st.markdown("""</div>""", unsafe_allow_html=True)

    # Users table
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**All Users**")

    # Mock user data (replace with DB query in production)
    users_data = _get_mock_users()

    # Create dataframe
    df_users = pd.DataFrame(users_data)

    # Render table with editable roles
    st.markdown(f"""<div class="table-container">""", unsafe_allow_html=True)

    for idx, user in enumerate(users_data):
        col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 1.5, 1.5, 1, 1])

        with col1:
            st.text(user["email"])
        with col2:
            st.text(user["full_name"])
        with col3:
            role = st.selectbox("Role",
                options=["viewer", "analyst", "admin", "super_admin"],
                index=["viewer", "analyst", "admin", "super_admin"].index(user["role"]),
                key=f"role_{idx}",
                label_visibility="collapsed"
            )
            if role != user["role"]:
                _update_user_role(user["id"], role)
        with col4:
            st.text(user["last_login"])
        with col5:
            status_color = C_GREEN if user["status"] == "Active" else C_RED
            st.markdown(f"""<span style="color:{status_color}">●</span> {user["status"]}""",
                       unsafe_allow_html=True)
        with col6:
            active = user["status"] == "Active"
            if st.button("Deactivate" if active else "Activate",
                        key=f"toggle_{idx}",
                        use_container_width=True):
                _toggle_user_status(user["id"], not active)
                st.rerun()

    st.markdown("""</div>""", unsafe_allow_html=True)


def _render_usage_stats_tab():
    """Render Usage Statistics tab."""
    st.subheader("Usage Analytics")

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)

    stats = _get_mock_usage_stats()

    with col1:
        st.metric("Total Reports Generated", stats["total_reports"], "+12 this week")
    with col2:
        st.metric("Weekly Active Users", stats["weekly_active"], "-2 from last week")
    with col3:
        st.metric("Reports This Month", stats["monthly_reports"], "+8%")
    with col4:
        st.metric("Avg Export/Day", stats["avg_export"], "+15%")

    # Charts
    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    # Top 10 tickers chart
    with col1:
        st.markdown("**Top 10 Researched Tickers**")
        ticker_data = _get_mock_ticker_data()

        fig = go.Figure(data=[
            go.Bar(
                y=ticker_data["ticker"],
                x=ticker_data["count"],
                orientation='h',
                marker=dict(color=C_TURQUOISE),
                text=ticker_data["count"],
                textposition='outside',
            )
        ])

        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color=C_TEXT, size=12),
            margin=dict(l=0, r=0, t=0, b=0),
            height=400,
            xaxis=dict(showgrid=False, zeroline=False, showline=False),
            yaxis=dict(showgrid=False, zeroline=False, showline=False),
        )

        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # Daily active users chart
    with col2:
        st.markdown("**Daily Active Users (Last 30 Days)**")
        dau_data = _get_mock_dau_data()

        fig = go.Figure(data=[
            go.Scatter(
                x=dau_data["date"],
                y=dau_data["users"],
                mode='lines',
                line=dict(color=C_ACCENT, width=3),
                fill='tozeroy',
                fillcolor='rgba(26,109,182,0.1)',
            )
        ])

        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color=C_TEXT, size=12),
            margin=dict(l=0, r=0, t=0, b=0),
            height=400,
            xaxis=dict(showgrid=False, zeroline=False),
            yaxis=dict(showgrid=False, zeroline=False),
        )

        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # Feature adoption
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**Feature Adoption**")

    col1, col2, col3, col4, col5 = st.columns(5)

    adoption = _get_mock_feature_adoption()

    with col1:
        st.metric("DCF Runs", adoption["dcf_runs"])
    with col2:
        st.metric("Reports Generated", adoption["reports"])
    with col3:
        st.metric("Exports Created", adoption["exports"])
    with col4:
        st.metric("Alerts Set", adoption["alerts"])
    with col5:
        st.metric("Notes Created", adoption["notes"])


def _render_system_config_tab():
    """Render System Configuration tab."""
    st.subheader("System Configuration")

    st.markdown(f"""<div class="glass-card">""", unsafe_allow_html=True)

    # API Keys
    st.markdown("**API Keys & Services**")

    # Mock API key status
    api_keys = {
        "Anthropic (Claude)": ("sk-ant-...7w", True),
        "Perplexity": ("ppl-...abc", True),
        "OpenAI": ("sk-...xyz", False),
        "Google": ("AIza...def", True),
    }

    for service, (key_mask, is_set) in api_keys.items():
        col1, col2, col3 = st.columns([2, 2, 1])

        status_color = C_GREEN if is_set else C_RED
        status_text = "Active" if is_set else "Not Set"

        with col1:
            st.text(service)
        with col2:
            if is_set:
                st.text(key_mask)
            else:
                st.text("—")
        with col3:
            st.markdown(f"""<span style="color:{status_color}">●</span> {status_text}""",
                       unsafe_allow_html=True)

    st.markdown("""</div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(f"""<div class="glass-card">""", unsafe_allow_html=True)

    # Model Configuration
    st.markdown("**Model Configuration**")

    col1, col2 = st.columns([1, 1])

    with col1:
        default_model = st.selectbox(
            "Default Research Model",
            options=["claude-opus-4", "claude-sonnet-4", "gpt-4o", "gpt-4-turbo"],
            index=0,
            key="default_model"
        )

    with col2:
        fallback_model = st.selectbox(
            "Fallback Model",
            options=["claude-opus-4", "claude-sonnet-4", "gpt-4o-mini", "gpt-4-turbo"],
            index=2,
            key="fallback_model"
        )

    if st.button("Save Model Configuration", use_container_width=True):
        st.success("Model configuration updated")

    st.markdown("""</div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(f"""<div class="glass-card">""", unsafe_allow_html=True)

    # Alert Thresholds
    st.markdown("**Alert Thresholds**")

    col1, col2 = st.columns(2)

    with col1:
        price_threshold = st.number_input(
            "Price Change Alert Threshold (%)",
            min_value=0.5,
            max_value=50.0,
            value=5.0,
            step=0.5,
            key="price_threshold"
        )

    with col2:
        volume_multiplier = st.number_input(
            "Volume Multiplier Alert Threshold",
            min_value=1.0,
            max_value=10.0,
            value=2.5,
            step=0.5,
            key="volume_threshold"
        )

    if st.button("Save Alert Thresholds", use_container_width=True):
        st.success("Alert thresholds updated")

    st.markdown("""</div>""", unsafe_allow_html=True)


def _render_audit_log_tab():
    """Render Audit Log tab."""
    st.subheader("Audit Log")

    col1, col2, col3, col4 = st.columns([1.5, 1, 1.5, 1.5])

    with col1:
        date_range = st.date_input(
            "Date Range",
            value=(datetime.now() - timedelta(days=7), datetime.now()),
            key="audit_date_range"
        )

    with col2:
        action_filter = st.selectbox(
            "Action Type",
            options=["All", "Create", "Update", "Delete", "Export", "Login"],
            key="audit_action"
        )

    with col3:
        user_filter = st.selectbox(
            "User",
            options=["All", "mmalki@tamcapital.sa", "analyst1@tamcapital.sa", "analyst2@tamcapital.sa"],
            key="audit_user"
        )

    with col4:
        if st.button("Export CSV", use_container_width=True):
            _export_audit_log()

    st.markdown("<br>", unsafe_allow_html=True)

    # Audit log table
    audit_logs = _get_mock_audit_logs()

    # Filter by date range
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
        audit_logs = [log for log in audit_logs
                     if start_date <= datetime.fromisoformat(log["timestamp"]).date() <= end_date]

    # Filter by action
    if action_filter != "All":
        audit_logs = [log for log in audit_logs if log["action"] == action_filter]

    # Filter by user
    if user_filter != "All":
        audit_logs = [log for log in audit_logs if log["user"] == user_filter]

    # Display table
    df_audit = pd.DataFrame(audit_logs)

    st.markdown(f"""<div class="table-container">""", unsafe_allow_html=True)

    # Header
    col1, col2, col3, col4, col5 = st.columns([2, 1.5, 1.2, 2.5, 1.8])
    with col1:
        st.markdown(f"<b style='color:{C_TURQUOISE}'>Timestamp</b>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<b style='color:{C_TURQUOISE}'>User</b>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<b style='color:{C_TURQUOISE}'>Action</b>", unsafe_allow_html=True)
    with col4:
        st.markdown(f"<b style='color:{C_TURQUOISE}'>Resource</b>", unsafe_allow_html=True)
    with col5:
        st.markdown(f"<b style='color:{C_TURQUOISE}'>Details</b>", unsafe_allow_html=True)

    st.divider()

    # Rows
    for log in audit_logs[-50:]:  # Show last 50 entries
        col1, col2, col3, col4, col5 = st.columns([2, 1.5, 1.2, 2.5, 1.8])

        with col1:
            st.text(log["timestamp"])
        with col2:
            st.text(log["user"].split("@")[0])
        with col3:
            action_color = {
                "Create": C_GREEN,
                "Update": C_ACCENT,
                "Delete": C_RED,
                "Export": C_TURQUOISE,
                "Login": C_TEXT2,
            }.get(log["action"], C_TEXT)
            st.markdown(f"""<span style="color:{action_color}">{log["action"]}</span>""",
                       unsafe_allow_html=True)
        with col4:
            st.text(log["resource"])
        with col5:
            st.caption(log["details"])

    st.markdown("""</div>""", unsafe_allow_html=True)


# Mock data functions
def _get_mock_users():
    """Return mock user data."""
    return [
        {
            "id": "user_1",
            "email": "mmalki@tamcapital.sa",
            "full_name": "Mohammed Malki",
            "role": "super_admin",
            "last_login": "Today, 9:42 AM",
            "status": "Active"
        },
        {
            "id": "user_2",
            "email": "analyst1@tamcapital.sa",
            "full_name": "Ahmed Al-Rashid",
            "role": "analyst",
            "last_login": "Today, 8:15 AM",
            "status": "Active"
        },
        {
            "id": "user_3",
            "email": "analyst2@tamcapital.sa",
            "full_name": "Fatima Al-Suwaidi",
            "role": "analyst",
            "last_login": "Yesterday, 3:30 PM",
            "status": "Active"
        },
        {
            "id": "user_4",
            "email": "viewer@tamcapital.sa",
            "full_name": "Omar Al-Kaabi",
            "role": "viewer",
            "last_login": "2 days ago",
            "status": "Active"
        },
        {
            "id": "user_5",
            "email": "inactive@tamcapital.sa",
            "full_name": "Removed User",
            "role": "analyst",
            "last_login": "30 days ago",
            "status": "Inactive"
        },
    ]


def _get_mock_usage_stats():
    """Return mock usage statistics."""
    return {
        "total_reports": 487,
        "weekly_active": 18,
        "monthly_reports": 156,
        "avg_export": 12
    }


def _get_mock_ticker_data():
    """Return mock ticker research data."""
    return {
        "ticker": ["SABIC", "SAB", "ZAIN", "ALRAJHI", "2222", "1214", "4050", "6020", "4030", "7020"],
        "count": [124, 89, 76, 65, 58, 52, 48, 44, 41, 38]
    }


def _get_mock_dau_data():
    """Return mock daily active users data."""
    dates = [(datetime.now() - timedelta(days=i)).strftime("%b %d") for i in range(29, -1, -1)]
    users = [12, 15, 18, 16, 19, 21, 20, 18, 22, 25, 24, 26, 28, 30, 29, 31, 32, 30, 28, 25, 26, 27, 25, 23, 22, 24, 26, 28, 27, 29]
    return {"date": dates, "users": users}


def _get_mock_feature_adoption():
    """Return mock feature adoption stats."""
    return {
        "dcf_runs": 234,
        "reports": 487,
        "exports": 156,
        "alerts": 89,
        "notes": 342
    }


def _get_mock_audit_logs():
    """Return mock audit logs."""
    now = datetime.now()
    logs = []

    actions = ["Create", "Update", "Delete", "Export", "Login"]
    resources = ["Report", "Watchlist", "Alert", "Portfolio", "User"]
    users = ["mmalki@tamcapital.sa", "analyst1@tamcapital.sa", "analyst2@tamcapital.sa"]
    details = [
        "Generated DCF report for SABIC",
        "Updated user role to analyst",
        "Exported portfolio data to CSV",
        "Created price alert threshold",
        "Added stock to watchlist"
    ]

    for i in range(100):
        log_time = now - timedelta(hours=i)
        logs.append({
            "timestamp": log_time.strftime("%Y-%m-%d %H:%M:%S"),
            "user": users[i % len(users)],
            "action": actions[i % len(actions)],
            "resource": resources[i % len(resources)],
            "details": details[i % len(details)]
        })

    return logs


def _send_user_invite(email: str, role: str):
    """Send invitation email to new user."""
    # TODO: Integrate with Supabase or email service
    pass


def _update_user_role(user_id: str, new_role: str):
    """Update user role in database."""
    # TODO: Integrate with Supabase
    pass


def _toggle_user_status(user_id: str, active: bool):
    """Activate or deactivate user."""
    # TODO: Integrate with Supabase
    pass


def _export_audit_log():
    """Export audit log to CSV."""
    audit_logs = _get_mock_audit_logs()
    df = pd.DataFrame(audit_logs)
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name=f"audit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
