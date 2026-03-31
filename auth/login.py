"""TAM Capital — Authentication, Login & Sign-Up Page."""
import streamlit as st
import json
import os
import hashlib
import uuid
from datetime import datetime
from pathlib import Path

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
C_GLASS = "rgba(34,47,98,0.18)"
C_BORDER = "rgba(108,185,182,0.12)"

# --- Local user store (JSON fallback when Supabase not available) ---
USERS_FILE = Path(__file__).parent.parent / "data" / "users.json"


def _load_users() -> list:
    """Load users from local JSON store."""
    if USERS_FILE.exists():
        try:
            with open(USERS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _save_users(users: list):
    """Save users to local JSON store."""
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2, default=str)


def _hash_password(password: str) -> str:
    """Hash a password with SHA-256 + salt."""
    salt = "tam-capital-2026"
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def _find_user_by_email(email: str) -> dict | None:
    """Find a user by email in local store."""
    users = _load_users()
    for u in users:
        if u.get("email", "").lower() == email.lower():
            return u
    return None


def _ensure_admin_exists():
    """Ensure the admin user exists in the local store."""
    admin_email = os.getenv("ADMIN_EMAIL", "mmalki@tamcapital.sa")
    admin_pass = os.getenv("ADMIN_PASSWORD", "tamcapital2026")
    if not _find_user_by_email(admin_email):
        users = _load_users()
        users.append({
            "id": "admin-local",
            "email": admin_email,
            "full_name": "Mohammed Malki",
            "role": "super_admin",
            "password_hash": _hash_password(admin_pass),
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "last_login": None,
            "token_usage": 0,
        })
        _save_users(users)


# =========================================================================
# LOGIN PAGE — Main Render
# =========================================================================

