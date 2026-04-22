"""
KYC Service — orchestrates the AI pipeline and persists the result.

Fully async: no asyncio.run(), no threadpool workarounds.
The route is async, this service is async, the repo is async — consistent throughout.
"""
import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.services.agents.orchestrator import run_agents
from app.repositories.application_repo import save_application

logger = logging.getLogger("kyc_service")

MAX_SESSION_ID_RETRIES = 3


def _generate_session_id() -> str:
    return f"LW-{uuid.uuid4().hex[:10].upper()}"


async def process_kyc_session(
    db: AsyncSession,
    *,
    audio_bytes: bytes,
    video_frame: bytes | None = None,
    loan_product: str,
    applicant_id: int,
    applicant_name: str,
) -> dict:
    """
    Run the full KYC pipeline and persist the result.
    Returns the complete result dict including session_id.
    """
    # AI pipeline — fully async, parallel where possible
    result = await run_agents(audio_bytes, video_frame=video_frame, loan_product=loan_product)

    # Persist with session_id collision retry
    session_id = None
    for attempt in range(MAX_SESSION_ID_RETRIES):
        session_id = _generate_session_id()
        try:
            await save_application(
                db,
                session_id     = session_id,
                applicant_id   = applicant_id,
                applicant_name = applicant_name,
                loan_product   = loan_product,
                result         = result,
            )
            break
        except IntegrityError:
            await db.rollback()
            logger.warning(f"Session ID collision attempt={attempt + 1} id={session_id}")
            if attempt == MAX_SESSION_ID_RETRIES - 1:
                raise RuntimeError("Failed to generate unique session ID after retries")

    logger.info(
        f"KYC complete session={session_id} "
        f"status={result['decision']['status']} "
        f"user_id={applicant_id} "
        f"total_ms={result.get('timing_ms', {}).get('total', 0)}"
    )

    return {**result, "session_id": session_id}
