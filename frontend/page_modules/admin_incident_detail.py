"""
Admin incident detail page.
"""
import streamlit as st
from datetime import datetime
from frontend.utils import api, auth as auth_utils, session as session_utils
from frontend.components.chat import render_conversation


def _fmt_date(dt_str) -> str:
    if not dt_str:
        return "—"
    try:
        dt = datetime.fromisoformat(str(dt_str).replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y %H:%M")
    except Exception:
        return str(dt_str)


def render() -> None:
    token = auth_utils.get_token()
    if not token:
        return

    incident_id = session_utils.get_active_incident()
    if not incident_id:
        st.warning("No incident selected.")
        if st.button("← All Incidents"):
            session_utils.navigate("all_incidents")
        return

    incident = api.admin_get_incident(token, incident_id)
    if not incident:
        st.error("Incident not found.")
        if st.button("← Back"):
            session_utils.navigate("all_incidents")
        return

    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🔍 Incident Detail (Admin)")
        st.caption(f"ID: `{incident.get('incident_id', '')}` | User: **{incident.get('username', incident.get('user_id', '?'))}**")
    with col2:
        if st.button("← All Incidents"):
            session_utils.navigate("all_incidents")

    st.markdown("---")

    # Metadata
    meta1, meta2, meta3 = st.columns(3)
    with meta1:
        st.metric("Status", incident.get("status", "—"))
    with meta2:
        st.metric("Resolution Level", incident.get("resolution_level", "—") or "In Progress")
    with meta3:
        st.metric("Created", _fmt_date(incident.get("created_at")))

    st.markdown("---")

    # Issue
    with st.expander("🔍 Original Issue", expanded=True):
        st.markdown(f"**{incident.get('user_query', '')}**")

    # Full conversation
    with st.expander("💬 Full Conversation", expanded=True):
        history = incident.get("conversation_history") or []
        if history:
            render_conversation(history)
        else:
            st.caption("No conversation history.")

    # L1
    l1 = incident.get("l1_resolution") or {}
    if l1:
        with st.expander("🔵 L1 Resolution"):
            st.json(l1)

    # Diagnostics
    diag_q = incident.get("diagnostic_questions") or []
    if diag_q:
        with st.expander(f"🔎 Diagnostics ({len(diag_q)} questions)"):
            diag_a = incident.get("diagnostic_answers") or []
            answer_map = {a["question_id"]: a["answer"] for a in diag_a}
            for q in diag_q:
                st.markdown(f"**Q:** {q.get('question', '')}")
                st.markdown(f"**A:** {answer_map.get(q.get('question_id', ''), '—')}")
                st.divider()

    # L2
    l2 = incident.get("l2_analysis") or {}
    if l2:
        with st.expander("🟠 L2 Resolution"):
            st.json(l2)

    # L3
    l3 = incident.get("l3_analysis") or {}
    if l3:
        with st.expander("🔴 L3 Expert Resolution"):
            st.json(l3)

    # Human Handoff
    if incident.get("human_handoff"):
        with st.expander("🚨 Human Handoff", expanded=True):
            st.error(f"**Escalation Reason:** {incident.get('human_handoff_reason', '—')}")

    # Final response
    final = incident.get("final_response", "")
    if final:
        with st.expander("✅ Final Response", expanded=True):
            st.markdown(final)

    st.markdown("---")

    # Admin actions
    st.subheader("Admin Actions")
    col1, col2 = st.columns(2)
    with col1:
        if incident.get("status") != "RESOLVED":
            notes = st.text_area("Resolution notes (optional):", key="admin_resolve_notes")
            if st.button("✅ Mark Resolved", type="primary"):
                result = api.admin_resolve_incident(token, incident_id, notes.strip())
                st.success(result.get("message", "Done"))
                st.rerun()

    with col2:
        add_notes = st.text_area("Add agent notes:", key="admin_add_notes_text")
        if st.button("💾 Save Notes"):
            if add_notes.strip():
                result = api.admin_add_notes(token, incident_id, add_notes.strip())
                st.success(result.get("message", "Notes saved"))
                st.rerun()

    if incident.get("human_handoff"):
        st.markdown("---")
        if st.button("🤝 Take Ownership of This Incident"):
            result = api.admin_take_ownership(token, incident_id)
            st.success(result.get("message", "Done"))
            st.rerun()
