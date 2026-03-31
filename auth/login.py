"""TAM Capital — Authentication & Login Page."""
import streamlit as st

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

def render_login_page():
    """Render the TAM Liquid Glass login page. Returns True if user is authenticated."""
    # Check if already logged in
    if st.session_state.get("authenticated"):
        return True

    # CSS for login page (same TAM Liquid Glass but centered card)
    st.markdown("""<style>
    [data-testid="stAppViewContainer"] {
        display: flex; align-items: center; justify-content: center;
        min-height: 100vh;
    }
    </style>""", unsafe_allow_html=True)

    # Center column
    col1, center, col3 = st.columns([1, 2, 1])
    with center:
        # TAM Logo
        # Glass card container
        st.markdown(f'''<div style="
            background: {C_GLASS};
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            border: 1px solid {C_BORDER};
            border-radius: 20px;
            padding: 40px 32px;
            text-align: center;
            margin: 40px auto;
            max-width: 420px;
        ">
            <h2 style="color:{C_TEXT};font-weight:700;margin-bottom:4px;font-size:1.4rem;">
                TAM Research</h2>
            <p style="color:{C_TEXT2};font-size:0.85rem;margin-bottom:24px;">
                Investment Research & Analytics Platform</p>
        </div>''', unsafe_allow_html=True)

        # Login form
        login_method = st.radio("Login method", ["Email & Password", "Magic Link"],
                                horizontal=True, label_visibility="collapsed")

        email = st.text_input("Email", placeholder="name@tamcapital.sa", key="login_email")

        if login_method == "Email & Password":
            password = st.text_input("Password", type="password", key="login_password")

            col_login, col_forgot = st.columns([2, 1])
            with col_login:
                if st.button("Sign In", key="login_btn", type="primary", use_container_width=True):
                    if email and password:
                        success = _authenticate_password(email, password)
                        if success:
                            st.rerun()
                        else:
                            st.error("Invalid credentials")
                    else:
                        st.warning("Please enter email and password")
            with col_forgot:
                if st.button("Forgot?", key="forgot_btn", use_container_width=True):
                    if email:
                        _send_password_reset(email)
                        st.success("Reset email sent")
                    else:
                        st.warning("Enter your email first")
        else:
            if st.button("Send Magic Link", key="magic_btn", type="primary", use_container_width=True):
                if email:
                    _send_magic_link(email)
                    st.success("Check your inbox for the login link")
                else:
                    st.warning("Please enter your email")

        # Disclaimer
        st.markdown(f'''<p style="color:{C_TEXT2};font-size:0.65rem;margin-top:20px;text-align:center;">
            TAM Capital | CMA Regulated<br>Confidential — Internal Use Only
        </p>''', unsafe_allow_html=True)

    return False


def _authenticate_password(email: str, password: str) -> bool:
    """Authenticate with email/password via Supabase Auth."""
    try:
        from data.supabase_client import get_client, SUPABASE_AVAILABLE
        if not SUPABASE_AVAILABLE:
            # Fallback: allow admin login with env-based password
            import os
            admin_email = os.getenv("ADMIN_EMAIL", "mmalki@tamcapital.sa")
            admin_pass = os.getenv("ADMIN_PASSWORD", "tamcapital2026")
            if email == admin_email and password == admin_pass:
                st.session_state.authenticated = True
                st.session_state.user = {
                    "id": "admin-local",
                    "email": admin_email,
                    "full_name": "Mohammed Malki",
                    "role": "super_admin",
                }
                return True
            return False

        client = get_client()
        response = client.auth.sign_in_with_password({"email": email, "password": password})
        if response.user:
            # Fetch user profile from users table
            user_data = client.table("users").select("*").eq("email", email).single().execute()
            st.session_state.authenticated = True
            st.session_state.user = user_data.data if user_data.data else {
                "id": response.user.id,
                "email": email,
                "full_name": email.split("@")[0],
                "role": "analyst",
            }
            st.session_state.auth_token = response.session.access_token
            return True
    except Exception as e:
        st.error(f"Authentication error: {str(e)}")
    return False


def _send_magic_link(email: str):
    """Send a magic link via Supabase Auth."""
    try:
        from data.supabase_client import get_client, SUPABASE_AVAILABLE
        if SUPABASE_AVAILABLE:
            client = get_client()
            client.auth.sign_in_with_otp({"email": email})
    except Exception:
        pass


def _send_password_reset(email: str):
    """Send password reset email."""
    try:
        from data.supabase_client import get_client, SUPABASE_AVAILABLE
        if SUPABASE_AVAILABLE:
            client = get_client()
            client.auth.reset_password_email(email)
    except Exception:
        pass


def get_current_user() -> dict | None:
    """Get the currently logged-in user."""
    return st.session_state.get("user")


def logout():
    """Clear session and log out."""
    try:
        from data.supabase_client import get_client, SUPABASE_AVAILABLE
        if SUPABASE_AVAILABLE:
            client = get_client()
            client.auth.sign_out()
    except Exception:
        pass
    for key in ["authenticated", "user", "auth_token"]:
        st.session_state.pop(key, None)


def is_authenticated() -> bool:
    """Check if user is authenticated."""
    return st.session_state.get("authenticated", False)
