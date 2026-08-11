"""
LangGraph routing functions (edges).
Each function receives state and returns the next node name.

IMPORTANT: When user_resolved/l2_resolved/l3_resolved is None, it means
the user has not yet answered. The workflow should NOT continue — the service
layer handles this by detecting awaiting_user_input=True and stopping the stream.

We use END as a sentinel that will cause the graph to stop when verification
is pending. The service layer restores and re-runs with the answer filled in.
"""
import logging
from langgraph.graph import END
from backend.graph.state import IncidentState

logger = logging.getLogger(__name__)


def route_after_l1_verification(state: IncidentState) -> str:
    """Route based on user's answer to L1 verification."""
    user_resolved = state.get("user_resolved")
    if user_resolved is None:
        # Awaiting user input — do not advance the graph
        return "__end__"
    if user_resolved is True:
        return "generate_final_response"
    return "diagnostics"


def route_after_diagnostics(state: IncidentState) -> str:
    """Route after receiving diagnostic answers."""
    return "routing_decision"


def route_after_routing_decision(state: IncidentState) -> str:
    """Route based on the routing agent's decision."""
    decision = state.get("routing_decision", "L2").upper()
    if decision == "MORE_DIAGNOSTICS":
        # Check if we have not exceeded max rounds
        current_round = state.get("diagnostic_round", 0)
        max_rounds = state.get("max_diagnostic_rounds", 3)
        if current_round < max_rounds:
            return "diagnostics"
        # Force to L2 when max rounds exceeded
        return "l2_resolution"
    if decision == "HUMAN_HANDOFF":
        return "human_handoff"
    return "l2_resolution"


def route_after_l2_verification(state: IncidentState) -> str:
    """Route based on user's answer to L2 verification."""
    l2_resolved = state.get("l2_resolved")
    if l2_resolved is None:
        return "__end__"
    if l2_resolved is True:
        return "generate_final_response"
    return "l3_resolution"


def route_after_l3_verification(state: IncidentState) -> str:
    """Route based on user's answer to L3 verification."""
    l3_resolved = state.get("l3_resolved")
    if l3_resolved is None:
        return "__end__"
    if l3_resolved is True:
        return "generate_final_response"
    return "human_handoff"
