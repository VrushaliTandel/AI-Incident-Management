"""
Session state helpers.
"""
import streamlit as st
from typing import Any, Optional


def get(key: str, default: Any = None) -> Any:
    return st.session_state.get(key, default)


def set_key(key: str, value: Any) -> None:
    st.session_state[key] = value


def navigate(page: str) -> None:
    st.session_state["current_page"] = page
    st.rerun()


def get_current_page() -> str:
    return st.session_state.get("current_page", "login")


def set_active_incident(incident_id: str) -> None:
    st.session_state["active_incident_id"] = incident_id
    st.session_state["active_thread_id"] = None


def get_active_incident() -> Optional[str]:
    return st.session_state.get("active_incident_id")


def set_active_thread(thread_id: str) -> None:
    st.session_state["active_thread_id"] = thread_id


def get_active_thread() -> Optional[str]:
    return st.session_state.get("active_thread_id")


def clear_active_incident() -> None:
    st.session_state.pop("active_incident_id", None)
    st.session_state.pop("active_thread_id", None)
    st.session_state.pop("workflow_state", None)
