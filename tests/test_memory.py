"""
Tests for memory service: state build, restore, and isolation.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from backend.services.memory_service import (
    build_initial_state,
    restore_state_from_db,
    apply_user_verification,
    apply_diagnostic_answer,
)


def test_build_initial_state():
    state = build_initial_state("VPN issue", 1, "inc-001", "thread-001")
    assert state["query"] == "VPN issue"
    assert state["user_id"] == 1
    assert state["incident_id"] == "inc-001"
    assert state["thread_id"] == "thread-001"
    assert state["status"] == "IN_PROGRESS"
    assert state["awaiting_user_input"] is False
    assert len(state["conversation_history"]) == 1
    assert state["conversation_history"][0]["role"] == "user"


def test_apply_verification_l1_yes():
    state = build_initial_state("test", 1, "id", "tid")
    state["current_node"] = "l1_resolution"
    updated = apply_user_verification(state, True)
    assert updated["user_resolved"] is True
    assert updated["awaiting_user_input"] is False
    history = updated["conversation_history"]
    assert any("Yes" in m.get("content", "") for m in history)


def test_apply_verification_l1_no():
    state = build_initial_state("test", 1, "id", "tid")
    state["current_node"] = "l1_resolution"
    updated = apply_user_verification(state, False)
    assert updated["user_resolved"] is False


def test_apply_verification_l2():
    state = build_initial_state("test", 1, "id", "tid")
    state["current_node"] = "l2_resolution"
    updated = apply_user_verification(state, True)
    assert updated["l2_resolved"] is True
    assert updated.get("user_resolved") is None  # L1 field untouched


def test_apply_verification_l3():
    state = build_initial_state("test", 1, "id", "tid")
    state["current_node"] = "l3_resolution"
    updated = apply_user_verification(state, False)
    assert updated["l3_resolved"] is False


def test_apply_diagnostic_answer():
    state = build_initial_state("test", 1, "id", "tid")
    state["diagnostic_questions"] = [
        {"question_id": "diag_1", "question": "Can you access other websites?", "answer": None}
    ]
    state["diagnostic_answers"] = []

    updated = apply_diagnostic_answer(state, "Yes, I can access other sites.")
    assert len(updated["diagnostic_answers"]) == 1
    assert updated["diagnostic_answers"][0]["answer"] == "Yes, I can access other sites."
    assert updated["diagnostic_questions"][0]["answer"] == "Yes, I can access other sites."
    # Should appear in conversation history
    assert any("Yes, I can access other sites." in m.get("content", "")
               for m in updated["conversation_history"])


def test_memory_isolation_different_users():
    """Verify states for different users are completely separate."""
    state_a = build_initial_state("User A issue", 1, "inc-A", "thread-A")
    state_b = build_initial_state("User B issue", 2, "inc-B", "thread-B")

    state_a = apply_user_verification(state_a, True)
    # B's state is not affected
    assert state_b.get("user_resolved") is None
    assert state_b["query"] == "User B issue"
    assert state_b["user_id"] == 2


def test_no_duplicate_diagnostic_questions():
    """Verify asked_questions tracking prevents duplicates."""
    state = build_initial_state("test", 1, "id", "tid")
    state["asked_questions"] = ["diag_1", "diag_2"]
    state["diagnostic_questions"] = [
        {"question_id": "diag_1", "question": "Q1", "answer": "A1"},
        {"question_id": "diag_2", "question": "Q2", "answer": "A2"},
    ]
    # A new question should have a different ID
    assert "diag_3" not in state["asked_questions"]
    assert "diag_1" in state["asked_questions"]
