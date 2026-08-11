"""
LangGraph workflow definition.
Builds the compiled graph with all nodes and edges.
"""
import logging
from functools import lru_cache

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from backend.graph.state import IncidentState
from backend.graph.nodes import (
    rag_node,
    l1_resolution_node,
    diagnostics_node,
    routing_decision_node,
    l2_resolution_node,
    l3_resolution_node,
    human_handoff_node,
    generate_final_response_node,
    persist_incident_node,
)
from backend.graph.routing import (
    route_after_l1_verification,
    route_after_diagnostics,
    route_after_routing_decision,
    route_after_l2_verification,
    route_after_l3_verification,
)

logger = logging.getLogger(__name__)


def build_workflow():
    """Construct and compile the incident workflow graph."""
    workflow = StateGraph(IncidentState)

    # ── Nodes ──────────────────────────────────────────────
    workflow.add_node("rag", rag_node)
    workflow.add_node("l1_resolution", l1_resolution_node)
    workflow.add_node("diagnostics", diagnostics_node)
    workflow.add_node("routing_decision", routing_decision_node)
    workflow.add_node("l2_resolution", l2_resolution_node)
    workflow.add_node("l3_resolution", l3_resolution_node)
    workflow.add_node("human_handoff", human_handoff_node)
    workflow.add_node("generate_final_response", generate_final_response_node)
    workflow.add_node("persist_incident", persist_incident_node)

    # ── Entry Point ─────────────────────────────────────────
    workflow.set_entry_point("rag")

    # ── Deterministic Edges ─────────────────────────────────
    workflow.add_edge("rag", "l1_resolution")
    # L1 → awaits user input → resume triggers routing
    workflow.add_edge("diagnostics", "routing_decision")
    # After persisting, workflow ends
    workflow.add_edge("persist_incident", END)
    workflow.add_edge("generate_final_response", "persist_incident")
    workflow.add_edge("human_handoff", "persist_incident")

    # ── Conditional Edges ───────────────────────────────────
    # After L1: YES → final, NO → diagnostics, None → END (await user)
    workflow.add_conditional_edges(
        "l1_resolution",
        route_after_l1_verification,
        {
            "generate_final_response": "generate_final_response",
            "diagnostics": "diagnostics",
            "__end__": END,
        },
    )

    # After routing decision: L2 | MORE_DIAGNOSTICS | HUMAN_HANDOFF
    workflow.add_conditional_edges(
        "routing_decision",
        route_after_routing_decision,
        {
            "l2_resolution": "l2_resolution",
            "diagnostics": "diagnostics",
            "human_handoff": "human_handoff",
        },
    )

    # After L2: YES → final, NO → L3, None → END (await user)
    workflow.add_conditional_edges(
        "l2_resolution",
        route_after_l2_verification,
        {
            "generate_final_response": "generate_final_response",
            "l3_resolution": "l3_resolution",
            "__end__": END,
        },
    )

    # After L3: YES → final, NO → human handoff, None → END (await user)
    workflow.add_conditional_edges(
        "l3_resolution",
        route_after_l3_verification,
        {
            "generate_final_response": "generate_final_response",
            "human_handoff": "human_handoff",
            "__end__": END,
        },
    )

    # ── Compile with MemorySaver (for within-session checkpoints) ──
    memory = MemorySaver()
    compiled = workflow.compile(checkpointer=memory)

    logger.info("LangGraph workflow compiled successfully")
    return compiled


@lru_cache(maxsize=1)
def get_workflow():
    """Return the cached compiled workflow."""
    return build_workflow()
