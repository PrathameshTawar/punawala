"""Auditor routes — async throughout."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db, Application, User
from app.auth import require_role
from app.repositories.application_repo import (
    serialize, save_auditor_review,
    get_applications_flagged, get_all_applications,
    get_rejection_reason_counts,
)
from app.schemas import ApplicationOut, ReviewResponse, RejectionReasonRow, AuditorStats

router = APIRouter(prefix="/auditor", tags=["auditor"])
AuditorUser = require_role("auditor", "admin")


class ReviewRequest(BaseModel):
    override: str = Field(..., pattern="^(Approved|Rejected)$")
    note:     str = Field(default="", max_length=2000)


@router.get("/queue", response_model=list[ApplicationOut])
async def review_queue(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuditorUser),
):
    """Flagged applications needing review. Reasons eagerly loaded (no N+1)."""
    apps = await get_applications_flagged(db)
    return [serialize(a) for a in apps]


@router.get("/applications", response_model=list[ApplicationOut])
async def all_applications(
    limit:  int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuditorUser),
):
    """All applications, newest first. Paginated."""
    apps = await get_all_applications(db, limit=limit, offset=offset)
    return [serialize(a) for a in apps]


@router.get("/all", response_model=list[ApplicationOut])
async def all_applications_compat(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuditorUser),
):
    """Backward-compatible alias for /applications."""
    return await all_applications(db=db, current_user=current_user)


@router.post("/{session_id}/review", response_model=ReviewResponse)
async def review_application(
    session_id: str,
    req: ReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuditorUser),
):
    try:
        await save_auditor_review(
            db,
            session_id   = session_id,
            override     = req.override,
            note         = req.note,
            auditor_id   = current_user.id,
            auditor_role = current_user.role,
        )
    except ValueError:
        raise HTTPException(404, "Application not found")
    return ReviewResponse(status="ok", override=req.override)


@router.get("/stats", response_model=AuditorStats)
async def stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuditorUser),
):
    total    = (await db.execute(select(func.count()).select_from(Application))).scalar()
    approved = (await db.execute(select(func.count()).select_from(Application).filter(Application.status == "Approved"))).scalar()
    rejected = (await db.execute(select(func.count()).select_from(Application).filter(Application.status == "Rejected"))).scalar()
    review   = (await db.execute(select(func.count()).select_from(Application).filter(Application.flagged == True))).scalar()
    return AuditorStats(
        total=total, approved=approved, rejected=rejected,
        pending_review=review,
        approval_rate=round(approved / total * 100, 1) if total else 0,
    )


@router.get("/stats/reasons", response_model=list[RejectionReasonRow])
async def rejection_reasons(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuditorUser),
):
    """Rejection breakdown by reason — enabled by the normalised DecisionReason table."""
    rows = await get_rejection_reason_counts(db)
    return [RejectionReasonRow(reason=r.reason, count=r.count) for r in rows]
