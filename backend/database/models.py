"""
SQLAlchemy ORM models.
All tables are defined here and registered with Base.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, String, Text, JSON
)
from sqlalchemy.orm import relationship

from backend.database.connection import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ─────────────────────────────────────────────
# Users
# ─────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(16), nullable=False, default="user")   # "user" | "admin"
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    incidents = relationship("Incident", back_populates="user", cascade="all, delete-orphan")
    human_handoffs = relationship(
        "HumanHandoff",
        back_populates="user",
        foreign_keys="HumanHandoff.user_id",
    )
    evaluations = relationship("Evaluation", back_populates="created_by_user")


# ─────────────────────────────────────────────
# Incidents
# ─────────────────────────────────────────────
class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(String(64), unique=True, index=True, nullable=False,
                         default=lambda: str(uuid.uuid4()))
    thread_id = Column(String(64), unique=True, index=True, nullable=False,
                       default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    user_query = Column(Text, nullable=False)

    # RAG
    retrieved_documents = Column(JSON, default=list)

    # L1
    l1_resolution = Column(JSON, default=dict)

    # Diagnostics
    diagnostic_questions = Column(JSON, default=list)
    diagnostic_answers = Column(JSON, default=list)

    # Routing
    routing_decision = Column(String(32), default="")
    routing_confidence = Column(Float, default=0.0)
    routing_reason = Column(Text, default="")
    missing_information = Column(JSON, default=list)

    # L2
    l2_analysis = Column(JSON, default=dict)
    l2_resolved = Column(Boolean, nullable=True)

    # L3
    l3_analysis = Column(JSON, default=dict)
    l3_resolved = Column(Boolean, nullable=True)

    # Human Handoff
    human_handoff = Column(Boolean, default=False)
    human_handoff_reason = Column(Text, default="")

    # Final
    final_response = Column(Text, default="")
    conversation_history = Column(JSON, default=list)

    # Status
    status = Column(String(32), default="IN_PROGRESS")  # IN_PROGRESS | RESOLVED | ESCALATED
    resolution_level = Column(String(32), default="")   # L1 | L2 | L3 | HUMAN_HANDOFF

    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="incidents")
    handoff = relationship("HumanHandoff", back_populates="incident", uselist=False,
                           cascade="all, delete-orphan")


# ─────────────────────────────────────────────
# Human Handoffs
# ─────────────────────────────────────────────
class HumanHandoff(Base):
    __tablename__ = "human_handoffs"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"),
                         unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    issue_summary = Column(Text, nullable=False)
    escalation_reason = Column(Text, nullable=False)
    ai_confidence = Column(Float, default=0.0)

    l1_summary = Column(Text, default="")
    diagnostics_summary = Column(Text, default="")
    l2_summary = Column(Text, default="")
    l3_summary = Column(Text, default="")

    # Assignment
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_at = Column(DateTime(timezone=True), nullable=True)
    agent_notes = Column(Text, default="")

    # Resolution
    resolved_by_agent = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    incident = relationship("Incident", back_populates="handoff")
    user = relationship("User", foreign_keys=[user_id], back_populates="human_handoffs")
    assigned_agent = relationship("User", foreign_keys=[assigned_to])


# ─────────────────────────────────────────────
# Evaluations
# ─────────────────────────────────────────────
class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    test_case_id = Column(String(128), nullable=False)
    faithfulness = Column(Float, nullable=True)
    answer_relevancy = Column(Float, nullable=True)
    contextual_relevancy = Column(Float, nullable=True)
    contextual_precision = Column(Float, nullable=True)
    contextual_recall = Column(Float, nullable=True)
    overall_score = Column(Float, nullable=True)
    run_id = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_by_user = relationship("User", back_populates="evaluations")
