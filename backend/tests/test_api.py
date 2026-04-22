"""
HTTP-layer integration tests — async FastAPI with AsyncClient.

Uses pytest-asyncio + httpx.AsyncClient + aiosqlite in-memory DB.
AI pipeline is mocked so tests run without API keys.

Run: pytest tests/test_api.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestAsyncSession = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestAsyncSession() as session:
        yield session


@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_test_db():
    from app.database import Base, get_db
    from app.main import app
    from app.auth import hash_password
    from app.database import User

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.dependency_overrides[get_db] = override_get_db

    # Seed demo users
    async with TestAsyncSession() as db:
        db.add_all([
            User(username="applicant", hashed_password=hash_password("Demo@12345"),
                 role="applicant", full_name="Demo Applicant"),
            User(username="auditor",   hashed_password=hash_password("Demo@12345"),
                 role="auditor",   full_name="Bank Auditor"),
            User(username="admin",     hashed_password=hash_password("Demo@12345"),
                 role="admin",     full_name="System Admin"),
        ])
        await db.commit()

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="module")
async def client():
    from app.main import app
    from app.middleware import RateLimitMiddleware
    with patch.object(RateLimitMiddleware, "dispatch",
                      new=lambda self, req, call_next: call_next(req)):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as c:
            yield c


async def _get_token(client, username="applicant", password="Demo@12345"):
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ── Auth ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_valid_credentials(client):
    resp = await client.post("/api/v1/auth/login",
                             data={"username": "applicant", "password": "Demo@12345"},
                             headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    assert resp.json()["role"] == "applicant"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    resp = await client.post("/api/v1/auth/login",
                             data={"username": "applicant", "password": "wrong"},
                             headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client):
    resp = await client.post("/api/v1/auth/login",
                             data={"username": "nobody", "password": "demo123"},
                             headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_current_user(client):
    token = await _get_token(client)
    resp = await client.get("/api/v1/auth/me", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["username"] == "applicant"


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_register_new_user(client):
    resp = await client.post("/api/v1/auth/register",
                             json={"username": "newuser99", "password": "Secure@Pass1",
                                   "full_name": "New User"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "applicant"


@pytest.mark.asyncio
async def test_register_duplicate_username(client):
    await client.post("/api/v1/auth/register",
                      json={"username": "dupuser99", "password": "Secure@Pass1"})
    resp = await client.post("/api/v1/auth/register",
                             json={"username": "dupuser99", "password": "Secure@Pass1"})
    assert resp.status_code == 400


# ── KYC ───────────────────────────────────────────────────────────────────────

MOCK_PIPELINE_RESULT = {
    "transcript": "I earn 50000 per month and I agree",
    "extracted":  {"income": 50000, "consent": True, "risk_level": "low"},
    "vision":     {"face_detected": True, "liveness_score": 0.92, "spoof_detected": False,
                   "multiple_faces": False, "screen_spoof": False,
                   "gaze_consistent": True, "lighting_ok": True},
    "decision":   {"status": "Approved", "reasons_pass": ["Consent confirmed"],
                   "reasons_fail": [], "confidence": 0.85, "emi": 15000,
                   "tenure": "24 months", "loan_amount": 600000,
                   "credit_score_band": "A", "model_version": "risk-engine-v2.1"},
    "timing_ms":  {"voice_vision": 100, "llm": 200, "risk": 5, "total": 305},
}


@pytest.mark.asyncio
async def test_kyc_process_requires_auth(client):
    resp = await client.post("/api/v1/kyc/process",
                             files={"file": ("audio.wav", b"fake", "audio/wav")},
                             data={"loan_product": "personal"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_kyc_process_empty_file(client):
    token = await _get_token(client)
    resp = await client.post("/api/v1/kyc/process",
                             files={"file": ("audio.wav", b"", "audio/wav")},
                             data={"loan_product": "personal"},
                             headers=_auth(token))
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_kyc_process_invalid_product(client):
    token = await _get_token(client)
    resp = await client.post("/api/v1/kyc/process",
                             files={"file": ("audio.wav", b"fake", "audio/wav")},
                             data={"loan_product": "mortgage"},
                             headers=_auth(token))
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_kyc_process_success(client):
    token = await _get_token(client)
    with patch("app.services.kyc_service.run_agents",
               new=AsyncMock(return_value=MOCK_PIPELINE_RESULT)):
        resp = await client.post("/api/v1/kyc/process",
                                 files={"file": ("audio.wav", b"fake audio", "audio/wav")},
                                 data={"loan_product": "personal"},
                                 headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert data["session_id"].startswith("LW-")
    assert data["decision"]["status"] == "Approved"


@pytest.mark.asyncio
async def test_kyc_explain_returns_reasons(client):
    token = await _get_token(client)
    with patch("app.services.kyc_service.run_agents",
               new=AsyncMock(return_value=MOCK_PIPELINE_RESULT)):
        create_resp = await client.post(
            "/api/v1/kyc/process",
            files={"file": ("audio.wav", b"fake audio", "audio/wav")},
            data={"loan_product": "personal"},
            headers=_auth(token),
        )
    session_id = create_resp.json()["session_id"]
    resp = await client.get(f"/api/v1/kyc/{session_id}/explain", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert "reasons_pass" in data
    assert "reasons_fail" in data
    assert "confidence" in data


# ── Applications ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_my_applications_returns_list(client):
    token = await _get_token(client)
    resp = await client.get("/api/v1/applications/my", headers=_auth(token))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_applicant_cannot_see_others_application(client):
    token = await _get_token(client)
    with patch("app.services.kyc_service.run_agents",
               new=AsyncMock(return_value=MOCK_PIPELINE_RESULT)):
        create_resp = await client.post(
            "/api/v1/kyc/process",
            files={"file": ("audio.wav", b"fake", "audio/wav")},
            data={"loan_product": "personal"},
            headers=_auth(token),
        )
    session_id = create_resp.json()["session_id"]
    other_token = await _get_token(client, "newuser99", "Secure@Pass1")
    resp = await client.get(f"/api/v1/applications/{session_id}", headers=_auth(other_token))
    assert resp.status_code == 403


# ── Auditor ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_short_password_rejected(client):
    """Password validation: min 8 chars."""
    resp = await client.post("/api/v1/auth/register",
                             json={"username": "shortpw", "password": "abc"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_username_rejected(client):
    """Username validation: alphanumeric + _ - only."""
    resp = await client.post("/api/v1/auth/register",
                             json={"username": "bad user!", "password": "Secure@Pass1"})
    assert resp.status_code == 422
    token = await _get_token(client)
    resp = await client.get("/api/v1/auditor/queue", headers=_auth(token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_auditor_can_access_queue(client):
    token = await _get_token(client, "auditor", "Demo@12345")
    resp = await client.get("/api/v1/auditor/queue", headers=_auth(token))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_auditor_stats(client):
    token = await _get_token(client, "auditor", "Demo@12345")
    resp = await client.get("/api/v1/auditor/stats", headers=_auth(token))
    assert resp.status_code == 200
    assert "total" in resp.json()
    assert "approval_rate" in resp.json()


@pytest.mark.asyncio
async def test_auditor_rejection_reasons(client):
    token = await _get_token(client, "auditor", "Demo@12345")
    resp = await client.get("/api/v1/auditor/stats/reasons", headers=_auth(token))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_applicant_cannot_review(client):
    token = await _get_token(client)
    resp = await client.post("/api/v1/auditor/fake-session/review",
                             json={"override": "Approved", "note": ""},
                             headers=_auth(token))
    assert resp.status_code == 403


# ── Health ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_check(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] in ("ok", "degraded")  # degraded is fine in test env


@pytest.mark.asyncio
async def test_health_no_auth_required(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
