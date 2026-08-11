"""
Admin analytics page — extended with additional KPI metrics and charts.
Includes Voice & Language Insights and an inline DeepEval snapshot.
"""
import streamlit as st
from frontend.utils import api, auth as auth_utils
from frontend.components import charts as chart_comp
from frontend.components.metric_card import metric_card


def render() -> None:
    token = auth_utils.get_token()
    if not token:
        return

    st.title("📊 Analytics")
    st.caption("Incident management metrics, trends, and performance KPIs.")
    st.markdown("---")

    data = api.admin_analytics(token)
    if not data:
        st.error("Could not load analytics data.")
        return

    total = data.get("total", 0)
    resolved = data.get("resolved", 0)
    escalated = data.get("escalated", 0)
    in_progress = data.get("in_progress", 0)
    l1 = data.get("l1_resolved", 0)
    l2 = data.get("l2_resolved", 0)
    l3 = data.get("l3_resolved", 0)
    handoff = data.get("human_handoff", 0)
    avg_mins = data.get("avg_resolution_minutes")
    ai_resolution_rate = round((resolved / total * 100), 1) if total else 0
    ai_automation_rate = round(((l1 + l2 + l3) / total * 100), 1) if total else 0
    l1_rate = round((l1 / total * 100), 1) if total else 0
    l2_rate = round((l2 / total * 100), 1) if total else 0
    l3_rate = round((l3 / total * 100), 1) if total else 0
    handoff_rate = round((handoff / total * 100), 1) if total else 0

    # ── ROW 1: Core KPIs ──────────────────────────────────────
    st.subheader("📈 Key Performance Indicators")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Total Incidents", str(total), color="#3b82d4")
    with col2:
        metric_card("Resolution Rate", f"{data.get('resolution_rate', 0):.1f}%", color="#22c55e")
    with col3:
        metric_card("Escalation Rate", f"{data.get('escalation_rate', 0):.1f}%", color="#ef4444")
    with col4:
        avg_str = f"{avg_mins:.0f} min" if avg_mins else "N/A"
        metric_card("Avg Resolution Time", avg_str, color="#f59e0b")

    st.markdown("")

    # ── ROW 2: AI Performance ─────────────────────────────────
    st.subheader("🤖 AI Resolution Performance")
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        metric_card("AI Automation Rate", f"{ai_automation_rate:.1f}%", color="#7c5cd8")
    with col6:
        metric_card("L1 Self-Service Rate", f"{l1_rate:.1f}%", color="#3b82d4")
    with col7:
        metric_card("L2 Advanced Rate", f"{l2_rate:.1f}%", color="#7c5cd8")
    with col8:
        metric_card("L3 Expert Rate", f"{l3_rate:.1f}%", color="#f59e0b")

    st.markdown("")

    # ── ROW 3: Workload ───────────────────────────────────────
    st.subheader("📋 Workload Overview")
    col9, col10, col11, col12 = st.columns(4)
    with col9:
        metric_card("Open / In Progress", str(in_progress), color="#f59e0b")
    with col10:
        metric_card("Resolved", str(resolved), color="#22c55e")
    with col11:
        metric_card("Escalated to Human", str(escalated), color="#ef4444")
    with col12:
        metric_card("Human Handoff Rate", f"{handoff_rate:.1f}%", color="#ef4444")

    st.markdown("")

    # ── ROW 4: Voice & Language Insights ─────────────────────
    st.subheader("🎤 Voice & Language Insights")
    st.caption("Derived from incident query text — no schema change required.")
    lang_dist   = data.get("language_distribution", {})
    non_english = data.get("non_english_incidents", 0)
    ml_rate     = data.get("multilingual_rate", 0.0)
    tier_avg    = data.get("avg_resolution_by_tier", {})

    colv1, colv2, colv3, colv4 = st.columns(4)
    with colv1:
        metric_card("Non-English Incidents", str(non_english), color="#7c5cd8")
    with colv2:
        metric_card("Multilingual Rate", f"{ml_rate:.1f}%", color="#3b82d4")
    with colv3:
        top_lang = max(lang_dist, key=lang_dist.get) if lang_dist else "—"
        metric_card("Top Language", top_lang, color="#f59e0b")
    with colv4:
        unique_langs = len([k for k, v in lang_dist.items() if v > 0])
        metric_card("Languages Detected", str(unique_langs), color="#22c55e")

    if lang_dist and len(lang_dist) > 1:
        st.markdown("")
        _render_language_chart(lang_dist)

    st.markdown("")

    # ── ROW 5: Avg Resolution Time by Tier ───────────────────
    st.subheader("⏱️ Avg Resolution Time by Tier")
    colt1, colt2, colt3, colt4 = st.columns(4)
    tier_colors = {"L1": "#22c55e", "L2": "#7c5cd8", "L3": "#f59e0b", "HUMAN_HANDOFF": "#ef4444"}
    tier_labels = {"L1": "L1 Avg", "L2": "L2 Avg", "L3": "L3 Avg", "HUMAN_HANDOFF": "Human Avg"}
    for col, tier in zip([colt1, colt2, colt3, colt4], ["L1", "L2", "L3", "HUMAN_HANDOFF"]):
        with col:
            val = tier_avg.get(tier)
            display = f"{val:.0f} min" if val is not None else "N/A"
            metric_card(tier_labels[tier], display, color=tier_colors[tier])

    st.markdown("---")

    # ── INLINE DEEPEVAL SNAPSHOT ──────────────────────────────
    st.subheader("🧪 RAG Quality Snapshot (DeepEval)")
    st.caption("Latest evaluation run — go to **Model Evaluation** for full history and to re-run.")
    _render_eval_snapshot(token)

    st.markdown("---")

    # ── CHARTS ROW 1 ─────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        time_series = data.get("time_series", [])
        if time_series:
            chart_comp.incidents_over_time(time_series)
        else:
            st.info("No time series data yet.")

    with col2:
        by_level = data.get("by_resolution_level", {})
        by_level = {k: v for k, v in by_level.items() if v > 0}
        if by_level:
            chart_comp.resolution_pie(by_level)
        else:
            st.info("No resolution level data yet.")

    # ── CHARTS ROW 2 ─────────────────────────────────────────
    col3, col4 = st.columns(2)
    with col3:
        by_status = data.get("by_status", {})
        if by_status:
            chart_comp.status_bar(by_status)
        else:
            st.info("No status data yet.")

    with col4:
        by_user = data.get("by_user", [])
        if by_user:
            chart_comp.users_bar(by_user)
        else:
            st.info("No user data yet.")

    # ── CHARTS ROW 3: AI tier funnel ────────────────────────
    st.markdown("---")
    st.subheader("🔁 AI Resolution Tier Funnel")
    _render_funnel(l1, l2, l3, handoff, total)

    # ── Resolution success gauge ──────────────────────────────
    st.markdown("---")
    st.subheader("🎯 Metrics Summary")
    _render_summary_table(data)


