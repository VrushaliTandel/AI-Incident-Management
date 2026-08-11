"""
Admin API router: dashboard, handoffs, user management.
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.repository import (
    get_all_incidents,
    get_incident_by_id,
    get_handoffs,
    get_handoff_by_incident,
    update_handoff,
    update_incident,
    delete_incident,
    get_dashboard_stats,
    list_users,
    update_user,
    count_user_incidents,
)
from backend.api.schemas import (
    DashboardStats,
    HandoffResponse,
    IncidentListItem,
    IncidentDetail,
    ResolveIncidentRequest,
    AddNotesRequest,
    UpdateUserRequest,
    UserResponse,
)
from backend.api.deps import require_admin
from backend.services.analytics_service import get_admin_analytics

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard", response_model=DashboardStats)
def admin_dashboard(
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    stats = get_dashboard_stats(db)
    return DashboardStats(**stats)


@router.get("/incidents", response_model=List[IncidentListItem])
def admin_all_incidents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: Optional[str] = None,
    user_id: Optional[int] = None,
    resolution_level: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    incidents = get_all_incidents(
        db, skip=skip, limit=limit, status=status,
        user_id=user_id, resolution_level=resolution_level
    )
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


@router.get("/incidents/{incident_id}", response_model=IncidentDetail)
def admin_get_incident(
    incident_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    incident = get_incident_by_id(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
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


@router.get("/handoffs", response_model=List[HandoffResponse])
def get_handoffs_endpoint(
    resolved: Optional[bool] = None,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    handoffs = get_handoffs(db, resolved=resolved)
    result = []
    for h in handoffs:
        result.append(
            HandoffResponse(
                id=h.id,
                incident_id=h.incident_id,
                user_id=h.user_id,
                username=h.user.username if h.user else None,
                issue_summary=h.issue_summary,
                escalation_reason=h.escalation_reason,
                ai_confidence=h.ai_confidence,
                l1_summary=h.l1_summary,
                l2_summary=h.l2_summary,
                l3_summary=h.l3_summary,
                diagnostics_summary=h.diagnostics_summary,
                assigned_to=h.assigned_to,
                assigned_at=h.assigned_at,
                agent_notes=h.agent_notes,
                resolved_by_agent=h.resolved_by_agent,
                resolved_at=h.resolved_at,
                created_at=h.created_at,
            )
        )
    return result


@router.post("/incidents/{incident_id}/take-ownership")
def take_ownership(
    incident_id: str,
    db: Session = Depends(get_db),
    current_admin=Depends(require_admin),
):
    incident = get_incident_by_id(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if not incident.handoff:
        raise HTTPException(status_code=400, detail="No handoff record for this incident")
    handoff = incident.handoff
    update_handoff(
        db, handoff.id,
        assigned_to=current_admin.id,
        assigned_at=datetime.now(timezone.utc),
    )
    return {"message": "Ownership taken", "assigned_to": current_admin.username}


@router.post("/handoffs/{handoff_id}/take-ownership")
def take_ownership_by_handoff(
    handoff_id: int,
    db: Session = Depends(get_db),
    current_admin=Depends(require_admin),
):
    """Take ownership of a handoff directly by its own integer ID."""
    from backend.database.models import HumanHandoff as HHModel
    handoff = db.query(HHModel).filter(HHModel.id == handoff_id).first()
    if not handoff:
        raise HTTPException(status_code=404, detail="Handoff not found")
    update_handoff(
        db, handoff.id,
        assigned_to=current_admin.id,
        assigned_at=datetime.now(timezone.utc),
    )
    return {"message": "Ownership taken", "assigned_to": current_admin.username}


@router.post("/handoffs/{handoff_id}/resolve")
def resolve_handoff_by_id(
    handoff_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    """Mark a handoff as resolved directly by its own integer ID."""
    from backend.database.models import HumanHandoff as HHModel
    handoff = db.query(HHModel).filter(HHModel.id == handoff_id).first()
    if not handoff:
        raise HTTPException(status_code=404, detail="Handoff not found")
    update_handoff(
        db, handoff.id,
        resolved_by_agent=True,
        resolved_at=datetime.now(timezone.utc),
    )
    # Also mark the parent incident as RESOLVED
    if handoff.incident:
        update_incident(db, handoff.incident.incident_id, status="RESOLVED")
    return {"message": "Handoff resolved"}


@router.post("/handoffs/{handoff_id}/notes")
def add_notes_by_handoff_id(
    handoff_id: int,
    request: AddNotesRequest,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    """Add agent notes to a handoff by its own integer ID."""
    from backend.database.models import HumanHandoff as HHModel
    handoff = db.query(HHModel).filter(HHModel.id == handoff_id).first()
    if not handoff:
        raise HTTPException(status_code=404, detail="Handoff not found")
    current_notes = handoff.agent_notes or ""
    new_notes = f"{current_notes}\n{request.notes}".strip() if current_notes else request.notes
    update_handoff(db, handoff.id, agent_notes=new_notes)
    return {"message": "Notes saved"}


@router.delete("/incidents/{incident_id}", status_code=204)
def admin_delete_incident(
    incident_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    """Admin: permanently delete an incident."""
    incident = get_incident_by_id(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    delete_incident(db, incident_id)


@router.post("/incidents/{incident_id}/resolve")
def resolve_incident(
    incident_id: str,
    request: ResolveIncidentRequest,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    incident = get_incident_by_id(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    update_incident(db, incident_id, status="RESOLVED")
    if incident.handoff:
        update_handoff(
            db, incident.handoff.id,
            resolved_by_agent=True,
            resolved_at=datetime.now(timezone.utc),
            agent_notes=request.agent_notes or "",
        )
    return {"message": "Incident resolved"}


@router.post("/incidents/{incident_id}/notes")
def add_notes(
    incident_id: str,
    request: AddNotesRequest,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    incident = get_incident_by_id(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if incident.handoff:
        current_notes = incident.handoff.agent_notes or ""
        new_notes = f"{current_notes}\n{request.notes}".strip()
        update_handoff(db, incident.handoff.id, agent_notes=new_notes)
    return {"message": "Notes added"}


@router.get("/analytics")
def get_analytics(
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return get_admin_analytics(db)


@router.get("/users", response_model=List[UserResponse])
def list_all_users(
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    users = list_users(db)
    result = []
    for u in users:
        r = UserResponse(
            id=u.id,
            username=u.username,
            email=u.email,
            role=u.role,
            is_active=u.is_active,
            created_at=u.created_at,
            updated_at=u.updated_at,
            incident_count=count_user_incidents(db, u.id),
        )
        result.append(r)
    return result


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user_endpoint(
    user_id: int,
    request: UpdateUserRequest,
    db: Session = Depends(get_db),
    current_admin=Depends(require_admin),
):
    # Prevent admin from deactivating themselves
    if user_id == current_admin.id and request.is_active is False:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    kwargs = {}
    if request.is_active is not None:
        kwargs["is_active"] = request.is_active
    if request.role is not None:
        if request.role not in ("user", "admin"):
            raise HTTPException(status_code=400, detail="Invalid role")
        kwargs["role"] = request.role

    user = update_user(db, user_id, **kwargs)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