def render_login_page():
    """Render the TAM login / signup page with polished dark theme."""
    if st.session_state.get("authenticated"):
        return True

    _ensure_admin_exists()

    # --- Full-page CSS ---
    st.markdown(f"""<style>
    /* Hide Streamlit chrome */
    #MainMenu, footer, .stDeployButton, div[data-testid="stToolbar"] {{display:none!important;}}
    header[data-testid="stHeader"] {{background:transparent!important;}}

    .stApp {{
        background: linear-gradient(160deg, {C_BG} 0%, #0E1A2E 50%, {C_BG} 100%) !important;
    }}

    /* Center content vertically */
    [data-testid="stAppViewContainer"] > .main > div {{
        display: flex; flex-direction: column; align-items: center;
        justify-content: center; min-height: 85vh;
    }}

    /* Input fields */
    .stTextInput input {{
        color: {C_TEXT} !important;
        background: rgba(14, 26, 46, 0.6) !important;
        border: 1px solid rgba(108,185,182,0.15) !important;
        border-radius: 8px !important;
        padding: 0.6rem 0.8rem !important;
        font-size: 0.9rem !important;
        caret-color: {C_TURQUOISE} !important;
    }}
    .stTextInput input:focus {{
        border-color: {C_TURQUOISE} !important;
        box-shadow: 0 0 0 2px rgba(108,185,182,0.15) !important;
    }}
    .stTextInput input::placeholder {{
        color: rgba(139,148,158,0.6) !important;
    }}
    .stTextInput label {{
        color: {C_TEXT2} !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
    }}
    .stTextInput .st-emotion-cache-1aehpvj {{
        color: {C_TEXT2} !important;
    }}

    /* Primary button */
    .stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, {C_ACCENT}, {C_TURQUOISE}) !important;
        border: none !important; color: white !important;
        border-radius: 8px !important; font-weight: 600 !important;
        padding: 0.6rem 1.5rem !important; font-size: 0.9rem !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 2px 12px rgba(26,109,182,0.3) !important;
    }}
    .stButton > button[kind="primary"]:hover {{
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 20px rgba(26,109,182,0.45) !important;
    }}
    /* Secondary / ghost button */
    .stButton > button[kind="secondary"],
    .stButton > button:not([kind="primary"]) {{
        background: transparent !important;
        border: 1px solid rgba(108,185,182,0.2) !important;
        color: {C_TEXT2} !important; border-radius: 8px !important;
        font-size: 0.85rem !important;
    }}
    .stButton > button[kind="secondary"]:hover,
    .stButton > button:not([kind="primary"]):hover {{
        border-color: {C_TURQUOISE} !important;
        color: {C_TURQUOISE} !important;
    }}

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0; justify-content: center;
        background: rgba(14,26,46,0.4); border-radius: 10px;
        padding: 3px; border: 1px solid rgba(108,185,182,0.08);
    }}
    .stTabs [data-baseweb="tab"] {{
        flex: 1; justify-content: center; border-radius: 8px;
        color: {C_TEXT2} !important; font-weight: 500 !important;
        font-size: 0.85rem !important; padding: 8px 16px !important;
    }}
    .stTabs [aria-selected="true"] {{
        color: white !important;
        background: rgba(26,109,182,0.3) !important;
    }}
    .stTabs [data-baseweb="tab-highlight"] {{
        display: none !important;
    }}
    .stTabs [data-baseweb="tab-border"] {{
        display: none !important;
    }}

    /* Reduce spacing between elements */
    div[data-testid="stVerticalBlock"] > div {{gap: 0.25rem;}}
    </style>""", unsafe_allow_html=True)

    # --- Layout ---
    _, center, _ = st.columns([1.2, 2, 1.2])
    with center:
        # Logo + Title header
        st.markdown(f"""
        <div style="text-align:center; padding:20px 0 24px 0;">
            <div style="display:inline-block; width:48px; height:48px; border-radius:12px;
                        background:linear-gradient(135deg, {C_ACCENT}, {C_TURQUOISE});
                        line-height:48px; text-align:center; font-size:1.2rem; font-weight:700;
                        color:white; margin-bottom:14px;">T</div>
            <h2 style="color:{C_TEXT}; font-weight:700; margin:0 0 4px 0; font-size:1.35rem;">
                TAM Research Terminal</h2>
            <p style="color:{C_TEXT2}; font-size:0.82rem; margin:0;">
                AI-Powered Investment Research</p>
        </div>
        """, unsafe_allow_html=True)

        # Tabs
        tab_signin, tab_signup = st.tabs(["Sign In", "Create Account"])

        with tab_signin:
            _render_signin_form()

        with tab_signup:
            _render_signup_form()

        # Footer
        st.markdown(f"""
        <div style="text-align:center; padding:20px 0 0 0;">
            <p style="color:rgba(139,148,158,0.5); font-size:0.65rem; margin:0;">
                TAM Capital  ·  CMA Regulated  ·  Confidential</p>
        </div>
        """, unsafe_allow_html=True)

    return False


# =========================================================================
# SIGN IN FORM
# =========================================================================

def _render_signin_form():
    """Render the sign-in form."""
    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

    email = st.text_input("Email", placeholder="name@tamcapital.sa", key="login_email")
    password = st.text_input("Password", type="password", key="login_password")

    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

    if st.button("Sign In", key="login_btn", type="primary", use_container_width=True):
        if email and password:
            success = _authenticate_password(email, password)
            if success:
                st.rerun()
            else:
                st.error("Invalid email or password")
        else:
            st.warning("Please enter email and password")

    # Password reset section
    if st.session_state.get("reset_pending"):
        _render_reset_code_form()
    else:
        st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
        if st.button("Forgot password?", key="forgot_btn", use_container_width=True):
            if email:
                _send_password_reset(email)
            else:
                st.warning("Enter your email first")


# =========================================================================
# SIGN UP FORM
# =========================================================================

