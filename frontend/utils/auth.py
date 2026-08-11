"""
Frontend auth utilities: token storage and session helpers.
"""
import streamlit as st
from typing import Optional


def get_token() -> Optional[str]:
    return st.session_state.get("token")


def get_user() -> Optional[dict]:
    return st.session_state.get("user")


def get_role() -> str:
    user = get_user()
    return user.get("role", "user") if user else "user"


def is_authenticated() -> bool:
    return bool(get_token() and get_user())


def is_admin() -> bool:
    return get_role() == "admin"


def set_auth(token: str, user: dict) -> None:
    st.session_state["token"] = token
    st.session_state["user"] = user


def clear_auth() -> None:
    for key in ["token", "user", "current_incident", "current_page"]:
        st.session_state.pop(key, None)


def require_auth():
    """Redirect to login if not authenticated."""
    if not is_authenticated():
        st.session_state["current_page"] = "login"
        st.rerun()


def require_admin_role():
    """Stop execution if user is not admin."""
    if not is_admin():
        st.error("🚫 Admin access required.")
        st.stop()
