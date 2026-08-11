"""
Human Handoffs page: admin queue for escalated incidents.
"""
import streamlit as st
from datetime import datetime
from frontend.utils import api, auth as auth_utils, session as session_utils


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

    st.title("🚨 Human Handoff Queue")
    st.caption("Incidents requiring human agent intervention.")
    st.markdown("---")

    # Controls row
    ctrl1, ctrl2 = st.columns([3, 1])
    with ctrl1:
        show_resolved = st.checkbox("Show resolved handoffs", value=False, key="handoffs_show_resolved")
    with ctrl2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    resolved_param = True if show_resolved else None
    handoffs = api.admin_get_handoffs(token, resolved=resolved_param)

    if not handoffs:
        st.success("✅ No pending handoffs! All incidents are handled.")
        return

    st.caption(f"**{len(handoffs)} handoff(s) found**")
    st.markdown("---")

    for h in handoffs:
        _render_handoff_card(token, h)


def _render_handoff_card(token: str, h: dict) -> None:
    resolved = h.get("resolved_by_agent", False)
    border_color = "#22c55e" if resolved else "#ef4444"
    handoff_id = h.get("id")          # integer PK of the handoff row
    assigned_to = h.get("assigned_to")

    with st.container():
        st.markdown(
            f"""
            <div style='border:1px solid {border_color};border-left:4px solid {border_color};
                        border-radius:6px;padding:16px;margin-bottom:12px;background:#fff;'>
                <div style='font-size:15px;font-weight:700;color:#1f2328;'>
                    🎫 {h.get('issue_summary', '')[:80]}
                </div>
                <div style='margin-top:8px;display:flex;gap:16px;flex-wrap:wrap;'>
                    <span style='font-size:12px;color:#57606a;'>User: <strong>{h.get('username', h.get('user_id', '?'))}</strong></span>
                    <span style='font-size:12px;color:#57606a;'>AI Confidence: <strong>{h.get('ai_confidence', 0):.0%}</strong></span>
                    <span style='font-size:12px;color:#57606a;'>Created: <strong>{_fmt_date(h.get('created_at'))}</strong></span>
                    <span style='font-size:12px;color:#57606a;'>Assigned: <strong>{"Agent #" + str(assigned_to) if assigned_to else "Unassigned"}</strong></span>
                    {'<span style="font-size:12px;color:#22c55e;"><strong>✅ Resolved</strong></span>' if resolved else '<span style="font-size:12px;color:#ef4444;"><strong>⏳ Pending</strong></span>'}
                </div>
                <div style='margin-top:8px;font-size:13px;color:#57606a;'>
                    <strong>Reason:</strong> {h.get('escalation_reason', '—')[:200]}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("🔍 Open Incident", key=f"open_{handoff_id}"):
                # Fetch all escalated incidents and find the one whose handoff matches
                incidents = api.admin_all_incidents(token, status="ESCALATED")
                # Match by user_id AND human_handoff flag, pick most recent
                matched = [
                    i for i in incidents
                    if i.get("human_handoff") and i.get("user_id") == h.get("user_id")
                ]
                if matched:
                    matched.sort(key=lambda x: x.get("created_at", ""), reverse=True)
                    session_utils.set_active_incident(matched[0]["incident_id"])
                    st.session_state["admin_viewing"] = True
                    session_utils.navigate("admin_incident_detail")
                    st.rerun()
                else:
                    st.warning("Incident not found.")

        with col2:
            ownership_label = "✅ Owned" if assigned_to else "🤝 Take Ownership"
            if st.button(ownership_label, key=f"take_{handoff_id}", disabled=bool(assigned_to)):
                result = api.admin_take_ownership_by_handoff(token, handoff_id)
                if "error" in result:
                    st.error(f"Failed: {result['error']}")
                else:
                    st.success(result.get("message", "Ownership taken."))
                    st.rerun()

        with col3:
            if not resolved:
                if st.button("✅ Mark Resolved", key=f"resolve_{handoff_id}"):
                    result = api.admin_resolve_handoff(token, handoff_id)
                    if "error" in result:
                        st.error(f"Failed: {result['error']}")
                    else:
                        st.success("Handoff marked as resolved.")
                        st.rerun()

        with col4:
            if st.button("📝 Add Notes", key=f"notes_btn_{handoff_id}"):
                st.session_state[f"show_notes_{handoff_id}"] = not st.session_state.get(f"show_notes_{handoff_id}", False)

        # Inline notes form
        if st.session_state.get(f"show_notes_{handoff_id}"):
            notes = st.text_area("Agent notes:", key=f"notes_text_{handoff_id}",
                                 placeholder="Enter notes for this handoff...")
            save_col, cancel_col = st.columns([1, 3])
            with save_col:
                if st.button("💾 Save", key=f"save_notes_{handoff_id}", type="primary"):
                    if notes.strip():
                        result = api.admin_add_notes_by_handoff(token, handoff_id, notes.strip())
                        if "error" in result:
                            st.error(f"Failed: {result['error']}")
                        else:
                            st.success("Notes saved.")
                            st.session_state.pop(f"show_notes_{handoff_id}", None)
                            st.rerun()
                    else:
                        st.warning("Notes cannot be empty.")

        if h.get("agent_notes"):
            st.caption(f"📝 **Agent Notes:** {h.get('agent_notes')}")

        st.divider()
