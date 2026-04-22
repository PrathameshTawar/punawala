"""
Application Repository — all database writes for KYC applications.

Fully async: uses AsyncSession and SQLAlchemy 2.0 select() style throughout.
Every write is atomic — rollback on any failure.
"""
import json
import logging
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import Application, DecisionReason, AuditLog

logger = logging.getLogger("app_repo")


async def save_application(
    db: AsyncSession,
    *,
    session_id: str,
    applicant_id: int,
    applicant_name: str,
    loan_product: str,
    result: dict,
) -> Application:
    """
    Persist a completed KYC result atomically.
    Application + DecisionReasons + AuditLog in one transaction.
    """
    extracted = result["extracted"]
    vision    = result["vision"]
    decision  = result["decision"]
    timing    = result.get("timing_ms", {})

    try:
        app = Application(
            session_id     = session_id,
            applicant_id   = applicant_id,
            applicant_name = applicant_name,
            loan_product   = loan_product,
            transcript     = result["transcript"],
            income         = extracted.get("income", 0),
            consent        = extracted.get("consent", False),
            risk_level     = extracted.get("risk_level", "medium"),
            face_detected  = vision.get("face_detected", False),
            liveness_score = vision.get("liveness_score", 0.0),
            spoof_detected = vision.get("spoof_detected", False),
            multiple_faces = vision.get("multiple_faces", False),
            screen_spoof   = vision.get("screen_spoof", False),
            status         = decision["status"],
            confidence     = decision.get("confidence", 0.0),
            credit_band    = decision.get("credit_score_band") or "",
            model_version  = decision.get("model_version", ""),
            emi            = decision.get("emi"),
            tenure         = decision.get("tenure"),
            loan_amount    = decision.get("loan_amount"),
            total_ms       = timing.get("total", 0),
            flagged        = (decision["status"] == "Manual Review"),
        )
        db.add(app)
        await db.flush()  # get app.id without committing

        # Normalised reason rows — enables GROUP BY queries on rejection reasons
        for r in decision.get("reasons_pass", []):
            db.add(DecisionReason(application_id=app.id, kind="pass", reason=r))
        for r in decision.get("reasons_fail", []):
            db.add(DecisionReason(application_id=app.id, kind="fail", reason=r))

        # Immutable audit log entry
        db.add(AuditLog(
            session_id = session_id,
            actor_id   = applicant_id,
            actor_role = "applicant",
            action     = "KYC_SUBMITTED",
            detail     = json.dumps({
                "status":     decision["status"],
                "confidence": decision.get("confidence"),
                "income":     extracted.get("income"),
                "risk_level": extracted.get("risk_level"),
                "liveness":   vision.get("liveness_score"),
                "product":    loan_product,
                "model":      decision.get("model_version"),
            }),
        ))

        await db.commit()
        await db.refresh(app)
        logger.info(f"Saved application session={session_id} status={decision['status']}")
        return app

    except Exception:
        await db.rollback()
        logger.exception(f"Failed to save application session={session_id}")
        raise


async def save_auditor_review(
    db: AsyncSession,
    *,
    session_id: str,
    override: str,
    note: str,
    auditor_id: int,
    auditor_role: str,
) -> None:
    """Persist an auditor override atomically."""
    try:
        result = await db.execute(
            select(Application).filter(Application.session_id == session_id)
        )
        app = result.scalar_one_or_none()
        if not app:
            raise ValueError(f"Application {session_id} not found")

        app.auditor_override = override
        app.auditor_note     = note
        app.auditor_id       = auditor_id
        app.reviewed_at      = datetime.now(timezone.utc)
        app.flagged          = False

        db.add(AuditLog(
            session_id = session_id,
            actor_id   = auditor_id,
            actor_role = auditor_role,
            action     = f"AUDITOR_{override.upper()}",
            detail     = note,
        ))

        await db.commit()

    except Exception:
        await db.rollback()
        logger.exception(f"Failed to save review session={session_id}")
        raise


async def get_applications_flagged(db: AsyncSession) -> list:
    """Auditor queue — flagged applications with reasons eagerly loaded."""
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.reasons))  # avoids N+1
        .filter(Application.flagged == True)
        .order_by(Application.created_at.desc())
    )
    return result.scalars().all()


async def get_all_applications(db: AsyncSession, limit: int = 50, offset: int = 0) -> list:
    """All applications with reasons eagerly loaded. Paginated."""
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.reasons))
        .order_by(Application.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


async def get_application_by_session(db: AsyncSession, session_id: str):
    """Single application with reasons eagerly loaded."""
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.reasons))
        .filter(Application.session_id == session_id)
    )
    return result.scalar_one_or_none()


async def get_applications_by_user(db: AsyncSession, applicant_id: int) -> list:
    """All applications for a specific user."""
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.reasons))
        .filter(Application.applicant_id == applicant_id)
        .order_by(Application.created_at.desc())
    )
    return result.scalars().all()


async def get_rejection_reason_counts(db: AsyncSession) -> list:
    """GROUP BY on DecisionReason — the whole point of normalising reasons."""
    result = await db.execute(
        select(DecisionReason.reason, func.count(DecisionReason.id).label("count"))
        .filter(DecisionReason.kind == "fail")
        .group_by(DecisionReason.reason)
        .order_by(func.count(DecisionReason.id).desc())
    )
    return result.all()


def serialize(app: Application) -> dict:
    """Single canonical serialiser — used by all routes."""
    reasons_pass = [r.reason for r in app.reasons if r.kind == "pass"]
    reasons_fail = [r.reason for r in app.reasons if r.kind == "fail"]

    return {
        "session_id":     app.session_id,
        "applicant_name": app.applicant_name,
        "loan_product":   app.loan_product,
        "status":         app.auditor_override or app.status,
        "ai_status":      app.status,
        "income":         app.income,
        "consent":        app.consent,
        "risk_level":     app.risk_level,
        "liveness_score": app.liveness_score,
        "confidence":     app.confidence,
        "credit_band":    app.credit_band,
        "model_version":  app.model_version,
        "emi":            app.emi,
        "tenure":         app.tenure,
        "loan_amount":    app.loan_amount,
        "reasons_pass":   reasons_pass,
        "reasons_fail":   reasons_fail,
        "transcript":     app.transcript,
        "flagged":        app.flagged,
        "auditor_note":   app.auditor_note,
        "total_ms":       app.total_ms,
        "created_at":     app.created_at.isoformat() if app.created_at else None,
        "reviewed_at":    app.reviewed_at.isoformat() if app.reviewed_at else None,
    }
