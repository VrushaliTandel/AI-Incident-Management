"""
LangGraph node implementations.
Each node function takes IncidentState and returns a partial state update.
"""
import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from backend.graph.state import IncidentState
from backend.graph.prompts import (
    L1_SYSTEM_PROMPT, L1_USER_PROMPT,
    DIAGNOSTIC_SYSTEM_PROMPT, DIAGNOSTIC_USER_PROMPT,
    ROUTING_SYSTEM_PROMPT, ROUTING_USER_PROMPT,
    ROUTING_ACK_SYSTEM_PROMPT, ROUTING_ACK_USER_PROMPT,
    L2_SYSTEM_PROMPT, L2_USER_PROMPT,
    L3_SYSTEM_PROMPT, L3_USER_PROMPT,
    HANDOFF_MESSAGE_SYSTEM_PROMPT, HANDOFF_MESSAGE_USER_PROMPT,
    FINAL_RESPONSE_SYSTEM_PROMPT, FINAL_RESPONSE_USER_PROMPT,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# LLM Factory
# ─────────────────────────────────────────────
def _get_llm(temperature: float = 0.3):
    from backend.config import get_settings
    settings = get_settings()
    if settings.openai_api_key:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.llm_model,
            temperature=temperature,
            openai_api_key=settings.openai_api_key,
        )
    # Fallback: try Ollama for local inference
    try:
        from langchain_community.chat_models import ChatOllama
        return ChatOllama(model="llama3.2", temperature=temperature)
    except Exception:
        raise RuntimeError(
            "No LLM configured. Set OPENAI_API_KEY in .env or install Ollama."
        )


