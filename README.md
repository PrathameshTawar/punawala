# KYC Intelligence Platform

> A production-grade AI system for real-time loan onboarding and identity verification using multimodal processing.

---

## The Problem

Traditional KYC systems fail on three fronts:

- High drop-offs — long forms, slow UX, users abandon mid-flow
- Fraud vulnerability — static data entry can't verify identity or detect spoofing
- Manual overhead — human reviewers create bottlenecks that don't scale

## The Solution

A real-time video-based onboarding system powered by a parallel pipeline architecture:

- Voice extractor identifies income and consent from natural speech
- Vision extractor detects liveness, spoofing, and fraud signals
- LLM structures and classifies behavioral signals
- Deterministic risk engine makes the final decision — AI never decides alone

---

## Architecture

```
┌─────────────────────┐
│   React Frontend    │
└──────────┬──────────┘
           │ JWT-authenticated requests
    ┌──────▼──────────────────────────────┐
    │         API Gateway (FastAPI)        │
    │   Rate limiting · Request tracing    │
    └──────┬──────────────────────────────┘
           │
    ┌──────▼──────────────────────────────────────────┐
    │              AI Orchestrator                     │
    │                                                  │
    │  [Voice Extractor] ──┐                               │
    │                  ├──► [LLM Extractor] ──► [Risk Engine] ──► Decision
    │  [Vision Extractor] ─┘                               │
    └──────────────────────────────────────────────────┘
           │
    ┌──────▼──────────────────────────────┐
    │         Audit Service               │
    │  Every action · Every actor ·       │
    │  Every decision · Model version     │
    └──────────────────────────────────────┘
           │
    ┌──────▼──────────────────────────────┐
    │         SQLite / PostgreSQL          │
    │  Users · Applications · Audit Logs  │
    └──────────────────────────────────────┘
```

### Data Flow

```
User speaks → Audio captured (MediaRecorder)
           → Voice Extractor  → Transcript
           → Vision Extractor → Liveness score, fraud signals   (parallel)
           → LLM Extractor    → {income, consent, risk_level}
           → Validators       → Type-safe, bounded inputs
           → Risk Engine  → Decision + reasons[] + confidence
           → Database     → Persisted with full audit trail
           → Frontend     → Explainability panel rendered
```

---

## Key Design Principles

| Principle | Implementation |
|---|---|
| AI is bounded, not trusted | LLM extracts only — rule engine decides |
| Every decision is explainable | `reasons_pass[]` + `reasons_fail[]` on every response |
| System is observable | Request tracing, structured logging, timing on every pipeline run |
| Failures are handled | LLM retry + regex fallback — pipeline never crashes |
| Every action is auditable | Immutable audit log with actor, role, timestamp, model version |
| Inputs are validated | All AI outputs pass through `validators.py` before the rule engine |

---

## Features

- Real-time WebSocket streaming KYC
- Parallel task execution (voice + vision via `asyncio.gather`)
- Multi-product loan engine (personal, home, business, vehicle)
- Credit score band (A/B/C/D) per application
- Risk-adjusted EMI calculation
- Decision confidence score (0–100%)
- Full explainability panel — every rule evaluated, pass/fail
- Decision simulation mode — drag sliders, see live rule engine output
- Auditor review queue with override + notes
- Immutable audit trail per session
- Rate limiting (30 req/min per IP)
- Request ID tracing on every response header
- JWT auth with role-based access (applicant / auditor / admin)
- Demo users auto-seeded on first startup

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Recharts, MediaRecorder API |
| Backend | FastAPI, Python 3.10, SQLAlchemy |
| AI — Speech | OpenAI Whisper (regex fallback) |
| AI — Extraction | GPT-4o-mini (regex fallback) |
| AI — Vision | Simulated (MediaPipe / DeepFace in production) |
| Auth | JWT (python-jose), bcrypt |
| Database | SQLite (swap to PostgreSQL for production) |
| Real-time | WebSockets |

---

## Run Locally

**Backend**
```bash
cd loan-wizard/backend
pip install -r requirements.txt
# Optional: set OPENAI_API_KEY in .env (fallback demo mode works without it)
uvicorn app.main:app --reload
```

**Frontend**
```bash
cd loan-wizard/frontend
npm install
npm start
```

**Demo accounts** (auto-seeded on first run)

| Role | Username | Password |
|---|---|---|
| Applicant | applicant | demo123 |
| Auditor | auditor | demo123 |
| Admin | admin | demo123 |

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/auth/login` | Get JWT token |
| POST | `/api/v1/kyc/process` | Submit audio for KYC |
| GET | `/api/v1/kyc/{id}/explain` | Full decision breakdown |
| GET | `/api/v1/applications/my` | Applicant's history |
| GET | `/api/v1/auditor/queue` | Flagged applications |
| POST | `/api/v1/auditor/{id}/review` | Auditor override |
| GET | `/api/v1/audit/{id}` | Full audit trail |
| GET | `/health` | Service health |

---

## Loan Products

| Product | Min Income | EMI Ratio | Max Tenure |
|---|---|---|---|
| Personal | ₹25,000 | 30% | 24 months |
| Home | ₹60,000 | 40% | 240 months |
| Business | ₹50,000 | 35% | 60 months |
| Vehicle | ₹30,000 | 25% | 60 months |

---

## Production Roadmap

- Replace vision simulation with MediaPipe / DeepFace liveness detection
- Kafka event bus for service decoupling and replay capability
- Redis for distributed rate limiting and session caching
- Prometheus + Grafana for metrics and alerting
- Kubernetes deployment with horizontal pod autoscaling
- Model versioning and A/B testing framework
- Credit bureau API integration
