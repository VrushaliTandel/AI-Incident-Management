"""
Incidents API router: user-facing incident management.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.repository import (
    get_incident_by_id,
    get_incidents_for_user,
    get_user_stats,
    delete_incident,
)
from backend.services.incident_service import create_new_incident, resume_incident
from backend.api.schemas import (
    NewIncidentRequest,
    ResumeIncidentRequest,
    IncidentListItem,
    IncidentDetail,
    WorkflowResponse,
)
from backend.api.deps import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.post("", response_model=WorkflowResponse, status_code=201)
def create_incident_endpoint(
    request: NewIncidentRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Start a new incident and run RAG + L1 resolution."""
    try:
        state = create_new_incident(db, current_user.id, request.query)
        return WorkflowResponse(
            incident_id=state.get("incident_id", ""),
            thread_id=state.get("thread_id", ""),
            awaiting_user_input=state.get("awaiting_user_input", False),
            user_input_type=state.get("user_input_type", "none"),
            current_node=state.get("current_node", ""),
            status=state.get("status", "IN_PROGRESS"),
            conversation_history=state.get("conversation_history", []),
        )
    except Exception as exc:
        logger.error("Failed to create incident: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to start incident: {str(exc)}")


@router.post("/{thread_id}/resume", response_model=WorkflowResponse)
def resume_incident_endpoint(
    thread_id: str,
    request: ResumeIncidentRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Resume an in-progress incident with user input."""
    try:
        # Map frontend input_type to service input_type
        # Frontend sends: "verification_yes", "verification_no", "diagnostic"
        # Also support legacy: "verification" with resolved bool
        input_type = request.input_type
        if input_type == "verification":
            input_type = "verification_yes" if request.resolved else "verification_no"

        state = resume_incident(
            db=db,
            thread_id=thread_id,
            user_id=current_user.id,
            user_input=request.user_input,
            input_type=input_type,
        )
        return WorkflowResponse(
            incident_id=state.get("incident_id", ""),
            thread_id=thread_id,
            awaiting_user_input=state.get("awaiting_user_input", False),
            user_input_type=state.get("user_input_type", "none"),
            current_node=state.get("current_node", ""),
            status=state.get("status", "IN_PROGRESS"),
            conversation_history=state.get("conversation_history", []),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("Resume incident failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Resume failed: {str(exc)}")


@router.get("/history", response_model=List[IncidentListItem])
def get_incident_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return the current user's incident history."""
    incidents = get_incidents_for_user(db, current_user.id, skip=skip, limit=limit)
    result = []
    for inc in incidents:
        result.append(
            IncidentListItem(
                incident_id=inc.incident_id,
                thread_id=inc.thread_id,
                user_id=inc.user_id,
                username=inc.user.username if inc.user else None,
                user_query=inc.user_query,
                status=inc.status,
                resolution_level=inc.resolution_level,
                created_at=inc.created_at,
                updated_at=inc.updated_at,
                human_handoff=inc.human_handoff or False,
            )
        )
    return result


@router.get("/stats")
def get_user_statistics(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return statistics for the current user."""
    return get_user_stats(db, current_user.id)


@router.delete("/{incident_id}", status_code=204)
def delete_incident_endpoint(
    incident_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Delete a user's own incident. Admins may use the admin endpoint instead."""
    incident = get_incident_by_id(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if incident.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    delete_incident(db, incident_id)


@router.get("/{incident_id}", response_model=IncidentDetail)
def get_incident_detail(
    incident_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return full incident details. Users can only access their own incidents."""
    incident = get_incident_by_id(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Enforce ownership (non-admin users)
    if current_user.role != "admin" and incident.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return IncidentDetail(
        incident_id=incident.incident_id,
        thread_id=incident.thread_id,
        user_id=incident.user_id,
        username=incident.user.username if incident.user else None,
        user_query=incident.user_query,
        retrieved_documents=incident.retrieved_documents,
        l1_resolution=incident.l1_resolution,
        diagnostic_questions=incident.diagnostic_questions,
        diagnostic_answers=incident.diagnostic_answers,
        routing_decision=incident.routing_decision,
        routing_confidence=incident.routing_confidence,
        routing_reason=incident.routing_reason,
        missing_information=incident.missing_information,
        l2_analysis=incident.l2_analysis,
        l2_resolved=incident.l2_resolved,
        l3_analysis=incident.l3_analysis,
        l3_resolved=incident.l3_resolved,
        human_handoff=incident.human_handoff or False,
        human_handoff_reason=incident.human_handoff_reason,
        final_response=incident.final_response,
        conversation_history=incident.conversation_history,
        status=incident.status,
        resolution_level=incident.resolution_level,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
    )
