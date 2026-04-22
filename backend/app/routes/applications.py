"""Applications routes — async throughout."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db, User
from app.auth import get_current_user
from app.repositories.application_repo import (
    serialize, get_application_by_session, get_applications_by_user,
)
from app.schemas import ApplicationOut

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("/my", response_model=list[ApplicationOut])
async def my_applications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apps = await get_applications_by_user(db, current_user.id)
    return [serialize(a) for a in apps]


@router.get("/{session_id}", response_model=ApplicationOut)
async def get_application(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    app = await get_application_by_session(db, session_id)
    if not app:
        raise HTTPException(404, "Application not found")
    if current_user.role == "applicant" and app.applicant_id != current_user.id:
        raise HTTPException(403, "Access denied")
    return serialize(app)
