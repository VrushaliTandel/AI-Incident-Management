"""
Admin: All Incidents page.
"""
import streamlit as st
from datetime import datetime
from frontend.utils import api, auth as auth_utils, session as session_utils
from frontend.components.incident_card import incident_card


def render() -> None:
    token = auth_utils.get_token()
    if not token:
        return

    st.title("📋 All Incidents")
    st.caption("View and manage all incidents across all users.")
    st.markdown("---")

    # Top control row: Refresh button aligned with filters
    filter_row, refresh_col = st.columns([5, 1])
    with refresh_col:
        if st.button("🔄 Refresh", use_container_width=True, key="admin_inc_refresh"):
            # Clear any cached filter state so the page fully reloads
            for k in ["admin_inc_status", "admin_inc_level", "admin_inc_search"]:
                st.session_state.pop(k, None)
            st.rerun()

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox(
            "Status", ["All", "IN_PROGRESS", "RESOLVED", "ESCALATED"],
            key="admin_inc_status"
        )
    with col2:
        level_filter = st.selectbox(
            "Resolution Level", ["All", "L1", "L2", "L3", "HUMAN_HANDOFF"],
            key="admin_inc_level"
        )
    with col3:
        search = st.text_input("Search issue", placeholder="Search...", key="admin_inc_search")

    params = {}
    if status_filter != "All":
        params["status"] = status_filter
    if level_filter != "All":
        params["resolution_level"] = level_filter

    incidents = api.admin_all_incidents(token, **params)

    if search:
        incidents = [i for i in incidents if search.lower() in i.get("user_query", "").lower()]

    st.caption(f"**{len(incidents)} incident(s) found**")
    st.markdown("---")

    if not incidents:
        st.info("No incidents found with the selected filters.")
        return

    # Table view
    table_data = []
    for i in incidents:
        table_data.append({
            "Incident ID": i.get("incident_id", "")[:8] + "...",
            "User": i.get("username", str(i.get("user_id", "?"))),
            "Issue": i.get("user_query", "")[:50] + ("..." if len(i.get("user_query", "")) > 50 else ""),
            "Status": i.get("status", ""),
            "Resolution Level": i.get("resolution_level", "—") or "—",
            "Created": _fmt_date(i.get("created_at")),
        })

    st.dataframe(table_data, use_container_width=True, hide_index=True)
    st.markdown("---")
    st.caption("Click an incident card below to view full details.")

    for i, inc in enumerate(incidents):
        if incident_card(inc, on_click_key=f"admin_inc_{i}"):
            session_utils.set_active_incident(inc["incident_id"])
            st.session_state["admin_viewing"] = True
            session_utils.navigate("admin_incident_detail")


def _fmt_date(dt_str) -> str:
    if not dt_str:
        return "—"
    try:
        dt = datetime.fromisoformat(str(dt_str).replace("Z", "+00:00"))
        return dt.strftime("%b %d %H:%M")
    except Exception:
        return str(dt_str)
