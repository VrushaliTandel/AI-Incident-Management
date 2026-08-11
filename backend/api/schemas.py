"""
Pydantic schemas for all API request/response models.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, field_validator


# ─────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────
class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        return v.strip()


class LoginRequest(BaseModel):
    username: str  # accepts username or email
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    role: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    incident_count: Optional[int] = None

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# Incidents
# ─────────────────────────────────────────────
class NewIncidentRequest(BaseModel):
    query: str

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        import re
        v = v.strip()
        if not v:
            raise ValueError("Query cannot be empty")
        if len(v) < 3:
            raise ValueError("Query is too short. Please describe the issue in more detail.")
        if len(v) > 5000:
            raise ValueError("Query is too long (max 5000 characters).")
        # Server-side prompt injection / jailbreak guard
        _BLOCKED = [
            r"(?i)(ignore|forget|disregard)\s+(previous|all|prior|above)\s+(instructions?|prompts?|rules?)",
            r"(?i)jailbreak",
            r"(?i)(drop|delete|truncate)\s+table",
            r"(?i)<\s*script",
            r"(?i)prompt\s*injection",
        ]
        for pattern in _BLOCKED:
            if re.search(pattern, v):
                raise ValueError("Input contains disallowed content.")
        return v


class ResumeIncidentRequest(BaseModel):
    user_input: str
    input_type: str  # "verification" | "diagnostic"
    resolved: Optional[bool] = None


class IncidentListItem(BaseModel):
    incident_id: str
    thread_id: str
    user_id: int
    username: Optional[str] = None
    user_query: str
    status: str
    resolution_level: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    human_handoff: bool = False

    class Config:
        from_attributes = True


class IncidentDetail(BaseModel):
    incident_id: str
    thread_id: str
    user_id: int
    username: Optional[str] = None
    user_query: str
    retrieved_documents: Optional[List[Dict]] = None
    l1_resolution: Optional[Dict] = None
    diagnostic_questions: Optional[List] = None
    diagnostic_answers: Optional[List] = None
    routing_decision: Optional[str] = None
    routing_confidence: Optional[float] = None
    routing_reason: Optional[str] = None
    missing_information: Optional[List] = None
    l2_analysis: Optional[Dict] = None
    l2_resolved: Optional[bool] = None
    l3_analysis: Optional[Dict] = None
    l3_resolved: Optional[bool] = None
    human_handoff: bool = False
    human_handoff_reason: Optional[str] = None
    final_response: Optional[str] = None
    conversation_history: Optional[List] = None
    status: str
    resolution_level: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WorkflowResponse(BaseModel):
    incident_id: str
    thread_id: str
    awaiting_user_input: bool
    user_input_type: str
    current_node: str
    status: str
    conversation_history: List[Dict[str, str]]


# ─────────────────────────────────────────────
# Admin
# ─────────────────────────────────────────────
class DashboardStats(BaseModel):
    total: int
    resolved: int
    escalated: int
    in_progress: int
    l1_resolved: int
    l2_resolved: int
    l3_resolved: int
    human_handoff: int
    resolution_rate: float
    escalation_rate: float


class HandoffResponse(BaseModel):
    id: int
    incident_id: int
    user_id: int
    username: Optional[str] = None
    issue_summary: str
    escalation_reason: str
    ai_confidence: float
    l1_summary: Optional[str] = None
    l2_summary: Optional[str] = None
    l3_summary: Optional[str] = None
    diagnostics_summary: Optional[str] = None
    assigned_to: Optional[int] = None
    assigned_at: Optional[datetime] = None
    agent_notes: Optional[str] = None
    resolved_by_agent: bool
    resolved_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TakeOwnershipRequest(BaseModel):
    pass  # No body needed — uses current user


class ResolveIncidentRequest(BaseModel):
    agent_notes: Optional[str] = None


class AddNotesRequest(BaseModel):
    notes: str


class UpdateUserRequest(BaseModel):
    is_active: Optional[bool] = None
    role: Optional[str] = None


# ─────────────────────────────────────────────
# Evaluation
# ─────────────────────────────────────────────
class EvaluationResult(BaseModel):
    test_case_id: str
    faithfulness: Optional[float]
    answer_relevancy: Optional[float]
    contextual_relevancy: Optional[float]
    contextual_precision: Optional[float]
    contextual_recall: Optional[float]
    overall_score: Optional[float]
    run_id: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EvaluationSummary(BaseModel):
    total_cases: int
    averages: Dict[str, Optional[float]]
    results: List[EvaluationResult]


# ─────────────────────────────────────────────
# System
# ─────────────────────────────────────────────
class SystemHealth(BaseModel):
    backend: str
    database: str
    chromadb: str
    llm: str
    rag: str
    llm_model: Optional[str] = None
    embedding_model: Optional[str] = None
    chroma_path: Optional[str] = None
    document_count: Optional[int] = None
