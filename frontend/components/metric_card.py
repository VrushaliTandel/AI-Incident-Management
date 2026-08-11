"""
Metric card component.
"""
import streamlit as st


def metric_card(label: str, value: str, delta: str = "", color: str = "#3b82d4") -> None:
    """Display a styled metric card."""
    delta_html = f"<div style='font-size:12px;color:#57606a;'>{delta}</div>" if delta else ""
    st.markdown(
        f"""
        <div style='
            background:#f7f8fa;
            border:1px solid #e5e7eb;
            border-left:4px solid {color};
            border-radius:6px;
            padding:16px 20px;
            margin-bottom:8px;
        '>
            <div style='font-size:13px;color:#57606a;font-weight:500;'>{label}</div>
            <div style='font-size:28px;font-weight:700;color:#1f2328;margin-top:4px;'>{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
