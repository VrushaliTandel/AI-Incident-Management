"""
Incident service: orchestrates the LangGraph workflow with DB persistence.

Resume strategy:
  The MemorySaver checkpointer lives in-process memory. After a server restart it
  is empty, so workflow.stream(None, config) would fail or restart from scratch.

  Instead we use update_state(config, full_state, as_node=<tier_node>) which tells
  LangGraph "node X just completed and produced this state". Then stream(None, config)
  correctly follows the conditional edge OUT of that node with the answer applied.

  This pattern works whether or not the checkpointer already has a snapshot.
"""
import logging
import uuid
from typing import Any, Dict

from sqlalchemy.orm import Session

from backend.database import models, repository
from backend.services.memory_service import (
    build_initial_state,
    restore_state_from_db,
)

logger = logging.getLogger(__name__)


def _get_workflow():
    from backend.graph.workflow import get_workflow
    return get_workflow()


# ─────────────────────────────────────────────────────────
# Create new incident
# ─────────────────────────────────────────────────────────
def create_new_incident(db: Session, user_id: int, query: str) -> Dict[str, Any]:
    """
    Create a new incident and run RAG + L1.
    Returns state after L1 pauses (awaiting_user_input=True).
    """
    incident_id = str(uuid.uuid4())
    thread_id   = str(uuid.uuid4())

    incident = models.Incident(
        incident_id=incident_id,
        thread_id=thread_id,
        user_id=user_id,
        user_query=query,
        status="IN_PROGRESS",
        conversation_history=[{"role": "user", "content": query}],
    )
    repository.create_incident(db, incident)

    initial_state = build_initial_state(query, user_id, incident_id, thread_id)
    config = {"configurable": {"thread_id": thread_id}}
    workflow = _get_workflow()

    final_state = None
    try:
        for event in workflow.stream(initial_state, config=config):
            node_name = list(event.keys())[0] if event else None
            if node_name:
                final_state = event[node_name]
                logger.debug("Node completed: %s", node_name)
    except Exception as exc:
        logger.error("Workflow stream error: %s", exc)

    # Read merged state from checkpointer
    try:
        snap = workflow.get_state(config)
        state_values = snap.values if snap and snap.values else (final_state or initial_state)
    except Exception:
        state_values = final_state or initial_state

    _persist_state_to_db(db, incident_id, state_values)
    return state_values


# ─────────────────────────────────────────────────────────
# Resume incident
# ─────────────────────────────────────────────────────────
def resume_incident(
    db: Session,
    thread_id: str,
    user_id: int,
    user_input: str,
    input_type: str,  # "verification_yes" | "verification_no" | "diagnostic"
) -> Dict[str, Any]:
    """
    Resume an in-progress incident.

    Strategy:
      1. Restore full state from DB.
      2. Apply the user's answer to the correct field.
      3. Call update_state(config, full_state, as_node=<tier>) so LangGraph seeds a
         fresh checkpoint that looks like <tier> node just finished.
      4. Call stream(None, config) to let the graph follow the conditional edge out
         of that node using the now-set answer field.
    """
    incident = repository.get_incident_by_thread(db, thread_id)
    if not incident:
        raise ValueError(f"Incident not found for thread_id {thread_id}")
    if incident.user_id != user_id:
        raise PermissionError("Access denied")
    if incident.status != "IN_PROGRESS":
        return restore_state_from_db(incident)

    # --- Step 1: restore full state ---
    state = restore_state_from_db(incident)
    config = {"configurable": {"thread_id": thread_id}}
    workflow = _get_workflow()

    # --- Step 2: apply answer + determine which tier node to resume from ---
    if input_type in ("verification_yes", "verification_no"):
        resolved = input_type == "verification_yes"
        state, as_node = _apply_verification(state, resolved)
    elif input_type == "diagnostic":
        state, as_node = _apply_diagnostic(state, user_input)
    else:
        as_node = "l1_resolution"

    logger.info("Resuming from as_node=%s, resolved=%s", as_node,
                state.get("user_resolved") or state.get("l2_resolved") or state.get("l3_resolved"))

    # --- Step 3: seed checkpointer so graph knows where it paused ---
    # IMPORTANT: exclude conversation_history from update_state.
    # conversation_history uses operator.add (append reducer), so passing the full
    # accumulated list here would re-append it on top of whatever is already in the
    # checkpointer, causing duplication. We strip it out; each node emits only its
    # own new messages, which the reducer then appends cleanly.
    state_without_history = {k: v for k, v in state.items() if k != "conversation_history"}
    try:
        workflow.update_state(config, state_without_history, as_node=as_node)
        logger.debug("update_state(as_node=%s) succeeded", as_node)
    except Exception as exc:
        logger.error("update_state failed: %s — falling back to direct stream", exc)
        return _resume_fallback(db, state, incident, config, workflow)

    # --- Step 4: stream(None) → follows conditional edge out of as_node ---
    final_state = dict(state)
    try:
        for event in workflow.stream(None, config=config):
            node_name = list(event.keys())[0] if event else None
            if node_name:
                node_out = event[node_name]
                # Merge non-history fields directly; history is handled by checkpointer
                for k, v in node_out.items():
                    if k != "conversation_history":
                        final_state[k] = v
                logger.debug("Resume node: %s", node_name)
                if final_state.get("awaiting_user_input"):
                    break
    except Exception as exc:
        logger.error("stream(None) error: %s — falling back", exc)
        return _resume_fallback(db, state, incident, config, workflow)

    # Read the fully-merged state from checkpointer — this is the authoritative
    # source for conversation_history (correctly accumulated by operator.add).
    try:
        snap = workflow.get_state(config)
        if snap and snap.values:
            final_state = snap.values
    except Exception:
        pass

    _persist_state_to_db(db, incident.incident_id, final_state)
    return final_state


