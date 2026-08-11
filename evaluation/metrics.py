"""
DeepEval metric definitions and utilities.
"""
from typing import List, Optional


def get_metric_names() -> List[str]:
    return [
        "faithfulness",
        "answer_relevancy",
        "contextual_relevancy",
        "contextual_precision",
        "contextual_recall",
    ]


def score_label(score: Optional[float]) -> str:
    if score is None:
        return "N/A"
    if score >= 0.9:
        return f"{score:.4f} (Excellent)"
    if score >= 0.75:
        return f"{score:.4f} (Good)"
    if score >= 0.6:
        return f"{score:.4f} (Fair)"
    return f"{score:.4f} (Needs Improvement)"


def compute_overall_score(scores: dict) -> Optional[float]:
    valid = [v for v in scores.values() if v is not None]
    return round(sum(valid) / len(valid), 4) if valid else None