def _render_signup_form():
    """Render the sign-up / registration form with email verification."""
    # Import email verification
    try:
        from auth.email_verify import send_and_store, verify_code, is_email_verified
        EMAIL_VERIFY = True
    except ImportError:
        EMAIL_VERIFY = False

    # Check if we're in the verification step
    if st.session_state.get("verify_pending"):
        _render_verify_code_form()
        return

    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

    full_name = st.text_input("Full Name", placeholder="Ahmed Al-Rashid", key="signup_name")
    email = st.text_input("Work Email", placeholder="name@company.com", key="signup_email")
    company = st.text_input("Company / Organization", placeholder="TAM Capital", key="signup_company")
    password = st.text_input("Create Password", type="password", key="signup_password",
                             help="At least 8 characters")
    password2 = st.text_input("Confirm Password", type="password", key="signup_password2")

    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

    if st.button("Create Account", key="signup_btn", type="primary", use_container_width=True):
        # Validation
        if not full_name or not email or not password:
            st.warning("Please fill in all required fields")
            return
        if len(password) < 8:
            st.warning("Password must be at least 8 characters")
            return
        if password != password2:
            st.error("Passwords do not match")
            return

        # Check if email already exists
        if _find_user_by_email(email):
            st.error("An account with this email already exists. Please sign in.")
            return

        if EMAIL_VERIFY:
            # Store signup data temporarily and send verification email
            st.session_state["pending_signup"] = {
                "full_name": full_name,
                "email": email,
                "password": password,
                "company": company,
            }
            success, msg, dev_code = send_and_store(email)
            if success:
                st.session_state["verify_pending"] = True
                if dev_code:
                    st.session_state["dev_verify_code"] = dev_code
                st.rerun()
            else:
                st.error(f"Could not send verification email: {msg}")
        else:
            # No email verification — register directly
            success = _register_user(full_name, email, password, company)
            if success:
                st.success("Account created! You're now signed in.")
                st.rerun()
            else:
                st.error("Registration failed. Please try again.")


# =========================================================================
# EMAIL VERIFICATION CODE FORM
# =========================================================================

def _render_verify_code_form():
    """Render the email verification code entry form."""
    from auth.email_verify import verify_code, send_and_store

    pending = st.session_state.get("pending_signup", {})
    email = pending.get("email", "")

    st.markdown(f"""
    <div style="text-align:center; padding:8px 0 12px 0;">
        <div style="font-size:1.6rem; margin-bottom:8px;">📧</div>
        <h3 style="color:{C_TEXT}; font-size:1.1rem; margin:0 0 4px 0;">Check your inbox</h3>
        <p style="color:{C_TEXT2}; font-size:0.82rem; margin:0;">
            We sent a 6-digit code to <strong style="color:{C_TURQUOISE};">{email}</strong>
        </p>
    </div>
    """, unsafe_allow_html=True)

    dev_code = st.session_state.get("dev_verify_code")
    if dev_code:
        st.info(f"Dev mode — your code is: **{dev_code}**")

    code = st.text_input("Verification code", max_chars=6, key="verify_code_input",
                         placeholder="123456")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Verify", key="verify_btn", type="primary", use_container_width=True):
            if not code or len(code) != 6:
                st.warning("Please enter the 6-digit code")
                return
            success, msg = verify_code(email, code)
            if success:
                reg_success = _register_user(
                    pending["full_name"], pending["email"],
                    pending["password"], pending.get("company", ""),
                )
                if reg_success:
                    for key in ["verify_pending", "pending_signup", "dev_verify_code"]:
                        st.session_state.pop(key, None)
                    st.success("Email verified! You're now signed in.")
                    st.rerun()
                else:
                    st.error("Registration failed after verification.")
            else:
                st.error(msg)
    with col2:
        if st.button("Resend Code", key="resend_btn", use_container_width=True):
            success, msg, dev_code = send_and_store(email)
            if success:
                if dev_code:
                    st.session_state["dev_verify_code"] = dev_code
                st.success("New code sent!")
                st.rerun()
            else:
                st.error(f"Failed to resend: {msg}")

    if st.button("← Back to Sign Up", key="back_signup_btn"):
        for key in ["verify_pending", "pending_signup", "dev_verify_code"]:
            st.session_state.pop(key, None)
        st.rerun()


