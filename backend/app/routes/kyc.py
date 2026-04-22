"""KYC routes — thin async layer."""
import logging
from fastapi import APIRouter, UploadFile, File, Depends, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db, User
from app.auth import get_current_user
from app.services.kyc_service import process_kyc_session
from app.repositories.application_repo import get_application_by_session, serialize
from app.schemas import KYCResult, ApplicationOut
from app.services.agents.risk_agent import process_risk
from app.services.validators import validate_extracted

logger = logging.getLogger("kyc_route")
router = APIRouter(prefix="/kyc", tags=["kyc"])

VALID_PRODUCTS  = {"personal", "home", "business", "vehicle"}
MAX_AUDIO_BYTES = 10 * 1024 * 1024
MAX_FRAME_BYTES = 5  * 1024 * 1024
ALLOWED_MIMES   = {
    "audio/wav", "audio/wave", "audio/webm", "audio/ogg",
    "audio/mpeg", "audio/mp4", "application/octet-stream",
}


@router.post("/sessions", status_code=201, response_model=KYCResult)
async def create_kyc_session(
    file:        UploadFile = File(...),
    video_frame: UploadFile = File(None),
    loan_product: str = Form("personal"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit audio for KYC processing. Returns 201 with full pipeline result."""
    if file.content_type and file.content_type not in ALLOWED_MIMES:
        raise HTTPException(415, f"Unsupported media type: {file.content_type}")
    if loan_product not in VALID_PRODUCTS:
        raise HTTPException(400, f"loan_product must be one of: {sorted(VALID_PRODUCTS)}")

    audio_bytes = await file.read()
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise HTTPException(413, "Audio file exceeds 10MB limit")
    if not audio_bytes:
        raise HTTPException(400, "Audio file is empty")

    video_frame_bytes = None
    if video_frame is not None and hasattr(video_frame, "read"):
        video_frame_bytes = await video_frame.read()
        if len(video_frame_bytes) > MAX_FRAME_BYTES:
            raise HTTPException(413, "Video frame exceeds 5MB limit")

    return await process_kyc_session(
        db,
        audio_bytes    = audio_bytes,
        video_frame    = video_frame_bytes,
        loan_product   = loan_product,
        applicant_id   = current_user.id,
        applicant_name = current_user.full_name,
    )


@router.post("/process", response_model=KYCResult)
async def process_kyc_compat(
    file: UploadFile = File(...),
    loan_product: str = Form("personal"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Backward-compatible alias for /sessions."""
    return await create_kyc_session(
        file=file, loan_product=loan_product, db=db, current_user=current_user
    )


@router.get("/{session_id}/explain", response_model=ApplicationOut)
async def explain(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    app = await get_application_by_session(db, session_id)
    if not app:
        raise HTTPException(404, "Session not found")
    if current_user.role == "applicant" and app.applicant_id != current_user.id:
        raise HTTPException(403, "Access denied")
    return serialize(app)


@router.post("/simulate")
async def simulate_kyc(
    income: int = Form(..., ge=0),
    risk_level: str = Form(..., pattern="^(low|medium|high)$"),
    liveness_score: float = Form(..., ge=0, le=1),
    loan_product: str = Form("personal"),
):
    '''Client-side simulation using backend risk engine (no AI, no DB).'''
    data = {
        "income": income,
        "consent": True,  # assume for sim
        "risk_level": risk_level,
        "liveness_score": liveness_score,
        "spoof_detected": False,
        "multiple_faces": False,
        "screen_spoof": False,
    }
    data = validate_extracted(data)
    result = process_risk(data, loan_product)
    return result
