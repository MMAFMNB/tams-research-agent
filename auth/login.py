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
C_GLASS = "rgba(34,47,98,0.12)"
C_BORDER = "rgba(108,185,182,0.08)"

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


def render_login_page():
    """Render the TAM Liquid Glass login/signup page."""
    if st.session_state.get("authenticated"):
        return True

    _ensure_admin_exists()

    # CSS
    st.markdown("""<style>
    [data-testid="stAppViewContainer"] {
        display: flex; align-items: center; justify-content: center;
        min-height: 100vh;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        justify-content: center;
    }
    .stTabs [data-baseweb="tab"] {
        flex: 1;
        justify-content: center;
    }
    </style>""", unsafe_allow_html=True)

    col1, center, col3 = st.columns([1, 2, 1])
    with center:
        # Header card
        st.markdown(f'''<div style="
            background: {C_GLASS};
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            border: 1px solid {C_BORDER};
            border-radius: 20px;
            padding: 40px 32px 20px;
            text-align: center;
            margin: 40px auto 0;
            max-width: 440px;
        ">
            <h2 style="color:{C_TEXT};font-weight:700;margin-bottom:4px;font-size:1.4rem;">
                TAM Research Terminal</h2>
            <p style="color:{C_TEXT2};font-size:0.85rem;margin-bottom:8px;">
                AI-Powered Investment Research for Saudi Markets</p>
        </div>''', unsafe_allow_html=True)

        # Tabs: Sign In / Create Account
        tab_signin, tab_signup = st.tabs(["Sign In", "Create Account"])

        with tab_signin:
            _render_signin_form()

        with tab_signup:
            _render_signup_form()

        # Disclaimer
        st.markdown(f'''<p style="color:{C_TEXT2};font-size:0.65rem;margin-top:20px;text-align:center;">
            TAM Capital | CMA Regulated<br>Confidential — Authorized Personnel Only
        </p>''', unsafe_allow_html=True)

    return False


def _render_signin_form():
    """Render the sign-in form."""
    email = st.text_input("Email", placeholder="name@tamcapital.sa", key="login_email")
    password = st.text_input("Password", type="password", key="login_password")

    col_login, col_forgot = st.columns([2, 1])
    with col_login:
        if st.button("Sign In", key="login_btn", type="primary", use_container_width=True):
            if email and password:
                success = _authenticate_password(email, password)
                if success:
                    st.rerun()
                else:
                    st.error("Invalid email or password")
            else:
                st.warning("Please enter email and password")
    with col_forgot:
        if st.button("Forgot?", key="forgot_btn", use_container_width=True):
            if email:
                _send_password_reset(email)
                st.info("If that email exists, a reset link was sent")
            else:
                st.warning("Enter your email first")


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

    full_name = st.text_input("Full Name", placeholder="Ahmed Al-Rashid", key="signup_name")
    email = st.text_input("Work Email", placeholder="name@company.com", key="signup_email")
    company = st.text_input("Company / Organization", placeholder="TAM Capital", key="signup_company")
    password = st.text_input("Create Password", type="password", key="signup_password",
                             help="At least 8 characters")
    password2 = st.text_input("Confirm Password", type="password", key="signup_password2")

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
                    # Dev mode — show code directly
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


def _render_verify_code_form():
    """Render the email verification code entry form."""
    from auth.email_verify import verify_code, send_and_store

    pending = st.session_state.get("pending_signup", {})
    email = pending.get("email", "")

    st.markdown(f"""
    <div style="text-align:center; padding:10px 0 15px 0;">
        <h3 style="color:{C_TEXT}; font-size:1.2rem;">Verify Your Email</h3>
        <p style="color:{C_TEXT2}; font-size:0.85rem;">
            We sent a 6-digit code to <strong style="color:{C_TURQUOISE};">{email}</strong>
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Dev mode: show code
    dev_code = st.session_state.get("dev_verify_code")
    if dev_code:
        st.info(f"Development mode — your verification code is: **{dev_code}**")

    code = st.text_input("Enter 6-digit code", max_chars=6, key="verify_code_input",
                         placeholder="123456")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Verify", key="verify_btn", type="primary", use_container_width=True):
            if not code or len(code) != 6:
                st.warning("Please enter the 6-digit code")
                return

            success, msg = verify_code(email, code)
            if success:
                # Complete registration
                reg_success = _register_user(
                    pending["full_name"],
                    pending["email"],
                    pending["password"],
                    pending.get("company", ""),
                )
                if reg_success:
                    # Clean up
                    for key in ["verify_pending", "pending_signup", "dev_verify_code"]:
                        st.session_state.pop(key, None)
                    st.success("Email verified! You're now signed in.")
                    st.rerun()
                else:
                    st.error("Registration failed after verification. Please try again.")
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

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
    if st.button("Back to Sign Up", key="back_signup_btn"):
        for key in ["verify_pending", "pending_signup", "dev_verify_code"]:
            st.session_state.pop(key, None)
        st.rerun()


def _register_user(full_name: str, email: str, password: str, company: str = "") -> bool:
    """Register a new user. Tries Supabase, falls back to local JSON."""
    try:
        from data.supabase_client import get_client, SUPABASE_AVAILABLE
        if SUPABASE_AVAILABLE:
            client = get_client()
            # Create auth user in Supabase
            response = client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "full_name": full_name,
                        "company": company,
                    }
                }
            })
            if response.user:
                # Also insert into users table
                user_id = response.user.id
                client.table("users").insert({
                    "id": user_id,
                    "email": email,
                    "full_name": full_name,
                    "role": "viewer",  # New signups start as viewer
                    "company": company,
                    "status": "active",
                    "created_at": datetime.now().isoformat(),
                }).execute()

                # Auto-login after signup
                st.session_state.authenticated = True
                st.session_state.user = {
                    "id": user_id,
                    "email": email,
                    "full_name": full_name,
                    "role": "viewer",
                    "company": company,
                }
                if response.session:
                    st.session_state.auth_token = response.session.access_token
                return True
    except Exception:
        pass

    # Fallback: local JSON store
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

        # Auto-login
        st.session_state.authenticated = True
        st.session_state.user = {
            "id": user_id,
            "email": email.lower(),
            "full_name": full_name,
            "role": "viewer",
            "company": company,
        }
        return True
    except Exception:
        return False


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
                    "id": response.user.id,
                    "email": email,
                    "full_name": email.split("@")[0],
                    "role": "analyst",
                }
                st.session_state.auth_token = response.session.access_token
                return True
    except Exception:
        pass

    # Fallback: local JSON store
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
        # Update last login
        users = _load_users()
        for u in users:
            if u["id"] == user["id"]:
                u["last_login"] = datetime.now().isoformat()
                break
        _save_users(users)

        st.session_state.authenticated = True
        st.session_state.user = {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user.get("role", "viewer"),
            "company": user.get("company", ""),
        }
        return True
    return False


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

    # Local fallback
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

    # Local fallback
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
