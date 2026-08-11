"""
Incident history page: all user's incidents.
"""
import streamlit as st
from frontend.utils import api, auth as auth_utils, session as session_utils
from frontend.components.incident_card import incident_card


def render() -> None:
    token = auth_utils.get_token()
    if not token:
        return

    st.title("📋 My Incidents")
    st.caption("Click any incident to view details or resume troubleshooting.")
    st.markdown("---")

    incidents = api.get_incident_history(token)

    if not incidents:
        st.info("No incidents found. Create your first incident from the sidebar or dashboard.")
        if st.button("➕ New Incident", type="primary"):
            session_utils.navigate("new_incident")
        return

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.selectbox(
            "Filter by Status", ["All", "IN_PROGRESS", "RESOLVED", "ESCALATED"],
            key="hist_status_filter"
        )
    with col2:
        search = st.text_input("Search", placeholder="Search by issue...", key="hist_search")

    filtered = incidents
    if status_filter != "All":
        filtered = [i for i in filtered if i.get("status") == status_filter]
    if search:
        filtered = [i for i in filtered if search.lower() in i.get("user_query", "").lower()]

    st.caption(f"Showing {len(filtered)} of {len(incidents)} incidents")
    st.markdown("---")

    # Confirm-delete state
    pending_delete = st.session_state.get("_hist_confirm_del")

    for i, inc in enumerate(filtered):
        iid = inc["incident_id"]

        # Confirm dialog for this incident
        if pending_delete == iid:
            st.warning(f"⚠️ Permanently delete incident `{iid}`?")
            dc1, dc2 = st.columns(2)
            with dc1:
                if st.button("✅ Yes, Delete", key=f"del_yes_{i}", type="primary"):
                    ok = api.delete_incident(token, iid)
                    st.session_state.pop("_hist_confirm_del", None)
                    if ok:
                        st.success("Deleted.")
                    else:
                        st.error("Delete failed.")
                    st.rerun()
            with dc2:
                if st.button("❌ Cancel", key=f"del_no_{i}"):
                    st.session_state.pop("_hist_confirm_del", None)
                    st.rerun()
            continue

        col_card, col_del = st.columns([9, 1])
        with col_card:
            if incident_card(inc, on_click_key=f"hist_inc_{i}"):
                session_utils.set_active_incident(iid)
                session_utils.navigate("incident_details")
        with col_del:
            if st.button("🗑️", key=f"del_{i}", help="Delete this incident"):
                st.session_state["_hist_confirm_del"] = iid
                st.rerun()
