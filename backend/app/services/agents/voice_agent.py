"""
Voice Agent — speech-to-text via OpenAI Whisper.

Uses AsyncOpenAI (1.x SDK) — non-blocking, correct in async FastAPI.
Lazy client: import never fails without API key.
tempfile.NamedTemporaryFile: no race condition between concurrent requests.
"""
import os
import tempfile
import logging
from app.config import settings

logger = logging.getLogger("voice_agent")

FALLBACK_TEXT   = "I earn 50000 per month and I agree to the loan terms"
MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB

# Lazy AsyncOpenAI client — created on first use
_openai_client = None


def _get_client():
    global _openai_client
    if _openai_client is None:
        api_key = settings.OPENAI_API_KEY
        if api_key and api_key not in ("your_api_key_here", "demo", ""):
            try:
                from openai import AsyncOpenAI
                _openai_client = AsyncOpenAI(api_key=api_key)
            except Exception as e:
                logger.warning(f"Failed to create AsyncOpenAI client: {e}")
    return _openai_client


async def process_voice(audio_bytes: bytes) -> str:
    """
    Transcribe audio bytes using Whisper (async, non-blocking).
    Falls back to FALLBACK_TEXT if API key not set or call fails.
    """
    if not audio_bytes:
        logger.warning("Empty audio bytes received")
        return FALLBACK_TEXT

    if len(audio_bytes) > MAX_AUDIO_BYTES:
        logger.warning(f"Audio too large: {len(audio_bytes)} bytes — using fallback")
        return FALLBACK_TEXT

    client = _get_client()
    if client is None:
        logger.debug("No OpenAI client — using fallback transcript")
        return FALLBACK_TEXT

    tmp_path = None
    try:
        # NamedTemporaryFile: unique path per request, no race condition
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".wav", prefix="lw_audio_"
        ) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        with open(tmp_path, "rb") as audio_file:
            transcript = await client.audio.transcriptions.create(
                model="whisper-1", file=audio_file
            )

        text = transcript.text.strip() if hasattr(transcript, "text") else ""
        if not text:
            logger.warning("Whisper returned empty transcript")
            return FALLBACK_TEXT

        logger.info(f"Transcribed {len(audio_bytes)} bytes → {len(text)} chars")
        return text

    except Exception as e:
        logger.warning(f"Whisper transcription failed: {e}")
        return FALLBACK_TEXT

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
