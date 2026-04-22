"""
Agent Orchestrator — parallel execution with structured tracing.

Pipeline:
  [Voice Agent] ──┐
                  ├─→ [LLM Agent] ──→ [Risk Engine] ──→ Decision
  [Vision Agent] ─┘

Each stage is timed and logged for observability.
"""
import asyncio
import logging
import time

from app.services.agents.voice_agent  import process_voice
from app.services.agents.vision_agent import process_vision
from app.services.agents.llm_agent    import process_llm
from app.services.agents.risk_agent   import process_risk

logger = logging.getLogger("orchestrator")


async def run_agents(audio_bytes: bytes, video_frame, loan_product: str = "personal") -> dict:
    session_start = time.monotonic()

    # Stage 1: Voice + Vision in parallel
    t0 = time.monotonic()
    transcript, vision_result = await asyncio.gather(
        process_voice(audio_bytes),
        process_vision(video_frame),
    )
    stage1_ms = int((time.monotonic() - t0) * 1000)

    # Stage 2: LLM extraction (needs transcript)
    t1 = time.monotonic()
    llm_result = await process_llm(transcript)
    stage2_ms = int((time.monotonic() - t1) * 1000)

    # Stage 3: Deterministic risk engine
    t2 = time.monotonic()
    merged   = {**llm_result, **vision_result}
    decision = process_risk(merged, loan_product=loan_product)
    stage3_ms = int((time.monotonic() - t2) * 1000)

    total_ms = int((time.monotonic() - session_start) * 1000)

    logger.info(
        "Pipeline complete",
        extra={
            "loan_product": loan_product,
            "status":       decision["status"],
            "confidence":   decision.get("confidence"),
            "stage1_ms":    stage1_ms,
            "stage2_ms":    stage2_ms,
            "stage3_ms":    stage3_ms,
            "total_ms":     total_ms,
        },
    )

    return {
        "transcript":  transcript,
        "extracted":   llm_result,
        "vision":      vision_result,
        "decision":    decision,
        "timing_ms":   {"voice_vision": stage1_ms, "llm": stage2_ms, "risk": stage3_ms, "total": total_ms},
    }
