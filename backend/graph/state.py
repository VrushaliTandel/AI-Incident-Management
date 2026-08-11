"""
LangGraph workflow state definition.
All fields that flow through the graph nodes are declared here.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, TypedDict, Annotated
import operator


class DiagnosticQuestion(TypedDict):
    question_id: str
    question: str
    answer: Optional[str]


class IncidentState(TypedDict):
    # Core identifiers
    query: str
    user_id: int
    incident_id: str
    thread_id: str

    # RAG
    retrieved_documents: List[Dict[str, Any]]
    context: str

    # Conversation
    conversation_history: Annotated[List[Dict[str, str]], operator.add]

    # L1
    l1_resolution: Dict[str, Any]
    user_resolved: Optional[bool]       # None = not answered yet

    # Diagnostics
    diagnostic_questions: List[DiagnosticQuestion]
    diagnostic_questions_text: str      # formatted for display
    diagnostic_answers: List[Dict[str, str]]
    asked_questions: List[str]          # IDs of already-asked questions

    # Routing
    routing_decision: str               # L2 | MORE_DIAGNOSTICS | HUMAN_HANDOFF
    routing_confidence: float
    routing_reason: str
    missing_information: List[str]

    # L2
    l2_analysis: Dict[str, Any]
    l2_resolved: Optional[bool]

    # L3
    l3_analysis: Dict[str, Any]
    l3_resolved: Optional[bool]

    # Human Handoff
    human_handoff: bool
    human_handoff_reason: str

    # Output
    final_response: str
    status: str                         # IN_PROGRESS | RESOLVED | ESCALATED
    resolution_level: str               # L1 | L2 | L3 | HUMAN_HANDOFF

    # Internal workflow control
    current_node: str
    awaiting_user_input: bool
    user_input_type: str                # "verification" | "diagnostic" | "none"
    diagnostic_round: int
    max_diagnostic_rounds: int