def _call_llm_json(system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    """Call LLM and parse JSON response."""
    from langchain_core.messages import SystemMessage, HumanMessage
    llm = _get_llm()
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    response = llm.invoke(messages)
    content = response.content.strip()

    # Extract JSON from markdown code blocks if present
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        logger.warning("LLM returned non-JSON; attempting partial extraction.")
        # Try to find the JSON object
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
        raise


def _call_llm_text(system_prompt: str, user_prompt: str, fallback: str = "") -> str:
    """Call LLM and return plain text response (no JSON parsing)."""
    from langchain_core.messages import SystemMessage, HumanMessage
    try:
        llm = _get_llm(temperature=0.4)
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        response = llm.invoke(messages)
        return response.content.strip()
    except Exception as exc:
        logger.error("_call_llm_text failed: %s", exc)
        return fallback


def _format_diagnostic_qa(
    questions: List[Dict], answers: List[Dict]
) -> str:
    """Format diagnostic Q&A into readable text."""
    if not questions:
        return "No diagnostic questions asked yet."
    lines = []
    answer_map = {a["question_id"]: a["answer"] for a in answers}
    for q in questions:
        qid = q.get("question_id", "")
        ans = answer_map.get(qid, "Not answered yet")
        lines.append(f"Q: {q['question']}\nA: {ans}")
    return "\n\n".join(lines)


def _format_l1_summary(l1: Dict) -> str:
    if not l1:
        return "No L1 resolution attempted."
    steps = "\n".join(f"  - {s}" for s in l1.get("resolution_steps", []))
    return f"Root cause hypothesis: {l1.get('root_cause_hypothesis', 'N/A')}\nSteps:\n{steps}"


def _format_l2_summary(l2: Dict) -> str:
    if not l2:
        return "No L2 resolution attempted."
    steps = "\n".join(f"  - {s}" for s in l2.get("resolution_steps", []))
    return f"Root cause: {l2.get('root_cause_analysis', 'N/A')}\nSteps:\n{steps}"


def _format_l3_summary(l3: Dict) -> str:
    if not l3:
        return "No L3 resolution attempted."
    actions = "\n".join(f"  - {a}" for a in l3.get("recommended_actions", []))
    return f"Root cause: {l3.get('root_cause', 'N/A')}\nActions:\n{actions}"


# ─────────────────────────────────────────────
# Node: RAG Retrieval
# ─────────────────────────────────────────────
def rag_node(state: IncidentState) -> Dict[str, Any]:
    """Retrieve relevant documents from ChromaDB."""
    logger.info("[RAG] Retrieving documents for: %.60s", state["query"])
    try:
        from backend.rag.retriever import retrieve_documents, format_context
        docs = retrieve_documents(state["query"], k=5)
        doc_list = [
            {"content": d.page_content, "source": d.metadata.get("source", "unknown")}
            for d in docs
        ]
        context = format_context(docs)
    except Exception as exc:
        logger.error("[RAG] Retrieval failed: %s", exc)
        doc_list = []
        context = "Knowledge base temporarily unavailable."

    return {
        "retrieved_documents": doc_list,
        "context": context,
        "current_node": "rag",
        # Only emit new messages — operator.add reducer appends them to existing history
        "conversation_history": [],
    }


# ─────────────────────────────────────────────
# Node: L1 Resolution
# ─────────────────────────────────────────────
def l1_resolution_node(state: IncidentState) -> Dict[str, Any]:
    """Generate L1 resolution steps using RAG context."""
    logger.info("[L1] Generating resolution for: %.60s", state["query"])
    try:
        result = _call_llm_json(
            L1_SYSTEM_PROMPT,
            L1_USER_PROMPT.format(
                query=state["query"],
                context=state.get("context", ""),
            ),
        )
    except Exception as exc:
        logger.error("[L1] LLM call failed: %s", exc)
        result = {
            "root_cause_hypothesis": "Unable to determine — LLM unavailable",
            "confidence": 0.0,
            "itsm_category": "Other",
            "estimated_priority": "P3",
            "known_facts": [],
            "resolution_steps": [
                "Step 1: Check your internet connection",
                "Step 2: Restart the affected application",
                "Step 3: Contact IT support if issue persists",
            ],
            "verification_steps": ["Confirm the issue is resolved"],
            "summary": "I found some basic troubleshooting steps. Please try them.",
        }

    # Build formatted response for display
    category = result.get("itsm_category", "")
    priority = result.get("estimated_priority", "")
    meta = ""
    if category or priority:
        meta = f"*Category: {category}  |  Priority: {priority}*\n\n" if category and priority else ""

    steps_text = "\n".join(
        f"{i+1}. {s}" for i, s in enumerate(result.get("resolution_steps", []))
    )
    display_message = (
        f"**L1 Support — Initial Troubleshooting**\n\n"
        f"{meta}"
        f"{result.get('summary', '')}\n\n"
        f"**Please try these steps:**\n\n{steps_text}\n\n"
        f"---\n**Did these steps resolve your issue?**"
    )

    return {
        "l1_resolution": result,
        "current_node": "l1_resolution",
        "awaiting_user_input": True,
        "user_input_type": "verification",
        "user_resolved": None,
        "conversation_history": [{"role": "assistant", "content": display_message}],
    }


# ─────────────────────────────────────────────
# Node: Diagnostics
# ─────────────────────────────────────────────
def diagnostics_node(state: IncidentState) -> Dict[str, Any]:
    """Generate the next targeted diagnostic question."""
    logger.info("[DIAGNOSTICS] Round %d", state.get("diagnostic_round", 0) + 1)

    asked = state.get("asked_questions", [])
    prev_questions = state.get("diagnostic_questions", [])
    prev_answers = state.get("diagnostic_answers", [])
    diagnostic_round = state.get("diagnostic_round", 0) + 1

    previous_qa = _format_diagnostic_qa(prev_questions, prev_answers)
    missing_info = state.get("missing_information", [])
    missing_str = "\n".join(f"- {m}" for m in missing_info) if missing_info else "Unknown"

    try:
        result = _call_llm_json(
            DIAGNOSTIC_SYSTEM_PROMPT.replace("{round}", str(diagnostic_round)),
            DIAGNOSTIC_USER_PROMPT.format(
                query=state["query"],
                l1_summary=_format_l1_summary(state.get("l1_resolution", {})),
                previous_qa=previous_qa,
                missing_info=missing_str,
                round=diagnostic_round,
            ),
        )
    except Exception as exc:
        logger.error("[DIAGNOSTICS] LLM failed: %s", exc)
        result = {
            "question_id": f"diag_{diagnostic_round}",
            "question": "Can you describe what error message or behavior you observe?",
            "why_asking": "Fallback question",
        }

    q_id = result.get("question_id", f"diag_{diagnostic_round}")
    question_text = result.get("question", "Can you provide more details?")

    # Build the updated questions list — guard against duplicate IDs AND duplicate text
    already_asked_texts = {q.get("question", "").strip().lower() for q in prev_questions}
    is_duplicate = (
        q_id in asked
        or question_text.strip().lower() in already_asked_texts
    )
    updated_questions = list(prev_questions)
    if not is_duplicate:
        updated_questions.append({
            "question_id": q_id,
            "question": question_text,
            "answer": None,
        })
    else:
        # LLM returned a duplicate — force a new unique ID so the round still advances
        q_id = f"diag_{diagnostic_round}_retry"

    # Ask LLM to phrase the diagnostic preamble in the user's language
    # (only on the first diagnostic round; subsequent rounds just show the question)
    if diagnostic_round == 1:
        preamble = _call_llm_text(
            "You are an IT support assistant. Write ONE short sentence (max 12 words) "
            "acknowledging that L1 steps did not work and you will ask a few questions to diagnose further. "
            "Write it in the SAME language as the user's original incident query. "
            "Return ONLY the sentence.",
            f"Original incident: {state['query']}",
            fallback="Thank you — let me ask a few questions to better diagnose this.",
        )
        display_message = f"{preamble}\n\n**{question_text}**"
    else:
        display_message = f"**{question_text}**"

    return {
        "diagnostic_questions": updated_questions,
        "diagnostic_questions_text": question_text,
        "diagnostic_round": diagnostic_round,
        "asked_questions": asked + [q_id],
        "current_node": "diagnostics",
        "awaiting_user_input": True,
        "user_input_type": "diagnostic",
        "conversation_history": [{"role": "assistant", "content": display_message}],
    }


# ─────────────────────────────────────────────
# Node: Routing Decision
# ─────────────────────────────────────────────
def routing_decision_node(state: IncidentState) -> Dict[str, Any]:
    """Decide whether to go to L2, ask more questions, or escalate."""
    logger.info("[ROUTING] Making routing decision")

    prev_questions = state.get("diagnostic_questions", [])
    prev_answers = state.get("diagnostic_answers", [])
    current_round = state.get("diagnostic_round", 0)
    max_rounds = state.get("max_diagnostic_rounds", 3)

    try:
        result = _call_llm_json(
            ROUTING_SYSTEM_PROMPT.format(max_rounds=max_rounds),
            ROUTING_USER_PROMPT.format(
                query=state["query"],
                l1_summary=_format_l1_summary(state.get("l1_resolution", {})),
                diagnostic_qa=_format_diagnostic_qa(prev_questions, prev_answers),
                current_round=current_round,
                max_rounds=max_rounds,
            ),
        )
    except Exception as exc:
        logger.error("[ROUTING] LLM failed: %s", exc)
        result = {
            "routing_decision": "L2",
            "confidence": 0.5,
            "reason": "Proceeding to L2 due to routing error",
            "missing_information": [],
        }

    routing_decision = result.get("routing_decision", "L2")

    # Emit a visible acknowledgement in the user's language so there is no silent gap
    # between the user's diagnostic answer and the next tier's response.
    ack = _call_llm_text(
        ROUTING_ACK_SYSTEM_PROMPT,
        ROUTING_ACK_USER_PROMPT.format(
            query=state["query"],
            routing_decision=routing_decision,
        ),
        fallback="Thank you — analysing your answers now…",
    )

    return {
        "routing_decision": routing_decision,
        "routing_confidence": float(result.get("confidence", 0.5)),
        "routing_reason": result.get("reason", ""),
        "missing_information": result.get("missing_information", []),
        "current_node": "routing_decision",
        "awaiting_user_input": False,
        "user_input_type": "none",
        "conversation_history": [{"role": "assistant", "content": ack}],
    }


# ─────────────────────────────────────────────
# Node: L2 Resolution
# ─────────────────────────────────────────────
def l2_resolution_node(state: IncidentState) -> Dict[str, Any]:
    """Generate advanced L2 resolution steps."""
    logger.info("[L2] Generating L2 resolution")

    prev_questions = state.get("diagnostic_questions", [])
    prev_answers = state.get("diagnostic_answers", [])

    try:
        result = _call_llm_json(
            L2_SYSTEM_PROMPT,
            L2_USER_PROMPT.format(
                query=state["query"],
                context=state.get("context", ""),
                l1_summary=_format_l1_summary(state.get("l1_resolution", {})),
                diagnostic_qa=_format_diagnostic_qa(prev_questions, prev_answers),
                routing_reason=state.get("routing_reason", ""),
            ),
        )
    except Exception as exc:
        logger.error("[L2] LLM failed: %s", exc)
        result = {
            "root_cause_analysis": "Unable to determine — LLM unavailable",
            "confidence": 0.0,
            "predicted_closure_code": "Software",
            "known_facts": [],
            "remaining_unknowns": [],
            "resolution_steps": [
                "Step 1: Collect detailed system logs",
                "Step 2: Contact your network administrator",
                "Step 3: Check firewall and proxy settings",
            ],
            "verification_steps": ["Verify connectivity is restored"],
            "summary": "I have escalated to advanced troubleshooting.",
        }

    steps_text = "\n".join(
        f"{i+1}. {s}" for i, s in enumerate(result.get("resolution_steps", []))
    )
    closure_code = result.get("predicted_closure_code", "")
    closure_note = f"*Predicted closure code: {closure_code}*\n\n" if closure_code else ""
    display_message = (
        f"**L2 Support — Advanced Troubleshooting**\n\n"
        f"{closure_note}"
        f"{result.get('summary', '')}\n\n"
        f"**Advanced resolution steps:**\n\n{steps_text}\n\n"
        f"---\n**Did these steps resolve your issue?**"
    )

    return {
        "l2_analysis": result,
        "l2_resolved": None,
        "current_node": "l2_resolution",
        "awaiting_user_input": True,
        "user_input_type": "verification",
        "conversation_history": [{"role": "assistant", "content": display_message}],
    }


# ─────────────────────────────────────────────
# Node: L3 Resolution
# ─────────────────────────────────────────────
def l3_resolution_node(state: IncidentState) -> Dict[str, Any]:
    """Generate expert L3 advanced resolution steps."""
    logger.info("[L3] Generating L3 resolution")

    prev_questions = state.get("diagnostic_questions", [])
    prev_answers = state.get("diagnostic_answers", [])

    try:
        result = _call_llm_json(
            L3_SYSTEM_PROMPT,
            L3_USER_PROMPT.format(
                query=state["query"],
                context=state.get("context", ""),
                l1_summary=_format_l1_summary(state.get("l1_resolution", {})),
                diagnostic_qa=_format_diagnostic_qa(prev_questions, prev_answers),
                l2_summary=_format_l2_summary(state.get("l2_analysis", {})),
            ),
        )
    except Exception as exc:
        logger.error("[L3] LLM failed: %s", exc)
        result = {
            "root_cause": "Complex system issue requiring expert intervention",
            "confidence": 0.3,
            "known_facts": [],
            "remaining_unknowns": ["Root cause not fully identified"],
            "advanced_diagnostics": ["Capture full system logs"],
            "recommended_actions": [
                "Action 1: Collect comprehensive diagnostic bundle",
                "Action 2: Contact vendor support",
                "Action 3: Schedule maintenance window for deeper investigation",
            ],
            "verification_steps": ["Confirm with specialist"],
            "resolved": False,
            "human_handoff_required": False,
            "human_handoff_reason": "",
            "summary": "I've applied our most advanced troubleshooting steps.",
        }

    actions_text = "\n".join(
        f"{i+1}. {a}" for i, a in enumerate(result.get("recommended_actions", []))
    )
    display_message = (
        f"**I've escalated to our highest level of troubleshooting (L3 Expert Analysis).**\n\n"
        f"{result.get('summary', '')}\n\n"
        f"**Expert recommended actions:**\n\n{actions_text}\n\n"
        f"---\n**Did these advanced steps resolve your issue?**"
    )

    return {
        "l3_analysis": result,
        "l3_resolved": None,
        "current_node": "l3_resolution",
        "awaiting_user_input": True,
        "user_input_type": "verification",
        "conversation_history": [{"role": "assistant", "content": display_message}],
    }


# ─────────────────────────────────────────────
# Node: Human Handoff
# ─────────────────────────────────────────────
def human_handoff_node(state: IncidentState) -> Dict[str, Any]:
    """Create a human handoff record and mark the incident as escalated."""
    logger.info("[HUMAN HANDOFF] Creating escalation for incident: %s", state.get("incident_id"))

    l3 = state.get("l3_analysis", {})
    handoff_reason = (
        l3.get("human_handoff_reason", "")
        or state.get("routing_reason", "")
        or "Issue could not be resolved by AI at L1, L2, or L3 levels."
    )

    ai_confidence = float(l3.get("confidence", state.get("routing_confidence", 0.2)))

    # Generate the user-facing message via LLM so it matches the user's language
    display_message = _call_llm_text(
        HANDOFF_MESSAGE_SYSTEM_PROMPT,
        HANDOFF_MESSAGE_USER_PROMPT.format(
            query=state.get("query", ""),
            handoff_reason=handoff_reason,
            incident_id=state.get("incident_id", "N/A"),
        ),
        fallback=(
            "I was unable to resolve your issue automatically. "
            "Your incident has been escalated to a human support agent who will review all steps taken and contact you soon. "
            f"Incident ID: `{state.get('incident_id', 'N/A')}`"
        ),
    )

    return {
        "human_handoff": True,
        "human_handoff_reason": handoff_reason,
        "status": "ESCALATED",
        "resolution_level": "HUMAN_HANDOFF",
        "current_node": "human_handoff",
        "awaiting_user_input": False,
        "user_input_type": "none",
        "final_response": display_message,
        "conversation_history": [{"role": "assistant", "content": display_message}],
    }


# ─────────────────────────────────────────────
# Node: Generate Final Response
# ─────────────────────────────────────────────
def generate_final_response_node(state: IncidentState) -> Dict[str, Any]:
    """Generate the final success response and determine resolution level."""
    logger.info("[FINAL] Generating final response")

    # Determine resolution level
    if state.get("l3_resolved"):
        resolution_level = "L3"
    elif state.get("l2_resolved"):
        resolution_level = "L2"
    else:
        resolution_level = "L1"

    # Generate the confirmation message via LLM in the user's language
    final_response = _call_llm_text(
        FINAL_RESPONSE_SYSTEM_PROMPT,
        FINAL_RESPONSE_USER_PROMPT.format(
            query=state.get("query", ""),
            resolution_level=resolution_level,
        ),
        fallback=(
            f"Your issue has been resolved at {resolution_level}. "
            "Your incident has been marked as RESOLVED. "
            "You can refer back to this incident if the issue recurs."
        ),
    )

    return {
        "final_response": final_response,
        "status": "RESOLVED",
        "resolution_level": resolution_level,
        "current_node": "final_response",
        "awaiting_user_input": False,
        "user_input_type": "none",
        "conversation_history": [{"role": "assistant", "content": final_response}],
    }


# ─────────────────────────────────────────────
# Node: Persist Incident
# ─────────────────────────────────────────────
def persist_incident_node(state: IncidentState) -> Dict[str, Any]:
    """Save/update the incident to the database."""
    logger.info("[PERSIST] Saving incident: %s", state.get("incident_id"))
    try:
        from backend.database.connection import SessionLocal
        from backend.database.repository import (
            get_incident_by_id, update_incident, create_handoff
        )
        from backend.database.models import HumanHandoff

        db = SessionLocal()
        try:
            incident = get_incident_by_id(db, state["incident_id"])
            if incident:
                update_incident(
                    db,
                    state["incident_id"],
                    retrieved_documents=state.get("retrieved_documents", []),
                    l1_resolution=state.get("l1_resolution", {}),
                    diagnostic_questions=state.get("diagnostic_questions", []),
                    diagnostic_answers=state.get("diagnostic_answers", []),
                    routing_decision=state.get("routing_decision", ""),
                    routing_confidence=state.get("routing_confidence", 0.0),
                    routing_reason=state.get("routing_reason", ""),
                    missing_information=state.get("missing_information", []),
                    l2_analysis=state.get("l2_analysis", {}),
                    l2_resolved=state.get("l2_resolved"),
                    l3_analysis=state.get("l3_analysis", {}),
                    l3_resolved=state.get("l3_resolved"),
                    human_handoff=state.get("human_handoff", False),
                    human_handoff_reason=state.get("human_handoff_reason", ""),
                    final_response=state.get("final_response", ""),
                    conversation_history=state.get("conversation_history", []),
                    status=state.get("status", "IN_PROGRESS"),
                    resolution_level=state.get("resolution_level", ""),
                )

                # Create human handoff record if needed
                if state.get("human_handoff") and not incident.handoff:
                    l1 = state.get("l1_resolution", {})
                    l2 = state.get("l2_analysis", {})
                    l3 = state.get("l3_analysis", {})
                    handoff = HumanHandoff(
                        incident_id=incident.id,
                        user_id=incident.user_id,
                        issue_summary=state["query"],
                        escalation_reason=state.get("human_handoff_reason", ""),
                        ai_confidence=state.get("routing_confidence", 0.2),
                        l1_summary=_format_l1_summary(l1),
                        diagnostics_summary=_format_diagnostic_qa(
                            state.get("diagnostic_questions", []),
                            state.get("diagnostic_answers", []),
                        ),
                        l2_summary=_format_l2_summary(l2),
                        l3_summary=_format_l3_summary(l3),
                    )
                    create_handoff(db, handoff)
        finally:
            db.close()
    except Exception as exc:
        logger.error("[PERSIST] Failed to save incident: %s", exc)

    return {"current_node": "persisted"}
