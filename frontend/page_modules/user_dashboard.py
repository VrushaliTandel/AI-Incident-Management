"""
User dashboard page.
"""
import streamlit as st
from frontend.utils import api, auth as auth_utils, session as session_utils
from frontend.components.metric_card import metric_card
from frontend.components.incident_card import incident_card


def render() -> None:
    token = auth_utils.get_token()
    user = auth_utils.get_user()
    if not token or not user:
        return

    st.title("🏠 My Dashboard")
    st.markdown(f"Welcome back, **{user.get('username', '')}** 👋")
    st.markdown("---")

    # Metrics
    stats = api.get_user_stats(token)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("My Total Incidents", str(stats.get("total", 0)), color="#3b82d4")
    with col2:
        metric_card("Resolved", str(stats.get("resolved", 0)), color="#22c55e")
    with col3:
        metric_card("Escalated", str(stats.get("escalated", 0)), color="#ef4444")
    with col4:
        metric_card("In Progress", str(stats.get("in_progress", 0)), color="#f59e0b")

    st.markdown("---")
    st.subheader("Recent Incidents")

    incidents = api.get_incident_history(token)

    if not incidents:
        st.info("You haven't created any incidents yet. Click **➕ New Incident** to get started!")
    else:
        for i, inc in enumerate(incidents[:5]):
            if incident_card(inc, on_click_key=f"dash_inc_{i}"):
                session_utils.set_active_incident(inc["incident_id"])
                session_utils.navigate("incident_details")

    st.markdown("---")
    if st.button("➕ New Incident", type="primary"):
        session_utils.navigate("new_incident")
