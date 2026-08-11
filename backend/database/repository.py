"""
Repository layer: all database CRUD operations.
Business logic lives in services; this module only touches the DB.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from backend.database.models import User, Incident, HumanHandoff, Evaluation

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# User repository
# ─────────────────────────────────────────────
def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_user_by_username_or_email(db: Session, login: str) -> Optional[User]:
    return (
        db.query(User)
        .filter((User.username == login) | (User.email == login))
        .first()
    )


def create_user(
    db: Session,
    username: str,
    email: str,
    password_hash: str,
    role: str = "user",
) -> User:
    user = User(username=username, email=email, password_hash=password_hash, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session, skip: int = 0, limit: int = 200) -> List[User]:
    return db.query(User).order_by(User.created_at.desc()).offset(skip).limit(limit).all()


def update_user(db: Session, user_id: int, **kwargs) -> Optional[User]:
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    for k, v in kwargs.items():
        if hasattr(user, k):
            setattr(user, k, v)
    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user


def count_user_incidents(db: Session, user_id: int) -> int:
    return db.query(func.count(Incident.id)).filter(Incident.user_id == user_id).scalar() or 0


# ─────────────────────────────────────────────
# Incident repository
# ─────────────────────────────────────────────
def create_incident(db: Session, incident: Incident) -> Incident:
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


def get_incident_by_id(db: Session, incident_id: str) -> Optional[Incident]:
    return db.query(Incident).filter(Incident.incident_id == incident_id).first()


def get_incident_by_thread(db: Session, thread_id: str) -> Optional[Incident]:
    return db.query(Incident).filter(Incident.thread_id == thread_id).first()


def get_incidents_for_user(
    db: Session, user_id: int, skip: int = 0, limit: int = 100
) -> List[Incident]:
    return (
        db.query(Incident)
        .filter(Incident.user_id == user_id)
        .order_by(desc(Incident.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_all_incidents(
    db: Session,
    skip: int = 0,
    limit: int = 200,
    status: Optional[str] = None,
    user_id: Optional[int] = None,
    resolution_level: Optional[str] = None,
) -> List[Incident]:
    q = db.query(Incident)
    if status:
        q = q.filter(Incident.status == status)
    if user_id:
        q = q.filter(Incident.user_id == user_id)
    if resolution_level:
        q = q.filter(Incident.resolution_level == resolution_level)
    return q.order_by(desc(Incident.created_at)).offset(skip).limit(limit).all()


def update_incident(db: Session, incident_id: str, **kwargs) -> Optional[Incident]:
    incident = get_incident_by_id(db, incident_id)
    if not incident:
        return None
    for k, v in kwargs.items():
        if hasattr(incident, k):
            setattr(incident, k, v)
    incident.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(incident)
    return incident


def delete_incident(db: Session, incident_id: str) -> bool:
    """Delete an incident (and cascade-delete its handoff). Returns True if deleted."""
    incident = get_incident_by_id(db, incident_id)
    if not incident:
        return False
    db.delete(incident)
    db.commit()
    return True


def get_dashboard_stats(db: Session) -> dict:
    total = db.query(func.count(Incident.id)).scalar() or 0
    resolved = db.query(func.count(Incident.id)).filter(Incident.status == "RESOLVED").scalar() or 0
    escalated = db.query(func.count(Incident.id)).filter(Incident.status == "ESCALATED").scalar() or 0
    in_progress = db.query(func.count(Incident.id)).filter(Incident.status == "IN_PROGRESS").scalar() or 0
    l1 = db.query(func.count(Incident.id)).filter(Incident.resolution_level == "L1").scalar() or 0
    l2 = db.query(func.count(Incident.id)).filter(Incident.resolution_level == "L2").scalar() or 0
    l3 = db.query(func.count(Incident.id)).filter(Incident.resolution_level == "L3").scalar() or 0
    handoff = db.query(func.count(Incident.id)).filter(Incident.resolution_level == "HUMAN_HANDOFF").scalar() or 0
    return {
        "total": total,
        "resolved": resolved,
        "escalated": escalated,
        "in_progress": in_progress,
        "l1_resolved": l1,
        "l2_resolved": l2,
        "l3_resolved": l3,
        "human_handoff": handoff,
        "resolution_rate": round(resolved / total * 100, 1) if total else 0,
        "escalation_rate": round(escalated / total * 100, 1) if total else 0,
    }


def get_user_stats(db: Session, user_id: int) -> dict:
    total = db.query(func.count(Incident.id)).filter(Incident.user_id == user_id).scalar() or 0
    resolved = db.query(func.count(Incident.id)).filter(Incident.user_id == user_id, Incident.status == "RESOLVED").scalar() or 0
    escalated = db.query(func.count(Incident.id)).filter(Incident.user_id == user_id, Incident.status == "ESCALATED").scalar() or 0
    in_progress = db.query(func.count(Incident.id)).filter(Incident.user_id == user_id, Incident.status == "IN_PROGRESS").scalar() or 0
    return {"total": total, "resolved": resolved, "escalated": escalated, "in_progress": in_progress}


# ─────────────────────────────────────────────
# Human Handoff repository
# ─────────────────────────────────────────────
def create_handoff(db: Session, handoff: HumanHandoff) -> HumanHandoff:
    db.add(handoff)
    db.commit()
    db.refresh(handoff)
    return handoff


def get_handoffs(
    db: Session, skip: int = 0, limit: int = 100, resolved: Optional[bool] = None
) -> List[HumanHandoff]:
    q = db.query(HumanHandoff)
    if resolved is not None:
        q = q.filter(HumanHandoff.resolved_by_agent == resolved)
    return q.order_by(desc(HumanHandoff.created_at)).offset(skip).limit(limit).all()


def get_handoff_by_incident(db: Session, incident_db_id: int) -> Optional[HumanHandoff]:
    return db.query(HumanHandoff).filter(HumanHandoff.incident_id == incident_db_id).first()


def update_handoff(db: Session, handoff_id: int, **kwargs) -> Optional[HumanHandoff]:
    handoff = db.query(HumanHandoff).filter(HumanHandoff.id == handoff_id).first()
    if not handoff:
        return None
    for k, v in kwargs.items():
        if hasattr(handoff, k):
            setattr(handoff, k, v)
    handoff.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(handoff)
    return handoff


# ─────────────────────────────────────────────
# Evaluation repository
# ─────────────────────────────────────────────
def save_evaluations(db: Session, evaluations: List[Evaluation]) -> List[Evaluation]:
    for ev in evaluations:
        db.add(ev)
    db.commit()
    for ev in evaluations:
        db.refresh(ev)
    return evaluations


def get_latest_evaluations(db: Session, limit: int = 50) -> List[Evaluation]:
    return db.query(Evaluation).order_by(desc(Evaluation.created_at)).limit(limit).all()


def get_evaluation_runs(db: Session) -> List[str]:
    """Return distinct run_ids ordered by most recent."""
    rows = (
        db.query(Evaluation.run_id, func.max(Evaluation.created_at).label("ts"))
        .group_by(Evaluation.run_id)
        .order_by(desc("ts"))
        .limit(20)
        .all()
    )
    return [r[0] for r in rows]


def get_evaluations_by_run(db: Session, run_id: str) -> List[Evaluation]:
    return (
        db.query(Evaluation)
        .filter(Evaluation.run_id == run_id)
        .order_by(Evaluation.id)
        .all()
    )
