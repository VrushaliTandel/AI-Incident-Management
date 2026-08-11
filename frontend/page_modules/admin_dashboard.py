"""
Admin dashboard page — with extended metrics and KPIs.
"""
import streamlit as st
from frontend.utils import api, auth as auth_utils, session as session_utils
from frontend.components.metric_card import metric_card


def render() -> None:
    token = auth_utils.get_token()
    if not token:
        return

    st.title("🎛️ Admin Dashboard")
    st.caption("Human Support Agent Console — Real-time Incident Overview")
    st.markdown("---")

    stats = api.admin_dashboard(token)
    if not stats:
        st.error("Could not load dashboard statistics.")
        return

    total = stats.get("total", 0)
    resolved = stats.get("resolved", 0)
    escalated = stats.get("escalated", 0)
    in_progress = stats.get("in_progress", 0)
    l1 = stats.get("l1_resolved", 0)
    l2 = stats.get("l2_resolved", 0)
    l3 = stats.get("l3_resolved", 0)
    handoff = stats.get("human_handoff", 0)
    resolution_rate = stats.get("resolution_rate", 0)
    escalation_rate = stats.get("escalation_rate", 0)
    ai_automation = round(((l1 + l2 + l3) / total * 100), 1) if total else 0
    handoff_rate = round((handoff / total * 100), 1) if total else 0

    # ── ROW 1: Core Incident Stats ───────────────────────────
    st.subheader("📋 Incident Overview")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Total Incidents", str(total), color="#3b82d4")
    with col2:
        metric_card("Resolved", str(resolved), color="#22c55e")
    with col3:
        metric_card("Escalated", str(escalated), color="#ef4444")
    with col4:
        metric_card("In Progress", str(in_progress), color="#f59e0b")

    st.markdown("")

    # ── ROW 2: AI Resolution Tiers ───────────────────────────
    st.subheader("🤖 AI Resolution Tiers")
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        metric_card("L1 Resolved", str(l1), color="#3b82d4")
    with col6:
        metric_card("L2 Resolved", str(l2), color="#7c5cd8")
    with col7:
        metric_card("L3 Resolved", str(l3), color="#f59e0b")
    with col8:
        metric_card("Human Handoff", str(handoff), color="#ef4444")

    st.markdown("")

    # ── ROW 3: Rates ─────────────────────────────────────────
    st.subheader("📈 Performance Rates")
    col9, col10, col11, col12 = st.columns(4)
    with col9:
        metric_card("Resolution Rate", f"{resolution_rate:.1f}%", color="#22c55e")
    with col10:
        metric_card("Escalation Rate", f"{escalation_rate:.1f}%", color="#ef4444")
    with col11:
        metric_card("AI Automation Rate", f"{ai_automation:.1f}%", color="#7c5cd8")
    with col12:
        metric_card("Human Handoff Rate", f"{handoff_rate:.1f}%", color="#ef4444")

    st.markdown("---")

    # Quick navigation
    st.subheader("⚡ Quick Actions")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🚨 Human Handoffs", use_container_width=True):
            session_utils.navigate("human_handoffs")
    with col2:
        if st.button("📋 All Incidents", use_container_width=True):
            session_utils.navigate("all_incidents")
    with col3:
        if st.button("📊 Analytics", use_container_width=True):
            session_utils.navigate("analytics")
    with col4:
        if st.button("👥 Users", use_container_width=True):
            session_utils.navigate("users")