# ─────────────────────────────────────────────────────────
# Fallback: bypass checkpointer entirely
# Runs the graph from a synthetic entry node with the answer already set.
# ─────────────────────────────────────────────────────────
def _resume_fallback(db, state, incident, config, workflow) -> Dict[str, Any]:
    """
    When update_state or stream(None) fails, run the remaining workflow by
    injecting the full state directly into the graph from the diagnostics or
    routing node, skipping already-completed nodes.
    """
    logger.warning("Using _resume_fallback for incident %s", incident.incident_id)

    # Determine a synthetic next-node to run from based on state
    l2 = state.get("l2_analysis") or {}
    l3 = state.get("l3_analysis") or {}
    user_resolved = state.get("user_resolved")
    l2_resolved   = state.get("l2_resolved")
    l3_resolved   = state.get("l3_resolved")
    diag_questions = state.get("diagnostic_questions") or []
    diag_answers   = state.get("diagnostic_answers") or []

    # Identify next node
    if l3 and l3_resolved is not None:
        next_node = "generate_final_response" if l3_resolved else "human_handoff"
    elif l2 and l2_resolved is not None:
        next_node = "generate_final_response" if l2_resolved else "l3_resolution"
    elif user_resolved is True:
        next_node = "generate_final_response"
    elif user_resolved is False:
        # Has diagnostic answers → go to routing; no answers → diagnostics
        next_node = "routing_decision" if diag_answers else "diagnostics"
    elif diag_answers and not diag_questions:
        next_node = "routing_decision"
    else:
        next_node = "diagnostics"

    # Build a fresh thread to avoid checkpoint conflicts
    fresh_thread = str(uuid.uuid4())
    fresh_config = {"configurable": {"thread_id": fresh_thread}}

    # Seed fresh checkpoint at the synthetic node — exclude history (append reducer)
    state_without_history = {k: v for k, v in state.items() if k != "conversation_history"}
    try:
        workflow.update_state(fresh_config, state_without_history, as_node=next_node)
    except Exception as exc:
        logger.error("Fallback update_state also failed: %s", exc)
        _persist_state_to_db(db, incident.incident_id, state)
        return state

    final_state = dict(state)
    try:
        for event in workflow.stream(None, config=fresh_config):
            node_name = list(event.keys())[0] if event else None
            if node_name:
                for k, v in event[node_name].items():
                    if k != "conversation_history":
                        final_state[k] = v
                if final_state.get("awaiting_user_input"):
                    break
    except Exception as exc:
        logger.error("Fallback stream error: %s", exc)
    try:
        snap = workflow.get_state(fresh_config)
        if snap and snap.values:
            final_state = snap.values
    except Exception:
        pass

    _persist_state_to_db(db, incident.incident_id, final_state)
    return final_state


# ─────────────────────────────────────────────────────────
# Apply answer helpers
# ─────────────────────────────────────────────────────────

