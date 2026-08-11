"""
Memory service: manages incident-specific conversational memory.
Combines LangGraph MemorySaver (in-session) with DB persistence (cross-restart).
"""
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def build_initial_state(
    query: str,
    user_id: int,
    incident_id: str,
    thread_id: str,
) -> Dict[str, Any]:
    """Build the initial LangGraph state for a new incident."""
    return {
        "query": query,
        "user_id": user_id,
        "incident_id": incident_id,
        "thread_id": thread_id,
        "retrieved_documents": [],
        "context": "",
        "conversation_history": [{"role": "user", "content": query}],
        "l1_resolution": {},
        "user_resolved": None,
        "diagnostic_questions": [],
        "diagnostic_questions_text": "",
        "diagnostic_answers": [],
        "asked_questions": [],
        "routing_decision": "",
        "routing_confidence": 0.0,
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
        "current_node": "start",
        "awaiting_user_input": False,
        "user_input_type": "none",
        "diagnostic_round": 0,
        "max_diagnostic_rounds": 3,
    }


def restore_state_from_db(incident) -> Dict[str, Any]:
    """Reconstruct state dict from a persisted Incident ORM object."""
    return {
        "query": incident.user_query,
        "user_id": incident.user_id,
        "incident_id": incident.incident_id,
        "thread_id": incident.thread_id,
        "retrieved_documents": incident.retrieved_documents or [],
        "context": "",
        "conversation_history": incident.conversation_history or [],
        "l1_resolution": incident.l1_resolution or {},
        "user_resolved": None,
        "diagnostic_questions": incident.diagnostic_questions or [],
        "diagnostic_questions_text": "",
        "diagnostic_answers": incident.diagnostic_answers or [],
        "asked_questions": [
            q.get("question_id", "") for q in (incident.diagnostic_questions or [])
        ],
        "routing_decision": incident.routing_decision or "",
        "routing_confidence": incident.routing_confidence or 0.0,
        "routing_reason": incident.routing_reason or "",
        "missing_information": incident.missing_information or [],
        "l2_analysis": incident.l2_analysis or {},
        "l2_resolved": incident.l2_resolved,
        "l3_analysis": incident.l3_analysis or {},
        "l3_resolved": incident.l3_resolved,
        "human_handoff": incident.human_handoff or False,
        "human_handoff_reason": incident.human_handoff_reason or "",
        "final_response": incident.final_response or "",
        "status": incident.status or "IN_PROGRESS",
        "resolution_level": incident.resolution_level or "",
        "current_node": "persisted",
        "awaiting_user_input": False,
        "user_input_type": "none",
        "diagnostic_round": len(incident.diagnostic_questions or []),
        "max_diagnostic_rounds": 3,
    }


def apply_user_verification(state: Dict[str, Any], resolved: bool) -> Dict[str, Any]:
    """
    Apply a YES/NO verification answer to the appropriate state field.

    Detection logic (does NOT rely on current_node, which may be 'persisted' after
    a DB restore):
      - If l3_analysis is populated and l3_resolved is still None → L3 tier
      - If l2_analysis is populated and l2_resolved is still None → L2 tier
      - Otherwise → L1 tier (user_resolved)
    """
    updated = dict(state)
    l2 = state.get("l2_analysis") or {}
    l3 = state.get("l3_analysis") or {}
    l3_resolved = state.get("l3_resolved")
    l2_resolved = state.get("l2_resolved")

    if l3 and l3_resolved is None and l2:
        updated["l3_resolved"] = resolved
    elif l2 and l2_resolved is None:
        updated["l2_resolved"] = resolved
    else:
        updated["user_resolved"] = resolved

    updated["awaiting_user_input"] = False
    updated["user_input_type"] = "none"
    answer_text = "Yes, resolved." if resolved else "No, not resolved."
    updated["conversation_history"] = updated.get("conversation_history", []) + [
        {"role": "user", "content": answer_text}
    ]
    return updated


def apply_diagnostic_answer(
    state: Dict[str, Any], answer: str
) -> Dict[str, Any]:
    """Record a diagnostic answer in the state."""
    updated = dict(state)
    questions = list(state.get("diagnostic_questions", []))
    answers = list(state.get("diagnostic_answers", []))

    # Find the most recently asked unanswered question
    unanswered = [q for q in questions if q.get("answer") is None]
    if unanswered:
        q = unanswered[-1]
        q_id = q.get("question_id", "")
        # Update question answer in place
        for i, question in enumerate(questions):
            if question.get("question_id") == q_id:
                questions[i] = dict(question)
                questions[i]["answer"] = answer
                break
        answers.append({"question_id": q_id, "answer": answer})

    updated["diagnostic_questions"] = questions
    updated["diagnostic_answers"] = answers
    updated["awaiting_user_input"] = False
    updated["user_input_type"] = "none"
    updated["conversation_history"] = updated.get("conversation_history", []) + [
        {"role": "user", "content": answer}
    ]
    return updated
