# System Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        React Frontend                           │
│   Login · KYC Session · Simulation Mode · Application History  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTPS / WSS
                            │ JWT on every request
┌───────────────────────────▼─────────────────────────────────────┐
│                    API Gateway (FastAPI)                         │
│   Rate limiting (30 req/min) · Request ID tracing               │
│   JWT validation · Role-based routing                           │
│   /api/v1/auth  /api/v1/kyc  /api/v1/auditor  /api/v1/audit    │
└──────┬──────────────┬──────────────┬──────────────┬─────────────┘
       │              │              │              │
  ┌────▼────┐   ┌─────▼─────┐  ┌────▼────┐  ┌─────▼──────┐
  │  Auth   │   │    KYC    │  │ Auditor │  │   Audit    │
  │ Service │   │  Service  │  │ Service │  │  Service   │
  └─────────┘   └─────┬─────┘  └─────────┘  └────────────┘
                      │
         ┌────────────▼────────────────────┐
         │        AI Orchestrator           │
         │   asyncio.gather — parallel      │
         │                                  │
         │  ┌─────────────┐ ┌────────────┐ │
         │  │ Voice Agent │ │Vision Agent│ │  ← Stage 1 (parallel)
         │  │  (Whisper)  │ │(Liveness)  │ │
         │  └──────┬──────┘ └─────┬──────┘ │
         │         └──────┬───────┘        │
         │         ┌──────▼──────┐         │
         │         │  LLM Agent  │         │  ← Stage 2
         │         │ (GPT-4o-mini│         │
         │         └──────┬──────┘         │
         │         ┌──────▼──────┐         │
         │         │  Validators │         │  ← Guardrail layer
         │         │ (sanitize)  │         │
         │         └──────┬──────┘         │
         │         ┌──────▼──────┐         │
         │         │ Risk Engine │         │  ← Stage 3 (deterministic)
         │         │  (rules)    │         │
         │         └──────┬──────┘         │
         └────────────────┼────────────────┘
                          │
         ┌────────────────▼────────────────┐
         │           SQLite / PostgreSQL    │
         │  users · applications · audit_logs│
         └──────────────────────────────────┘
```

---

## Decision Pipeline (Detail)

```
Raw Audio
    │
    ▼
Voice Agent ──────────────────────────────────────────────────────┐
    │  transcript: str                                             │
    │                                                              │ parallel
Vision Agent ─────────────────────────────────────────────────────┘
    │  {face_detected, liveness_score, spoof_detected,
    │   multiple_faces, screen_spoof, gaze_consistent}
    │
    ▼
LLM Agent (GPT-4o-mini)
    │  Attempt 1 → Attempt 2 (500ms backoff) → Regex fallback
    │  {income: int, consent: bool, risk_level: low|medium|high}
    │
    ▼
Validators (guardrail layer)
    │  Type coercion · Range clamping · Enum validation
    │  "Assume AI output is wrong by default"
    │
    ▼
Risk Engine (deterministic — no AI)
    │
    ├─ Hard stops (fraud):  spoof / screen_spoof / multiple_faces
    ├─ Compliance:          consent required
    ├─ Liveness:            score ≥ 0.50
    ├─ Behavioral:          high risk → Manual Review
    └─ Eligibility:         income ≥ product minimum
    │
    ▼
Decision
    {status, reasons_pass[], reasons_fail[],
     confidence, emi, tenure, loan_amount,
     credit_score_band, model_version}
    │
    ▼
Audit Log (immutable)
    {session_id, actor, role, action, detail{}, schema_version, timestamp}
```

---

## Data Model

```
users
  id · username · hashed_password · role · full_name · created_at

applications
  session_id · applicant_id · loan_product
  transcript · income · consent · risk_level          ← voice/LLM
  face_detected · liveness_score · spoof_detected     ← vision
  multiple_faces · screen_spoof
  status · reasons_pass · reasons_fail                ← decision
  confidence · credit_band · model_version · emi
  tenure · loan_amount · total_ms
  auditor_id · auditor_note · auditor_override        ← review
  flagged · created_at · reviewed_at

audit_logs
  session_id · actor_id · actor_role
  action · detail (JSON) · timestamp
```

---

## Security Model

```
Request
  → RateLimitMiddleware   (30 req/min per IP, in-memory)
  → RequestTracingMiddleware  (X-Request-ID header)
  → CORSMiddleware
  → Route handler
      → get_current_user()   (JWT decode + DB lookup)
      → require_role()       (applicant | auditor | admin)
      → Business logic
```

Token payload:
```json
{"sub": "username", "role": "applicant|auditor|admin", "exp": 1234567890}
```

---

## Resilience Model

```
LLM Agent:
  Call GPT-4o-mini
    → Success: parse JSON strictly
    → Failure: wait 500ms, retry
      → Success: parse JSON
      → Failure: regex fallback (always succeeds)

Vision Agent:
  Isolated — failure does not block voice pipeline
  Returns conservative defaults on error

Risk Engine:
  Pure function — no I/O, no external calls
  Cannot fail — always returns a valid decision dict
```

---

## Observability

Every request:
- `X-Request-ID` header on response
- `X-Response-Time` header on response
- Structured log: `METHOD /path → STATUS [Xms] id=XXXX`

Every pipeline run:
```json
{
  "loan_product": "personal",
  "status": "Approved",
  "confidence": 0.847,
  "stage1_ms": 120,
  "stage2_ms": 340,
  "stage3_ms": 2,
  "total_ms": 462
}
```

---

## Production Scaling Path

```
Current (single process):
  uvicorn app.main:app

Next (multi-worker):
  uvicorn app.main:app --workers 4

Production (containerized):
  docker-compose up          ← backend + frontend + nginx

Scale-out (Kubernetes):
  kubectl apply -f infra/k8s/
  HorizontalPodAutoscaler on CPU/request-rate

Event-driven (Kafka):
  Audio received → Kafka topic: kyc.audio.received
  Voice done     → Kafka topic: kyc.transcript.ready
  Decision made  → Kafka topic: kyc.decision.complete
  Audit event    → Kafka topic: kyc.audit.log
```

---

## Test Coverage

```
tests/test_risk_engine.py       — 21 tests  (every rule, every boundary)
tests/test_validators.py        — 20 tests  (every field, every edge case)
tests/test_pipeline_integration.py — 7 tests (full pipeline with mocked AI)

Total: 48 tests, 48 passing
```

Run:
```bash
cd backend
pytest tests/ -v
```
