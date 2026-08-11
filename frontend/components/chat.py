"""
Chat display component: renders the conversation history ChatGPT-style.
"""
import streamlit as st
from typing import List, Dict


def render_conversation(history: List[Dict[str, str]]) -> None:
    """Render conversation history with styled message bubbles."""
    for msg in history:
        role = msg.get("role", "assistant")
        content = msg.get("content", "")
        if role == "system":
            continue  # skip internal messages
        if role == "user":
            with st.chat_message("user"):
                st.markdown(content)
        else:
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(content)


def render_verification_buttons(key_prefix: str = "verif") -> str:
    """
    Render YES/NO verification buttons.
    Returns "yes", "no", or "" if not clicked yet.
    """
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("✅ Yes, Resolved", key=f"{key_prefix}_yes", type="primary"):
            return "yes"
    with col2:
        if st.button("❌ No, Try More", key=f"{key_prefix}_no"):
            return "no"
    return ""


def render_diagnostic_input(question: str, key: str = "diag_input") -> str:
    """
    Render a diagnostic question input field.
    Returns the submitted answer or "".
    """
    st.info(f"💬 **{question}**")
    answer = st.text_input("Your answer:", key=key, placeholder="Type your answer here...")
    if st.button("Submit Answer", key=f"{key}_submit", type="primary"):
        if answer.strip():
            return answer.strip()
        st.warning("Please provide an answer.")
    return ""
