"""
Incident details page: loads historical incident from DB (does NOT re-run workflow).
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


def _status_badge(status: str) -> str:
    colors = {
        "RESOLVED": ("green", "✅"),
        "ESCALATED": ("red", "🚨"),
        "IN_PROGRESS": ("orange", "🔄"),
    }
    color, icon = colors.get(status, ("gray", "⚪"))
    return f":{color}[{icon} {status}]"


def render() -> None:
    token = auth_utils.get_token()
    if not token:
        return

    incident_id = session_utils.get_active_incident()
    if not incident_id:
        st.warning("No incident selected.")
        if st.button("← Back to My Incidents"):
            session_utils.navigate("incident_history")
        return

    # Load from backend (persistent DB)
    incident = api.get_incident_detail(token, incident_id)
    if not incident:
        st.error("Incident not found or access denied.")
        if st.button("← Back"):
            session_utils.navigate("incident_history")
        return

    # ── Header ──────────────────────────────────────────────
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(f"🎫 Incident Details")
        st.caption(f"ID: `{incident.get('incident_id', '')}` | Thread: `{incident.get('thread_id', '')}`")
    with col2:
        status = incident.get("status", "IN_PROGRESS")
        st.markdown(f"**Status:** {_status_badge(status)}")
        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            if st.button("← Back"):
                session_utils.navigate("incident_history")
        with btn_c2:
            if st.button("🗑️ Delete", help="Permanently delete this incident"):
                st.session_state["_detail_confirm_del"] = True

    st.markdown("---")

    # ── Metadata ────────────────────────────────────────────
    meta_col1, meta_col2, meta_col3 = st.columns(3)
    with meta_col1:
        st.metric("Created", _fmt_date(incident.get("created_at")))
    with meta_col2:
        st.metric("Updated", _fmt_date(incident.get("updated_at")))
    with meta_col3:
        level = incident.get("resolution_level", "") or "In Progress"
        st.metric("Resolution Level", level)

    # ── Confirm delete ───────────────────────────────────────
    if st.session_state.get("_detail_confirm_del"):
        st.warning(f"⚠️ Permanently delete incident `{incident_id}`?")
        dc1, dc2 = st.columns(2)
        with dc1:
            if st.button("✅ Yes, Delete", type="primary", key="det_del_yes"):
                ok = api.delete_incident(token, incident_id)
                st.session_state.pop("_detail_confirm_del", None)
                if ok:
                    st.success("Incident deleted.")
                    session_utils.navigate("incident_history")
                    st.rerun()
                else:
                    st.error("Delete failed.")
        with dc2:
            if st.button("❌ Cancel", key="det_del_no"):
                st.session_state.pop("_detail_confirm_del", None)
                st.rerun()

    st.markdown("---")

    # ── Original Query ──────────────────────────────────────
    with st.expander("🔍 Original Issue", expanded=True):
        st.markdown(f"**{incident.get('user_query', '')}**")

    # ── Conversation History ─────────────────────────────────
    with st.expander("💬 Conversation", expanded=True):
        history = incident.get("conversation_history") or []
        if history:
            render_conversation(history)
        else:
            st.caption("No conversation history.")

    # ── Retrieved Context ────────────────────────────────────
    retrieved = incident.get("retrieved_documents") or []
    if retrieved:
        with st.expander(f"📚 Retrieved Knowledge Base Context ({len(retrieved)} docs)"):
            for i, doc in enumerate(retrieved, 1):
                st.markdown(f"**Source {i}: {doc.get('source', 'Unknown')}**")
                st.text(doc.get("content", "")[:300] + "..." if len(doc.get("content", "")) > 300 else doc.get("content", ""))
                st.divider()

    # ── L1 Resolution ───────────────────────────────────────
    l1 = incident.get("l1_resolution") or {}
    if l1:
        with st.expander("🔵 L1 Resolution"):
            st.markdown(f"**Root Cause:** {l1.get('root_cause_hypothesis', '—')}")
            st.markdown(f"**Confidence:** {l1.get('confidence', 0):.0%}")
            steps = l1.get("resolution_steps", [])
            if steps:
                st.markdown("**Steps:**")
                for s in steps:
                    st.markdown(f"- {s}")

    # ── Diagnostics ──────────────────────────────────────────
    diag_q = incident.get("diagnostic_questions") or []
    diag_a = incident.get("diagnostic_answers") or []
    if diag_q:
        with st.expander(f"🔎 Diagnostics ({len(diag_q)} questions)"):
            answer_map = {a["question_id"]: a["answer"] for a in diag_a}
            for q in diag_q:
                qid = q.get("question_id", "")
                st.markdown(f"**Q:** {q.get('question', '')}")
                ans = answer_map.get(qid) or q.get("answer", "Not answered")
                st.markdown(f"**A:** {ans}")
                st.divider()

    # ── L2 Resolution ───────────────────────────────────────
    l2 = incident.get("l2_analysis") or {}
    if l2:
        with st.expander("🟠 L2 Resolution"):
            st.markdown(f"**Root Cause:** {l2.get('root_cause_analysis', '—')}")
            st.markdown(f"**Confidence:** {l2.get('confidence', 0):.0%}")
            steps = l2.get("resolution_steps", [])
            if steps:
                st.markdown("**Steps:**")
                for s in steps:
                    st.markdown(f"- {s}")
            if incident.get("l2_resolved") is not None:
                st.markdown(f"**L2 Resolved:** {'✅ Yes' if incident.get('l2_resolved') else '❌ No'}")

    # ── L3 Resolution ───────────────────────────────────────
    l3 = incident.get("l3_analysis") or {}
    if l3:
        with st.expander("🔴 L3 Expert Resolution"):
            st.markdown(f"**Root Cause:** {l3.get('root_cause', '—')}")
            st.markdown(f"**Confidence:** {l3.get('confidence', 0):.0%}")
            actions = l3.get("recommended_actions", [])
            if actions:
                st.markdown("**Recommended Actions:**")
                for a in actions:
                    st.markdown(f"- {a}")
            if incident.get("l3_resolved") is not None:
                st.markdown(f"**L3 Resolved:** {'✅ Yes' if incident.get('l3_resolved') else '❌ No'}")

    # ── Human Handoff ────────────────────────────────────────
    if incident.get("human_handoff"):
        with st.expander("🚨 Human Handoff"):
            st.error(f"**Escalation Reason:** {incident.get('human_handoff_reason', '—')}")

    # ── Final Response ───────────────────────────────────────
    final = incident.get("final_response", "")
    if final:
        with st.expander("✅ Final Response", expanded=True):
            st.markdown(final)

    # ── Resume option for IN_PROGRESS incidents ──────────────
    if status == "IN_PROGRESS":
        st.markdown("---")

        # Work out where the incident currently is so we show the right UI
        l1      = incident.get("l1_resolution") or {}
        l2      = incident.get("l2_analysis") or {}
        l3      = incident.get("l3_analysis") or {}
        diag_q  = incident.get("diagnostic_questions") or []
        l2_res  = incident.get("l2_resolved")
        l3_res  = incident.get("l3_resolved")

        # Determine awaiting state: figure out which tier last ran
        # and whether the user still needs to answer a verification or diagnostic
        unanswered_diag = [q for q in diag_q if q.get("answer") is None]

        if unanswered_diag:
            # A diagnostic question was asked but not yet answered
            awaiting_input = True
            input_type     = "diagnostic"
            cur_node       = "diagnostics"
        elif l3 and l3_res is None:
            # L3 ran, waiting for user verification
            awaiting_input = True
            input_type     = "verification"
            cur_node       = "l3_resolution"
        elif l2 and l2_res is None:
            # L2 ran, waiting for user verification
            awaiting_input = True
            input_type     = "verification"
            cur_node       = "l2_resolution"
        elif l1 and incident.get("l1_resolution") and not diag_q:
            # L1 ran, no diagnostics yet — waiting for L1 verification
            awaiting_input = True
            input_type     = "verification"
            cur_node       = "l1_resolution"
        else:
            awaiting_input = False
            input_type     = "none"
            cur_node       = "persisted"

        st.info(
            f"This incident is still in progress at **{'L3' if l3 else 'L2' if l2 else 'L1'} "
            f"{'— awaiting your answer' if awaiting_input else '— processing'}**. "
            "Click below to continue."
        )

        if st.button("▶️ Resume Troubleshooting", type="primary"):
            # Build the full workflow state so new_incident.py renders the correct UI
            st.session_state["workflow_state"] = {
                # Identifiers
                "incident_id":            incident.get("incident_id"),
                "thread_id":              incident.get("thread_id"),
                "status":                 "IN_PROGRESS",
                # Workflow position — must be correct for UI to show buttons
                "awaiting_user_input":    awaiting_input,
                "user_input_type":        input_type,
                "current_node":           cur_node,
                # Full conversation so chat history displays
                "conversation_history":   incident.get("conversation_history", []),
                # Tier data — needed by _apply_verification tier-detection logic
                "l1_resolution":          l1,
                "l2_analysis":            l2,
                "l3_analysis":            l3,
                "l2_resolved":            l2_res,
                "l3_resolved":            l3_res,
                "diagnostic_questions":   diag_q,
                "diagnostic_answers":     incident.get("diagnostic_answers") or [],
                "user_resolved":          None,
                "routing_decision":       incident.get("routing_decision") or "",
                "routing_confidence":     incident.get("routing_confidence") or 0.0,
                "routing_reason":         incident.get("routing_reason") or "",
                "missing_information":    incident.get("missing_information") or [],
                "human_handoff":          incident.get("human_handoff") or False,
                "human_handoff_reason":   incident.get("human_handoff_reason") or "",
                "final_response":         incident.get("final_response") or "",
                "resolution_level":       incident.get("resolution_level") or "",
                "query":                  incident.get("user_query", ""),
                "user_id":                incident.get("user_id"),
                "diagnostic_round":       len(diag_q),
                "max_diagnostic_rounds":  3,
            }
            st.session_state["workflow_incident_id"] = incident.get("incident_id")
            st.session_state["workflow_thread_id"]   = incident.get("thread_id")
            # Clear stale submission flags so voice/form works fresh
            for k in ("_voice_submitted", "_diag_submitted", "__vt__", "__dvt__"):
                st.session_state.pop(k, None)
            session_utils.navigate("new_incident")
