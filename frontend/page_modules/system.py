"""
Admin System Health page.
"""
import streamlit as st
from frontend.utils import api, auth as auth_utils
from frontend.components.metric_card import metric_card


def render() -> None:
    token = auth_utils.get_token()
    if not token:
        return

    st.title("⚙️ System Health")
    st.caption("Real-time status of all system components.")
    st.markdown("---")

    if st.button("🔄 Refresh Status"):
        st.rerun()

    health = api.system_health(token)
    if not health:
        st.error("Could not load system health.")
        return

    def _status_icon(s: str) -> str:
        if "online" in s.lower() or "configured" in s.lower():
            return "🟢"
        if "error" in s.lower() or "offline" in s.lower():
            return "🔴"
        return "🟡"

    # Component status cards
    components = [
        ("Backend API", "backend"),
        ("Database", "database"),
        ("ChromaDB", "chromadb"),
        ("LLM", "llm"),
        ("RAG Pipeline", "rag"),
    ]

    for label, key in components:
        status = health.get(key, "unknown")
        icon = _status_icon(status)
        color = "#22c55e" if "🟢" in icon else "#ef4444" if "🔴" in icon else "#f59e0b"
        metric_card(f"{icon} {label}", status, color=color)

    st.markdown("---")
    st.subheader("Configuration")
    config_items = {
        "LLM Model": health.get("llm_model", "—"),
        "Embedding Model": health.get("embedding_model", "—"),
        "ChromaDB Path": health.get("chroma_path", "—"),
        "Documents in Vector DB": str(health.get("document_count", "—")),
    }
    for k, v in config_items.items():
        st.markdown(f"**{k}:** `{v}`")

    st.markdown("---")
    st.caption("⚠️ API keys and secrets are never displayed here for security reasons.")