# =========================================================================
# PASSWORD RESET — now uses Resend (not just Supabase)
# =========================================================================

def _send_password_reset(email: str):
    """Send password reset email via Resend. Works for local JSON users too."""
    user = _find_user_by_email(email)
    if not user:
        # Don't reveal whether email exists
        st.info("If that email is registered, you'll receive a reset code shortly.")
        return

    try:
        from auth.email_verify import send_and_store
        success, msg, dev_code = send_and_store(email)
        if success:
            st.session_state["reset_pending"] = True
            st.session_state["reset_email"] = email
            if dev_code:
                st.session_state["dev_reset_code"] = dev_code
            st.info("Password reset code sent! Check your inbox.")
            st.rerun()
        else:
            st.error(f"Could not send reset email: {msg}")
    except ImportError:
        st.error("Email service not available.")


def _render_reset_code_form():
    """Render the password reset code + new password form."""
    from auth.email_verify import verify_code

    email = st.session_state.get("reset_email", "")

    st.markdown(f"""
    <div style="text-align:center; padding:8px 0 10px 0;">
        <div style="font-size:1.4rem; margin-bottom:6px;">🔑</div>
        <h4 style="color:{C_TEXT}; font-size:1rem; margin:0 0 4px 0;">Reset Your Password</h4>
        <p style="color:{C_TEXT2}; font-size:0.8rem; margin:0;">
            Enter the code sent to <strong style="color:{C_TURQUOISE};">{email}</strong></p>
    </div>
    """, unsafe_allow_html=True)

    dev_code = st.session_state.get("dev_reset_code")
    if dev_code:
        st.info(f"Dev mode — your reset code is: **{dev_code}**")

    code = st.text_input("Reset code", max_chars=6, key="reset_code_input", placeholder="123456")
    new_pass = st.text_input("New password", type="password", key="reset_new_pass",
                             help="At least 8 characters")
    new_pass2 = st.text_input("Confirm new password", type="password", key="reset_new_pass2")

    if st.button("Reset Password", key="reset_submit_btn", type="primary", use_container_width=True):
        if not code or len(code) != 6:
            st.warning("Enter the 6-digit code")
            return
        if not new_pass or len(new_pass) < 8:
            st.warning("Password must be at least 8 characters")
            return
        if new_pass != new_pass2:
            st.error("Passwords do not match")
            return

        success, msg = verify_code(email, code)
        if success:
            # Update the password in local store
            users = _load_users()
            updated = False
            for u in users:
                if u.get("email", "").lower() == email.lower():
                    u["password_hash"] = _hash_password(new_pass)
                    updated = True
                    break
            if updated:
                _save_users(users)
                for key in ["reset_pending", "reset_email", "dev_reset_code"]:
                    st.session_state.pop(key, None)
                st.success("Password reset! You can now sign in with your new password.")
                st.rerun()
            else:
                st.error("User not found.")
        else:
            st.error(msg)

    if st.button("← Back to Sign In", key="back_signin_btn"):
        for key in ["reset_pending", "reset_email", "dev_reset_code"]:
            st.session_state.pop(key, None)
        st.rerun()


# =========================================================================
# REGISTRATION
# =========================================================================

def _register_user(full_name: str, email: str, password: str, company: str = "") -> bool:
    """Register a new user. Tries Supabase, falls back to local JSON."""
    try:
        from data.supabase_client import get_client, SUPABASE_AVAILABLE
        if SUPABASE_AVAILABLE:
            client = get_client()
            response = client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {"data": {"full_name": full_name, "company": company}}
            })
            if response.user:
                user_id = response.user.id
                client.table("users").insert({
                    "id": user_id, "email": email, "full_name": full_name,
                    "role": "viewer", "company": company, "status": "active",
                    "created_at": datetime.now().isoformat(),
                }).execute()
                st.session_state.authenticated = True
                st.session_state.user = {
                    "id": user_id, "email": email, "full_name": full_name,
                    "role": "viewer", "company": company,
                }
                if response.session:
                    st.session_state.auth_token = response.session.access_token
                return True
    except Exception:
        pass
    return _register_user_local(full_name, email, password, company)