def _render_language_chart(lang_dist: dict) -> None:
    """Bar chart of language distribution."""
    try:
        import plotly.graph_objects as go
        langs  = sorted(lang_dist.items(), key=lambda x: x[1], reverse=True)
        labels = [l[0] for l in langs]
        values = [l[1] for l in langs]
        colors = ["#3b82d4", "#7c5cd8", "#f59e0b", "#22c55e", "#ef4444",
                  "#6b7280", "#a855f7", "#ec4899", "#14b8a6", "#f97316",
                  "#84cc16", "#06b6d4"]
        fig = go.Figure([go.Bar(
            x=labels,
            y=values,
            marker_color=colors[:len(labels)],
            text=values,
            textposition="auto",
        )])
        fig.update_layout(
            title="Incident Language Distribution",
            yaxis_title="Incidents",
            height=260,
            margin=dict(l=20, r=20, t=40, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        st.write(lang_dist)


def _render_eval_snapshot(token: str) -> None:
    """Inline DeepEval metric cards — latest run only."""
    eval_data = api.admin_get_evaluations(token)
    if not eval_data:
        st.info("No evaluation data yet. Run an evaluation from the **Model Evaluation** page.")
        return

    latest = eval_data.get("latest") or eval_data
    if not isinstance(latest, dict):
        st.info("No evaluation data yet.")
        return

    metric_defs = [
        ("Faithfulness",          "faithfulness",          "#3b82d4"),
        ("Answer Relevancy",      "answer_relevancy",      "#7c5cd8"),
        ("Contextual Relevancy",  "contextual_relevancy",  "#f59e0b"),
        ("Contextual Precision",  "contextual_precision",  "#22c55e"),
        ("Contextual Recall",     "contextual_recall",     "#ef4444"),
    ]
    ev_col1, ev_col2, ev_col3, ev_col4, ev_col5 = st.columns(5)
    for col, (label, key, color) in zip(
        [ev_col1, ev_col2, ev_col3, ev_col4, ev_col5], metric_defs
    ):
        with col:
            val = latest.get(key)
            metric_card(label, f"{val:.2f}" if val is not None else "—", color=color)

    overall = latest.get("overall_score")
    if overall is not None:
        st.metric("Overall RAG Score", f"{overall:.2f}")

    if any(latest.get(k) is not None for _, k, _ in metric_defs):
        chart_comp.evaluation_radar(latest)


def _render_funnel(l1: int, l2: int, l3: int, handoff: int, total: int) -> None:
    try:
        import plotly.graph_objects as go
        stages = ["All Incidents", "L1 Resolved", "L2 Resolved", "L3 Resolved", "Human Handoff"]
        values = [total, l1, l2, l3, handoff]
        colors = ["#3b82d4", "#22c55e", "#7c5cd8", "#f59e0b", "#ef4444"]
        fig = go.Figure(go.Funnel(
            y=stages,
            x=values,
            textinfo="value+percent initial",
            marker={"color": colors},
        ))
        fig.update_layout(
            title="AI Triage Funnel — How incidents are resolved",
            height=350,
            margin=dict(l=20, r=20, t=50, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        st.write({"L1": l1, "L2": l2, "L3": l3, "Human": handoff})


def _render_summary_table(data: dict) -> None:
    import pandas as pd
    rows = [
        {"Metric": "Total Incidents", "Value": str(data.get("total", 0)), "Status": "ℹ️"},
        {"Metric": "Resolved", "Value": str(data.get("resolved", 0)), "Status": "✅"},
        {"Metric": "Escalated", "Value": str(data.get("escalated", 0)), "Status": "🔴"},
        {"Metric": "In Progress", "Value": str(data.get("in_progress", 0)), "Status": "🟡"},
        {"Metric": "L1 Resolved", "Value": str(data.get("l1_resolved", 0)), "Status": "✅"},
        {"Metric": "L2 Resolved", "Value": str(data.get("l2_resolved", 0)), "Status": "✅"},
        {"Metric": "L3 Resolved", "Value": str(data.get("l3_resolved", 0)), "Status": "✅"},
        {"Metric": "Human Handoff", "Value": str(data.get("human_handoff", 0)), "Status": "🚨"},
        {"Metric": "Resolution Rate", "Value": f"{data.get('resolution_rate', 0):.1f}%", "Status": "📊"},
        {"Metric": "Escalation Rate", "Value": f"{data.get('escalation_rate', 0):.1f}%", "Status": "📊"},
        {
            "Metric": "Avg Resolution Time",
            "Value": (f"{data['avg_resolution_minutes']:.1f} min" if data.get("avg_resolution_minutes") else "N/A"),
            "Status": "⏱️",
        },
    ]
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
