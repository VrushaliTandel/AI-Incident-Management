"""
Admin Model Evaluation page (DeepEval).
"""
import streamlit as st
from frontend.utils import api, auth as auth_utils
from frontend.components.metric_card import metric_card
from frontend.components.charts import evaluation_radar


def render() -> None:
    token = auth_utils.get_token()
    if not token:
        return

    st.title("🧪 Model Evaluation")
    st.caption("DeepEval metrics for the RAG + LLM pipeline.")
    st.markdown("---")

    # Run evaluation button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("▶️ Run Evaluation", type="primary"):
            with st.spinner("Running DeepEval evaluation (this may take several minutes)..."):
                result = api.admin_run_evaluation(token)
                if "error" in result:
                    st.error(f"Evaluation failed: {result['error']}")
                else:
                    st.success(f"✅ Evaluation complete! Run ID: `{result.get('run_id', '')}` | {result.get('count', 0)} test cases")
                    st.rerun()

    st.markdown("---")

    # Load existing results
    data = api.admin_get_evaluations(token)
    if not data:
        st.info("No evaluation results yet. Click **Run Evaluation** to start.")
        return

    latest = data.get("latest")
    if not latest:
        # Fallback: use flat structure
        latest = data

    averages = latest if isinstance(latest, dict) else {}

    # Metric cards
    st.subheader("Latest Evaluation Metrics")
    col1, col2, col3, col4, col5 = st.columns(5)
    metric_defs = [
        ("Faithfulness", "faithfulness", "#3b82d4"),
        ("Answer Relevancy", "answer_relevancy", "#7c5cd8"),
        ("Contextual Relevancy", "contextual_relevancy", "#f59e0b"),
        ("Contextual Precision", "contextual_precision", "#22c55e"),
        ("Contextual Recall", "contextual_recall", "#ef4444"),
    ]
    cols = [col1, col2, col3, col4, col5]
    for col, (label, key, color) in zip(cols, metric_defs):
        with col:
            val = averages.get(key)
            metric_card(label, f"{val:.2f}" if val is not None else "—", color=color)

    overall = averages.get("overall_score")
    st.metric("Overall Score", f"{overall:.2f}" if overall is not None else "—")

    st.markdown("---")

    # Radar chart
    if any(averages.get(k) is not None for k, _, _ in metric_defs):
        st.subheader("Metrics Radar")
        evaluation_radar(averages)
        st.markdown("---")

    # Run history
    runs = data.get("runs", [])
    if runs and len(runs) > 1:
        st.subheader("Evaluation History")
        history_data = []
        for run in runs:
            if run:
                history_data.append({
                    "Run ID": run.get("run_id", "")[:8],
                    "Test Cases": run.get("count", 0),
                    "Faithfulness": _fmt_score(run.get("faithfulness")),
                    "Answer Relevancy": _fmt_score(run.get("answer_relevancy")),
                    "Contextual Relevancy": _fmt_score(run.get("contextual_relevancy")),
                    "Contextual Precision": _fmt_score(run.get("contextual_precision")),
                    "Contextual Recall": _fmt_score(run.get("contextual_recall")),
                    "Overall": _fmt_score(run.get("overall_score")),
                    "Date": run.get("created_at", "")[:16] if run.get("created_at") else "—",
                })
        if history_data:
            st.dataframe(history_data, use_container_width=True, hide_index=True)
        st.markdown("---")

    # Individual test cases
    test_cases = data.get("test_cases", [])
    if test_cases:
        st.subheader("Individual Test Case Results")
        tc_data = []
        for tc in test_cases:
            tc_data.append({
                "Test Case": tc.get("test_case_id", ""),
                "Faithfulness": _fmt_score(tc.get("faithfulness")),
                "Answer Relevancy": _fmt_score(tc.get("answer_relevancy")),
                "Contextual Relevancy": _fmt_score(tc.get("contextual_relevancy")),
                "Contextual Precision": _fmt_score(tc.get("contextual_precision")),
                "Contextual Recall": _fmt_score(tc.get("contextual_recall")),
                "Overall": _fmt_score(tc.get("overall_score")),
            })
        st.dataframe(tc_data, use_container_width=True, hide_index=True)


def _fmt_score(val) -> str:
    if val is None:
        return "—"
    return f"{float(val):.4f}"
