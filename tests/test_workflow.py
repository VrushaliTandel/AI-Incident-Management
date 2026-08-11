"""
Tests for LangGraph workflow routing logic.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from backend.graph.routing import (
    route_after_l1_verification,
    route_after_routing_decision,
    route_after_l2_verification,
    route_after_l3_verification,
)


def _state(**kwargs):
    base = {
        "query": "Test issue",
        "user_id": 1,
        "incident_id": "test-id",
        "thread_id": "test-thread",
        "retrieved_documents": [],
        "context": "",
        "conversation_history": [],
        "l1_resolution": {},
        "user_resolved": None,
        "diagnostic_questions": [],
        "diagnostic_questions_text": "",
        "diagnostic_answers": [],
        "asked_questions": [],
        "routing_decision": "",
        "routing_confidence": 0.5,
        "routing_reason": "",
        "missing_information": [],
        "l2_analysis": {},
        "l2_resolved": None,
        "l3_analysis": {},
        "l3_resolved": None,
        "human_handoff": False,
        "human_handoff_reason": "",
        "final_response": "",
        "status": "IN_PROGRESS",
        "resolution_level": "",
        "current_node": "l1_resolution",
        "awaiting_user_input": False,
        "user_input_type": "none",
        "diagnostic_round": 0,
        "max_diagnostic_rounds": 3,
    }
    base.update(kwargs)
    return base


class TestL1Routing:
    def test_yes_routes_to_final(self):
        state = _state(user_resolved=True)
        assert route_after_l1_verification(state) == "generate_final_response"

    def test_no_routes_to_diagnostics(self):
        state = _state(user_resolved=False)
        assert route_after_l1_verification(state) == "diagnostics"

    def test_none_stops_graph_awaiting_input(self):
        """None means user hasn't answered yet — graph should stop."""
        state = _state(user_resolved=None)
        assert route_after_l1_verification(state) == "__end__"


class TestRoutingDecision:
    def test_l2_decision(self):
        state = _state(routing_decision="L2")
        assert route_after_routing_decision(state) == "l2_resolution"

    def test_more_diagnostics_within_limit(self):
        state = _state(routing_decision="MORE_DIAGNOSTICS", diagnostic_round=1, max_diagnostic_rounds=3)
        assert route_after_routing_decision(state) == "diagnostics"

    def test_more_diagnostics_at_limit_forces_l2(self):
        state = _state(routing_decision="MORE_DIAGNOSTICS", diagnostic_round=3, max_diagnostic_rounds=3)
        assert route_after_routing_decision(state) == "l2_resolution"

    def test_human_handoff_decision(self):
        state = _state(routing_decision="HUMAN_HANDOFF")
        assert route_after_routing_decision(state) == "human_handoff"

    def test_case_insensitive(self):
        state = _state(routing_decision="l2")
        assert route_after_routing_decision(state) == "l2_resolution"


class TestL2Routing:
    def test_yes_routes_to_final(self):
        state = _state(l2_resolved=True)
        assert route_after_l2_verification(state) == "generate_final_response"

    def test_no_routes_to_l3(self):
        state = _state(l2_resolved=False)
        assert route_after_l2_verification(state) == "l3_resolution"


class TestL3Routing:
    def test_yes_routes_to_final(self):
        state = _state(l3_resolved=True)
        assert route_after_l3_verification(state) == "generate_final_response"

    def test_no_routes_to_handoff(self):
        state = _state(l3_resolved=False)
        assert route_after_l3_verification(state) == "human_handoff"
