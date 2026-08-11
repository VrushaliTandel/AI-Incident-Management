"""
Sidebar components for USER and ADMIN.
"""
import streamlit as st
from typing import List, Dict
from frontend.utils import auth as auth_utils, session as session_utils, api


def _status_icon(status: str) -> str:
    return {"RESOLVED": "🟢", "ESCALATED": "🔴", "IN_PROGRESS": "🟡"}.get(status, "⚪")


def render_user_sidebar(incidents: List[Dict]) -> None:
    with st.sidebar:
        st.markdown("## 🤖 AI Incident Management")
        st.divider()

        # New Incident button
        if st.button("➕ New Incident", use_container_width=True, type="primary"):
            session_utils.clear_active_incident()
            session_utils.navigate("new_incident")

        st.divider()

        # Navigation
        if st.button("🏠 Dashboard", use_container_width=True):
            session_utils.navigate("user_dashboard")
        if st.button("📋 My Incidents", use_container_width=True):
            session_utils.navigate("incident_history")

        st.divider()
        st.markdown("**Recent Incidents**")

        if not incidents:
            st.caption("No incidents yet.")
        else:
            for inc in incidents[:10]:
                icon = _status_icon(inc.get("status", ""))
                query = inc.get("user_query", "Unknown")
                label = f"{icon} {query[:30]}..." if len(query) > 30 else f"{icon} {query}"
                btn_key = f"sidebar_inc_{inc['incident_id']}"
                if st.button(label, key=btn_key, use_container_width=True):
                    session_utils.set_active_incident(inc["incident_id"])
                    session_utils.navigate("incident_details")

        st.divider()

        user = auth_utils.get_user()
        backend_ok = api.check_backend()
        backend_status = "🟢 Backend Online" if backend_ok else "🔴 Backend Offline"
        st.caption(backend_status)

        if user:
            st.caption(f"👤 {user.get('username', '')}")
        if st.button("🚪 Logout", use_container_width=True):
            auth_utils.clear_auth()
            session_utils.navigate("login")


def render_admin_sidebar() -> None:
    with st.sidebar:
        st.markdown("## 🤖 AI Incident Management")
        st.markdown("*Admin Panel*")
        st.divider()

        pages = [
            ("🏠 Dashboard", "admin_dashboard"),
            ("🚨 Human Handoffs", "human_handoffs"),
            ("📋 All Incidents", "all_incidents"),
            ("📊 Analytics", "analytics"),
            ("🧪 Model Evaluation", "evaluation"),
            ("👥 Users", "users"),
            ("⚙️ System", "system"),
        ]
        for label, page in pages:
            if st.button(label, use_container_width=True):
                session_utils.navigate(page)

        st.divider()
        user = auth_utils.get_user()
        if user:
            st.caption(f"👤 Admin: {user.get('username', '')}")
        if st.button("🚪 Logout", use_container_width=True):
            auth_utils.clear_auth()
            session_utils.navigate("login")
