"""Role-Based Access Control for TAM Research."""
import streamlit as st
from functools import wraps

# Permission matrix
PERMISSIONS = {
    "super_admin": {
        "pages": ["dashboard", "research", "portfolio", "sectors", "comparison", "watchlist", "admin"],
        "actions": ["generate_report", "export", "manage_portfolio", "manage_watchlist",
                     "manage_alerts", "manage_users", "view_audit", "system_config",
                     "manage_notes", "view_all_reports"],
    },
    "admin": {
        "pages": ["dashboard", "research", "portfolio", "sectors", "comparison", "watchlist", "admin"],
        "actions": ["generate_report", "export", "manage_portfolio", "manage_watchlist",
                     "manage_alerts", "manage_users", "view_audit", "manage_notes", "view_all_reports"],
    },
    "analyst": {
        "pages": ["dashboard", "research", "portfolio", "sectors", "comparison", "watchlist"],
        "actions": ["generate_report", "export", "manage_portfolio", "manage_watchlist",
                     "manage_alerts", "manage_notes"],
    },
    "viewer": {
        "pages": ["dashboard", "sectors"],
        "actions": ["view_reports"],
    },
}

def get_user_role() -> str:
    user = st.session_state.get("user", {})
    return user.get("role", "viewer")

def has_permission(action: str) -> bool:
    role = get_user_role()
    return action in PERMISSIONS.get(role, {}).get("actions", [])

def can_access_page(page: str) -> bool:
    role = get_user_role()
    return page in PERMISSIONS.get(role, {}).get("pages", [])

def require_permission(action: str):
    """Decorator/function that checks permission and shows error if denied."""
    if not has_permission(action):
        st.error(f"You don't have permission to perform this action. Contact your admin.")
        st.stop()

def require_role(*roles):
    """Check if current user has one of the required roles."""
    current_role = get_user_role()
    if current_role not in roles:
        st.error("Access denied. Insufficient permissions.")
        st.stop()

def is_admin() -> bool:
    return get_user_role() in ("super_admin", "admin")

def is_super_admin() -> bool:
    return get_user_role() == "super_admin"

def get_accessible_pages() -> list:
    role = get_user_role()
    return PERMISSIONS.get(role, {}).get("pages", [])
