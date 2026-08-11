"""
Tests for DeepEval evaluation pipeline.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from backend.services.evaluation_service import load_dataset, _aggregate_results, _mock_evaluation
from backend.database.models import Evaluation


def test_load_dataset():
    dataset = load_dataset()
    assert isinstance(dataset, list)
    assert len(dataset) > 0
    for item in dataset:
        assert "input" in item
        assert "expected_output" in item
        assert "retrieval_context" in item


def test_mock_evaluation_returns_correct_count():
    dataset = load_dataset()
    results = _mock_evaluation(dataset, run_id="test-run", created_by=None)
    assert len(results) == len(dataset)


def test_mock_evaluation_scores_in_range():
    dataset = load_dataset()
    results = _mock_evaluation(dataset, run_id="test-run", created_by=None)
    for ev in results:
        for attr in ["faithfulness", "answer_relevancy", "contextual_relevancy",
                     "contextual_precision", "contextual_recall"]:
            score = getattr(ev, attr)
            if score is not None:
                assert 0.0 <= score <= 1.0, f"{attr} = {score} out of range"


def test_aggregate_results_empty():
    result = _aggregate_results([], "test-run")
    assert result["run_id"] == "test-run"
    assert result["count"] == 0


def test_aggregate_results_average():
    evals = [
        Evaluation(test_case_id="t1", faithfulness=0.8, answer_relevancy=0.9,
                   contextual_relevancy=0.7, contextual_precision=0.85,
                   contextual_recall=0.75, overall_score=0.8, run_id="r1"),
        Evaluation(test_case_id="t2", faithfulness=0.9, answer_relevancy=0.8,
                   contextual_relevancy=0.8, contextual_precision=0.75,
                   contextual_recall=0.85, overall_score=0.82, run_id="r1"),
    ]
    result = _aggregate_results(evals, "r1")
    assert result["faithfulness"] == pytest.approx(0.85, abs=0.001)
    assert result["answer_relevancy"] == pytest.approx(0.85, abs=0.001)


def test_five_metrics_present():
    """Verify all five required metrics are tracked."""
    metrics = ["faithfulness", "answer_relevancy", "contextual_relevancy",
               "contextual_precision", "contextual_recall"]
    dataset = load_dataset()
    results = _mock_evaluation(dataset[:1], run_id="test", created_by=None)
    for metric in metrics:
        assert hasattr(results[0], metric), f"Missing metric: {metric}"


def test_evaluation_with_db():
    """Test evaluation run with in-memory DB."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.database.connection import Base
    from backend.database import models  # noqa

    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=test_engine)
    Session = sessionmaker(bind=test_engine)
    db = Session()

    try:
        result = _mock_evaluation(load_dataset()[:3], "test-run", created_by=None)
        from backend.database.repository import save_evaluations
        saved = save_evaluations(db, result)
        assert len(saved) == 3
    finally:
        db.close()
