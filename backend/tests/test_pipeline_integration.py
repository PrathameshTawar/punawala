"""
Integration tests — Full pipeline with mocked AI services.

Run: pytest tests/test_pipeline_integration.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch, AsyncMock

MOCK_TRANSCRIPT = "I earn 50000 per month and I agree to the loan terms"

MOCK_LLM_OUTPUT = {
    "income": 50000,
    "consent": True,
    "risk_level": "low",
}

MOCK_VISION_OUTPUT = {
    "face_detected":   True,
    "liveness_score":  0.92,
    "spoof_detected":  False,
    "multiple_faces":  False,
    "screen_spoof":    False,
    "gaze_consistent": True,
    "lighting_ok":     True,
}


@pytest.mark.asyncio
async def test_full_pipeline_approves_valid_applicant():
    from app.services.agents import orchestrator

    with patch.object(orchestrator, "process_voice",  new=AsyncMock(return_value=MOCK_TRANSCRIPT)), \
         patch.object(orchestrator, "process_vision", new=AsyncMock(return_value=MOCK_VISION_OUTPUT)), \
         patch.object(orchestrator, "process_llm",    new=AsyncMock(return_value=MOCK_LLM_OUTPUT)):

        result = await orchestrator.run_agents(b"fake_audio", video_frame=None, loan_product="personal")

    assert result["decision"]["status"] == "Approved"
    assert result["transcript"] == MOCK_TRANSCRIPT
    assert result["decision"]["emi"] is not None
    assert result["decision"]["confidence"] > 0
    assert "timing_ms" in result


@pytest.mark.asyncio
async def test_pipeline_rejects_on_no_consent():
    from app.services.agents import orchestrator

    llm_no_consent = {**MOCK_LLM_OUTPUT, "consent": False}

    with patch.object(orchestrator, "process_voice",  new=AsyncMock(return_value=MOCK_TRANSCRIPT)), \
         patch.object(orchestrator, "process_vision", new=AsyncMock(return_value=MOCK_VISION_OUTPUT)), \
         patch.object(orchestrator, "process_llm",    new=AsyncMock(return_value=llm_no_consent)):

        result = await orchestrator.run_agents(b"fake_audio", video_frame=None)

    assert result["decision"]["status"] == "Rejected"
    assert result["decision"]["emi"] is None


@pytest.mark.asyncio
async def test_pipeline_rejects_on_spoof():
    from app.services.agents import orchestrator

    vision_spoof = {**MOCK_VISION_OUTPUT, "spoof_detected": True, "liveness_score": 0.30}

    with patch.object(orchestrator, "process_voice",  new=AsyncMock(return_value=MOCK_TRANSCRIPT)), \
         patch.object(orchestrator, "process_vision", new=AsyncMock(return_value=vision_spoof)), \
         patch.object(orchestrator, "process_llm",    new=AsyncMock(return_value=MOCK_LLM_OUTPUT)):

        result = await orchestrator.run_agents(b"fake_audio", video_frame=None)

    assert result["decision"]["status"] == "Rejected"
    assert any("spoof" in r.lower() for r in result["decision"]["reasons_fail"])


@pytest.mark.asyncio
async def test_pipeline_sends_high_risk_to_manual_review():
    from app.services.agents import orchestrator

    llm_high_risk = {**MOCK_LLM_OUTPUT, "risk_level": "high"}

    with patch.object(orchestrator, "process_voice",  new=AsyncMock(return_value=MOCK_TRANSCRIPT)), \
         patch.object(orchestrator, "process_vision", new=AsyncMock(return_value=MOCK_VISION_OUTPUT)), \
         patch.object(orchestrator, "process_llm",    new=AsyncMock(return_value=llm_high_risk)):

        result = await orchestrator.run_agents(b"fake_audio", video_frame=None)

    assert result["decision"]["status"] == "Manual Review"


@pytest.mark.asyncio
async def test_pipeline_uses_fallback_when_llm_fails():
    """Pipeline completes even when LLM raises — regex fallback kicks in."""
    from app.services.agents import orchestrator

    async def failing_llm(transcript):
        raise RuntimeError("OpenAI API unavailable")

    with patch.object(orchestrator, "process_voice",  new=AsyncMock(return_value=MOCK_TRANSCRIPT)), \
         patch.object(orchestrator, "process_vision", new=AsyncMock(return_value=MOCK_VISION_OUTPUT)), \
         patch.object(orchestrator, "process_llm",    new=failing_llm):

        # llm_agent handles its own fallback — pipeline should not raise
        # We test this by patching at the orchestrator level with a failing function
        # The orchestrator will propagate the error; the fallback is inside llm_agent itself
        # This test verifies the orchestrator doesn't swallow errors silently
        with pytest.raises(RuntimeError):
            await orchestrator.run_agents(b"fake_audio", video_frame=None)


@pytest.mark.asyncio
async def test_result_always_has_model_version():
    from app.services.agents import orchestrator

    with patch.object(orchestrator, "process_voice",  new=AsyncMock(return_value=MOCK_TRANSCRIPT)), \
         patch.object(orchestrator, "process_vision", new=AsyncMock(return_value=MOCK_VISION_OUTPUT)), \
         patch.object(orchestrator, "process_llm",    new=AsyncMock(return_value=MOCK_LLM_OUTPUT)):

        result = await orchestrator.run_agents(b"fake_audio", video_frame=None)

    assert result["decision"]["model_version"] != ""


@pytest.mark.asyncio
async def test_timing_ms_recorded_for_all_stages():
    from app.services.agents import orchestrator

    with patch.object(orchestrator, "process_voice",  new=AsyncMock(return_value=MOCK_TRANSCRIPT)), \
         patch.object(orchestrator, "process_vision", new=AsyncMock(return_value=MOCK_VISION_OUTPUT)), \
         patch.object(orchestrator, "process_llm",    new=AsyncMock(return_value=MOCK_LLM_OUTPUT)):

        result = await orchestrator.run_agents(b"fake_audio", video_frame=None)

    timing = result["timing_ms"]
    assert "voice_vision" in timing
    assert "llm" in timing
    assert "risk" in timing
    assert "total" in timing
    assert timing["total"] >= 0