def _register_user_local(full_name: str, email: str, password: str, company: str = "") -> bool:
    """Register user in local JSON store."""
    try:
        users = _load_users()
        user_id = str(uuid.uuid4())
        new_user = {
            "id": user_id,
            "email": email.lower(),
            "full_name": full_name,
            "role": "viewer",
            "company": company,
            "password_hash": _hash_password(password),
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "last_login": datetime.now().isoformat(),
            "token_usage": 0,
        }
        users.append(new_user)
        _save_users(users)
        st.session_state.authenticated = True
        st.session_state.user = {
            "id": user_id, "email": email.lower(), "full_name": full_name,
            "role": "viewer", "company": company,
        }
        return True
    except Exception:
        return False


# =========================================================================
# AUTHENTICATION
# =========================================================================

def _authenticate_password(email: str, password: str) -> bool:
    """Authenticate with email/password. Tries Supabase, falls back to local."""
    try:
        from data.supabase_client import get_client, SUPABASE_AVAILABLE
        if SUPABASE_AVAILABLE:
            client = get_client()
            response = client.auth.sign_in_with_password({"email": email, "password": password})
            if response.user:
                user_data = client.table("users").select("*").eq("email", email).single().execute()
                st.session_state.authenticated = True
                st.session_state.user = user_data.data if user_data.data else {
                    "id": response.user.id, "email": email,
                    "full_name": email.split("@")[0], "role": "analyst",
                }
                st.session_state.auth_token = response.session.access_token
                return True
    except Exception:
        pass
    return _authenticate_local(email, password)


def _authenticate_local(email: str, password: str) -> bool:
    """Authenticate against local JSON user store."""
    user = _find_user_by_email(email)
    if not user:
        return False
    if user.get("status") != "active":
        st.error("Your account has been deactivated. Contact admin.")
        return False
    if user.get("password_hash") == _hash_password(password):
        users = _load_users()
        for u in users:
            if u["id"] == user["id"]:
                u["last_login"] = datetime.now().isoformat()
                break
        _save_users(users)
        st.session_state.authenticated = True
        st.session_state.user = {
            "id": user["id"], "email": user["email"],
            "full_name": user["full_name"],
            "role": user.get("role", "viewer"),
            "company": user.get("company", ""),
        }
        return True
    return False


# =========================================================================
# PUBLIC API — used by app.py and admin
# =========================================================================

def get_current_user() -> dict | None:
    """Get the currently logged-in user."""
    return st.session_state.get("user")


def get_all_users() -> list:
    """Get all registered users (for admin panel)."""
    try:
        from data.supabase_client import get_client, SUPABASE_AVAILABLE
        if SUPABASE_AVAILABLE:
            client = get_client()
            result = client.table("users").select("*").order("created_at", desc=True).execute()
            if result.data:
                return result.data
    except Exception:
        pass
    return _load_users()


def update_user_role(user_id: str, new_role: str) -> bool:
    """Update a user's role."""
    try:
        from data.supabase_client import get_client, SUPABASE_AVAILABLE
        if SUPABASE_AVAILABLE:
            client = get_client()
            client.table("users").update({"role": new_role}).eq("id", user_id).execute()
            return True
    except Exception:
        pass
    users = _load_users()
    for u in users:
        if u["id"] == user_id:
            u["role"] = new_role
            _save_users(users)
            return True
    return False


def toggle_user_status(user_id: str, active: bool) -> bool:
    """Activate or deactivate a user."""
    status = "active" if active else "inactive"
    try:
        from data.supabase_client import get_client, SUPABASE_AVAILABLE
        if SUPABASE_AVAILABLE:
            client = get_client()
            client.table("users").update({"status": status}).eq("id", user_id).execute()
            return True
    except Exception:
        pass
    users = _load_users()
    for u in users:
        if u["id"] == user_id:
            u["status"] = status
            _save_users(users)
            return True
    return False


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