def _apply_verification(state: Dict[str, Any], resolved: bool):
    """
    Apply YES/NO answer to the correct tier field.
    Returns (updated_state, as_node) where as_node is the tier node that
    just 'completed' — the graph will follow its conditional edge.
    """
    updated = dict(state)
    l2 = state.get("l2_analysis") or {}
    l3 = state.get("l3_analysis") or {}
    l2_resolved = state.get("l2_resolved")
    l3_resolved = state.get("l3_resolved")

    answer_text = "Yes, resolved." if resolved else "No, not resolved."

    if l3 and l3_resolved is None and l2:
        updated["l3_resolved"] = resolved
        as_node = "l3_resolution"
    elif l2 and l2_resolved is None:
        updated["l2_resolved"] = resolved
        as_node = "l2_resolution"
    else:
        updated["user_resolved"] = resolved
        as_node = "l1_resolution"

    updated["awaiting_user_input"] = False
    updated["user_input_type"] = "none"
    updated["conversation_history"] = list(state.get("conversation_history", [])) + [
        {"role": "user", "content": answer_text}
    ]
    return updated, as_node


def _apply_diagnostic(state: Dict[str, Any], answer: str):
    """
    Record diagnostic answer. Returns (updated_state, as_node).
    as_node = "diagnostics" so the graph runs routing_decision next.
    """
    updated   = dict(state)
    questions = list(state.get("diagnostic_questions", []))
    answers   = list(state.get("diagnostic_answers", []))

    unanswered = [q for q in questions if q.get("answer") is None]
    if unanswered:
        q    = unanswered[-1]
        q_id = q.get("question_id", "")
        for i, question in enumerate(questions):
            if question.get("question_id") == q_id:
                questions[i]           = dict(question)
                questions[i]["answer"] = answer
                break
        answers.append({"question_id": q_id, "answer": answer})

    updated["diagnostic_questions"] = questions
    updated["diagnostic_answers"]   = answers
    updated["awaiting_user_input"]  = False
    updated["user_input_type"]      = "none"
    updated["conversation_history"] = list(state.get("conversation_history", [])) + [
        {"role": "user", "content": answer}
    ]
    return updated, "diagnostics"


# ─────────────────────────────────────────────────────────
# DB persistence
# ─────────────────────────────────────────────────────────

def _persist_state_to_db(db: Session, incident_id: str, state: Dict[str, Any]) -> None:
    """Write workflow state to the database."""
    try:
        repository.update_incident(
            db, incident_id,
            retrieved_documents   = state.get("retrieved_documents", []),
            l1_resolution         = state.get("l1_resolution", {}),
            diagnostic_questions  = state.get("diagnostic_questions", []),
            diagnostic_answers    = state.get("diagnostic_answers", []),
            routing_decision      = state.get("routing_decision", ""),
            routing_confidence    = state.get("routing_confidence", 0.0),
            routing_reason        = state.get("routing_reason", ""),
            missing_information   = state.get("missing_information", []),
            l2_analysis           = state.get("l2_analysis", {}),
            l2_resolved           = state.get("l2_resolved"),
            l3_analysis           = state.get("l3_analysis", {}),
            l3_resolved           = state.get("l3_resolved"),
            human_handoff         = state.get("human_handoff", False),
            human_handoff_reason  = state.get("human_handoff_reason", ""),
            final_response        = state.get("final_response", ""),
            conversation_history  = state.get("conversation_history", []),
            status                = state.get("status", "IN_PROGRESS"),
            resolution_level      = state.get("resolution_level", ""),
        )

        # Create human handoff record if needed
        incident = repository.get_incident_by_id(db, incident_id)
        if incident and state.get("human_handoff") and not incident.handoff:
            from backend.database.models import HumanHandoff
            from backend.graph.nodes import (
                _format_l1_summary, _format_l2_summary,
                _format_l3_summary, _format_diagnostic_qa,
            )
            repository.create_handoff(db, HumanHandoff(
                incident_id          = incident.id,
                user_id              = incident.user_id,
                issue_summary        = state.get("query", ""),
                escalation_reason    = state.get("human_handoff_reason", ""),
                ai_confidence        = state.get("routing_confidence", 0.2),
                l1_summary           = _format_l1_summary(state.get("l1_resolution", {})),
                diagnostics_summary  = _format_diagnostic_qa(
                    state.get("diagnostic_questions", []),
                    state.get("diagnostic_answers", []),
                ),
                l2_summary           = _format_l2_summary(state.get("l2_analysis", {})),
                l3_summary           = _format_l3_summary(state.get("l3_analysis", {})),
            ))
    except Exception as exc:
        logger.error("Failed to persist state for %s: %s", incident_id, exc)
