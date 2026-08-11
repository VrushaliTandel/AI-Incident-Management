"""
Reusable Plotly chart helpers.
"""
import streamlit as st
from typing import List, Dict, Any


def incidents_over_time(time_series: List[Dict[str, Any]]) -> None:
    try:
        import plotly.graph_objects as go
        dates = [d["date"] for d in time_series]
        counts = [d["count"] for d in time_series]
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates, y=counts, mode="lines+markers",
            line=dict(color="#3b82d4", width=2),
            marker=dict(size=5),
            name="Incidents",
        ))
        fig.update_layout(
            title="Incidents Over Time (Last 30 Days)",
            xaxis_title="Date", yaxis_title="Count",
            height=300, margin=dict(l=20, r=20, t=40, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        st.line_chart({d["date"]: d["count"] for d in time_series})


def resolution_pie(by_level: Dict[str, int]) -> None:
    try:
        import plotly.graph_objects as go
        labels = list(by_level.keys())
        values = list(by_level.values())
        colors = ["#3b82d4", "#7c5cd8", "#f59e0b", "#ef4444", "#6b7280"]
        fig = go.Figure(go.Pie(
            labels=labels, values=values,
            marker=dict(colors=colors[:len(labels)]),
            hole=0.4,
        ))
        fig.update_layout(
            title="Resolution Level Breakdown",
            height=300, margin=dict(l=20, r=20, t=40, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        st.write(by_level)


def status_bar(by_status: Dict[str, int]) -> None:
    try:
        import plotly.graph_objects as go
        colors = {"RESOLVED": "#22c55e", "ESCALATED": "#ef4444", "IN_PROGRESS": "#f59e0b"}
        fig = go.Figure([go.Bar(
            x=list(by_status.keys()),
            y=list(by_status.values()),
            marker_color=[colors.get(k, "#6b7280") for k in by_status.keys()],
        )])
        fig.update_layout(
            title="Incidents by Status",
            yaxis_title="Count",
            height=280, margin=dict(l=20, r=20, t=40, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        st.write(by_status)


def users_bar(by_user: List[Dict]) -> None:
    try:
        import plotly.graph_objects as go
        usernames = [u["username"] for u in by_user]
        counts = [u["count"] for u in by_user]
        fig = go.Figure([go.Bar(
            x=usernames, y=counts,
            marker_color="#7c5cd8",
        )])
        fig.update_layout(
            title="Incidents by User",
            yaxis_title="Incidents",
            height=280, margin=dict(l=20, r=20, t=40, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        st.write({u["username"]: u["count"] for u in by_user})


def evaluation_radar(averages: Dict[str, Any]) -> None:
    try:
        import plotly.graph_objects as go
        metrics = ["faithfulness", "answer_relevancy", "contextual_relevancy",
                   "contextual_precision", "contextual_recall"]
        labels = ["Faithfulness", "Answer\nRelevancy", "Contextual\nRelevancy",
                  "Contextual\nPrecision", "Contextual\nRecall"]
        values = [averages.get(m, 0) or 0 for m in metrics]
        values_closed = values + [values[0]]  # close the polygon
        labels_closed = labels + [labels[0]]
        fig = go.Figure(go.Scatterpolar(
            r=values_closed,
            theta=labels_closed,
            fill="toself",
            line_color="#3b82d4",
            fillcolor="rgba(59,130,212,0.2)",
            name="Score",
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(range=[0, 1])),
            title="Evaluation Metrics Radar",
            height=350, margin=dict(l=20, r=20, t=40, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        st.write(averages)
