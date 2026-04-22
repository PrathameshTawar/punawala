"""
Repository layer tests — async.

Run: pytest tests/test_repository.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.database import Base, User
from app.auth import hash_password
from app.repositories.application_repo import (
    save_application, save_auditor_review, serialize,
    get_application_by_session,
)

TEST_URL    = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_URL)
TestSession = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def fresh_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db():
    async with TestSession() as session:
        yield session


@pytest_asyncio.fixture
async def user(db):
    u = User(username="testuser", hashed_password=hash_password("Secure@Pass1"),
             role="applicant", full_name="Test User")
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


APPROVED_RESULT = {
    "transcript": "I earn 50000 and I agree",
    "extracted":  {"income": 50000, "consent": True, "risk_level": "low"},
    "vision":     {"face_detected": True, "liveness_score": 0.92,
                   "spoof_detected": False, "multiple_faces": False, "screen_spoof": False},
    "decision":   {"status": "Approved",
                   "reasons_pass": ["Consent confirmed", "Income meets threshold"],
                   "reasons_fail": [], "confidence": 0.85, "emi": 15000,
                   "tenure": "24 months", "loan_amount": 600000,
                   "credit_score_band": "A", "model_version": "risk-engine-v2.1"},
    "timing_ms":  {"total": 305},
}

REJECTED_RESULT = {
    "transcript": "I don't agree",
    "extracted":  {"income": 0, "consent": False, "risk_level": "high"},
    "vision":     {"face_detected": True, "liveness_score": 0.85,
                   "spoof_detected": False, "multiple_faces": False, "screen_spoof": False},
    "decision":   {"status": "Rejected", "reasons_pass": [],
                   "reasons_fail": ["Verbal consent not recorded"],
                   "confidence": 0.05, "emi": None, "tenure": None,
                   "loan_amount": None, "credit_score_band": None,
                   "model_version": "risk-engine-v2.1"},
    "timing_ms":  {"total": 200},
}


@pytest.mark.asyncio
async def test_save_application_creates_record(db, user):
    app = await save_application(db, session_id="LW-TEST001", applicant_id=user.id,
                                 applicant_name=user.full_name, loan_product="personal",
                                 result=APPROVED_RESULT)
    assert app.session_id == "LW-TEST001"
    assert app.status == "Approved"
    assert app.income == 50000
    assert app.confidence == 0.85


@pytest.mark.asyncio
async def test_save_application_creates_reason_rows(db, user):
    app = await save_application(db, session_id="LW-TEST002", applicant_id=user.id,
                                 applicant_name=user.full_name, loan_product="personal",
                                 result=APPROVED_RESULT)
    pass_reasons = [r for r in app.reasons if r.kind == "pass"]
    fail_reasons = [r for r in app.reasons if r.kind == "fail"]
    assert len(pass_reasons) == 2
    assert len(fail_reasons) == 0


@pytest.mark.asyncio
async def test_save_application_creates_audit_log(db, user):
    from sqlalchemy import select
    from app.database import AuditLog
    await save_application(db, session_id="LW-TEST003", applicant_id=user.id,
                           applicant_name=user.full_name, loan_product="personal",
                           result=APPROVED_RESULT)
    result = await db.execute(select(AuditLog).filter(AuditLog.session_id == "LW-TEST003"))
    logs = result.scalars().all()
    assert len(logs) == 1
    assert logs[0].action == "KYC_SUBMITTED"


@pytest.mark.asyncio
async def test_save_application_rejected_has_fail_reasons(db, user):
    app = await save_application(db, session_id="LW-TEST004", applicant_id=user.id,
                                 applicant_name=user.full_name, loan_product="personal",
                                 result=REJECTED_RESULT)
    fail_reasons = [r for r in app.reasons if r.kind == "fail"]
    assert len(fail_reasons) == 1
    assert "consent" in fail_reasons[0].reason.lower()


@pytest.mark.asyncio
async def test_save_application_rollback_on_duplicate(db, user):
    await save_application(db, session_id="LW-DUPE", applicant_id=user.id,
                           applicant_name=user.full_name, loan_product="personal",
                           result=APPROVED_RESULT)
    with pytest.raises(Exception):
        await save_application(db, session_id="LW-DUPE", applicant_id=user.id,
                               applicant_name=user.full_name, loan_product="personal",
                               result=APPROVED_RESULT)


@pytest.mark.asyncio
async def test_auditor_review_updates_override(db, user):
    await save_application(db, session_id="LW-REV001", applicant_id=user.id,
                           applicant_name=user.full_name, loan_product="personal",
                           result=REJECTED_RESULT)
    await save_auditor_review(db, session_id="LW-REV001", override="Approved",
                              note="Manually verified", auditor_id=user.id,
                              auditor_role="auditor")
    app = await get_application_by_session(db, "LW-REV001")
    assert app.auditor_override == "Approved"
    assert app.auditor_note == "Manually verified"
    assert app.flagged == False


@pytest.mark.asyncio
async def test_auditor_review_creates_audit_log(db, user):
    from sqlalchemy import select
    from app.database import AuditLog
    await save_application(db, session_id="LW-REV002", applicant_id=user.id,
                           applicant_name=user.full_name, loan_product="personal",
                           result=REJECTED_RESULT)
    await save_auditor_review(db, session_id="LW-REV002", override="Rejected",
                              note="Confirmed fraud", auditor_id=user.id,
                              auditor_role="auditor")
    result = await db.execute(select(AuditLog).filter(AuditLog.session_id == "LW-REV002"))
    actions = [l.action for l in result.scalars().all()]
    assert "KYC_SUBMITTED" in actions
    assert "AUDITOR_REJECTED" in actions


@pytest.mark.asyncio
async def test_serialize_returns_reasons_lists(db, user):
    app = await save_application(db, session_id="LW-SER001", applicant_id=user.id,
                                 applicant_name=user.full_name, loan_product="personal",
                                 result=APPROVED_RESULT)
    data = serialize(app)
    assert isinstance(data["reasons_pass"], list)
    assert isinstance(data["reasons_fail"], list)
    assert len(data["reasons_pass"]) == 2


@pytest.mark.asyncio
async def test_serialize_uses_auditor_override_as_status(db, user):
    await save_application(db, session_id="LW-SER002", applicant_id=user.id,
                           applicant_name=user.full_name, loan_product="personal",
                           result=REJECTED_RESULT)
    await save_auditor_review(db, session_id="LW-SER002", override="Approved",
                              note="", auditor_id=user.id, auditor_role="auditor")
    app = await get_application_by_session(db, "LW-SER002")
    data = serialize(app)
    assert data["status"] == "Approved"     # override
    assert data["ai_status"] == "Rejected"  # original AI decision
