"""
Incident card component.
"""
import streamlit as st
from datetime import datetime


def _status_badge(status: str) -> str:
    colors = {
        "RESOLVED": ("#e6f4ea", "#1e7e34"),
        "ESCALATED": ("#fde8e8", "#c0392b"),
        "IN_PROGRESS": ("#fff3cd", "#856404"),
    }
    bg, fg = colors.get(status, ("#f7f8fa", "#1f2328"))
    return (
        f"<span style='background:{bg};color:{fg};padding:2px 8px;"
        f"border-radius:12px;font-size:11px;font-weight:600;'>{status}</span>"
    )


def incident_card(incident: dict, on_click_key: str) -> bool:
    """Render an incident card. Returns True if clicked."""
    query = incident.get("user_query", "")[:60]
    status = incident.get("status", "IN_PROGRESS")
    resolution = incident.get("resolution_level", "") or "—"
    created = incident.get("created_at", "")
    if isinstance(created, str) and "T" in created:
        try:
            created = datetime.fromisoformat(created.replace("Z", "+00:00"))
            created = created.strftime("%b %d, %H:%M")
        except Exception:
            pass

    st.markdown(
        f"""
        <div style='border:1px solid #e5e7eb;border-radius:6px;
                    padding:12px 16px;margin-bottom:8px;background:#fff;'>
            <div style='font-size:14px;font-weight:600;color:#1f2328;'>{query}</div>
            <div style='margin-top:6px;display:flex;gap:8px;align-items:center;'>
                {_status_badge(status)}
                <span style='font-size:12px;color:#57606a;'>Level: {resolution}</span>
                <span style='font-size:12px;color:#57606a;margin-left:auto;'>{created}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return st.button("Open →", key=on_click_key)
