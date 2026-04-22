"""
Audit trail routes — async throughout.
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db, AuditLog, Application, User
from app.auth import require_role, get_current_user

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/{session_id}")
async def get_audit_trail(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full audit trail for a session — every action, actor, timestamp."""
    app_result = await db.execute(
        select(Application).filter(Application.session_id == session_id)
    )
    app = app_result.scalar_one_or_none()
    if not app:
        raise HTTPException(404, "Session not found")
    if current_user.role == "applicant" and app.applicant_id != current_user.id:
        raise HTTPException(403, "Access denied")

    logs_result = await db.execute(
        select(AuditLog)
        .filter(AuditLog.session_id == session_id)
        .order_by(AuditLog.timestamp.asc())
    )
    logs = logs_result.scalars().all()

    return {
        "session_id": session_id,
        "events": [
            {
                "action":     log.action,
                "actor_id":   log.actor_id,
                "actor_role": log.actor_role,
                "detail":     _try_parse(log.detail),
                "timestamp":  log.timestamp.isoformat(),
            }
            for log in logs
        ],
    }


@router.get("/")
async def all_audit_logs(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("auditor", "admin")),
):
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)
    )
    logs = result.scalars().all()
    return [
        {
            "session_id": log.session_id,
            "action":     log.action,
            "actor_role": log.actor_role,
            "timestamp":  log.timestamp.isoformat(),
        }
        for log in logs
    ]


def _try_parse(s: str):
    try:
        return json.loads(s)
    except Exception:
        return s
