"""
Pydantic response schemas — the public API contract.

Every route declares response_model= using one of these.
This gives: automatic response validation, correct OpenAPI docs, and a
defined contract that clients can rely on.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, Union
from pydantic import BaseModel, Field


# ── Auth ──────────────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type:   str
    role:         str
    full_name:    str


class UserMe(BaseModel):
    username:  str
    role:      str
    full_name: str


# ── KYC ───────────────────────────────────────────────────────────────────────

class ApplicationOut(BaseModel):
    session_id:     str
    applicant_name: str
    loan_product:   str
    status:         str
    ai_status:      str
    income:         int
    consent:        bool
    risk_level:     str
    liveness_score: float
    confidence:     float
    credit_band:    str
    model_version:  str
    emi:            Optional[int]
    tenure:         Optional[str]
    loan_amount:    Optional[int]
    reasons_pass:   list[str]
    reasons_fail:   list[str]
    transcript:     str
    flagged:        bool
    auditor_note:   str
    total_ms:       int
    created_at:     Optional[datetime]
    reviewed_at:    Optional[datetime]

    model_config = {"from_attributes": True, "protected_namespaces": ()}


class KYCResult(BaseModel):
    session_id: str
    transcript: str
    extracted:  dict
    vision:     dict
    decision:   dict
    timing_ms:  dict


# ── Auditor ───────────────────────────────────────────────────────────────────

class ReviewResponse(BaseModel):
    status:   str
    override: str


class RejectionReasonRow(BaseModel):
    reason: str
    count:  int


class AuditorStats(BaseModel):
    total:          int
    approved:       int
    rejected:       int
    pending_review: int
    approval_rate:  float


# ── Audit ─────────────────────────────────────────────────────────────────────

class AuditEvent(BaseModel):
    action:     str
    actor_id:   int
    actor_role: str
    detail:     Union[dict, str]
    timestamp:  datetime


class AuditTrail(BaseModel):
    session_id: str
    events:     list[AuditEvent]


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status:      str
    version:     str
    environment: str
    database:    str = "unknown"
    redis:       Optional[str] = None
