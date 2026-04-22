"""
LLM Agent — extraction only, never decision-making.

Uses AsyncOpenAI (1.x SDK) — non-blocking, correct in async FastAPI.
Lazy client: import never fails without API key.
Resilience: retry once with 500ms backoff, then regex fallback (always succeeds).
Output is ALWAYS validated by validators.py before reaching the risk engine.
"""
import os
import json
import re
import asyncio
import logging
from app.config import settings

logger = logging.getLogger("llm_agent")

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


SYSTEM_PROMPT = """You are a financial data extraction AI. Extract ONLY facts from speech.

Extract:
- income: monthly income as integer (0 if not mentioned or unclear)
- consent: true ONLY if user explicitly agrees/says yes/okay/I agree/I consent
- risk_level: "low" if speech is clear and confident, "medium" if hesitant or vague, "high" if contradictory or suspicious

Return ONLY valid JSON. No explanation. No markdown.
{"income": number, "consent": boolean, "risk_level": "low"|"medium"|"high"}"""


def _regex_fallback(text: str) -> dict:
    """Always-succeeds fallback. Income-keyword-aware."""
    income     = 0
    text_lower = text.lower()

    # Priority 1: number after income keywords
    m = re.search(
        r'(?:earn|income|salary|make|get|receive|paid)[^\d\w]{0,20}(\d[\d,]*|fifty|sixty|seventy|eighty|ninety|hundred|thousand)\s*([kK])?',
        text_lower
    )
    if m:
        val = m.group(1).replace(",", "")
        if val.isdigit():
            income = int(val)
            if m.group(2):
                income *= 1000
        else:
            # simple natural language fallback
            income = 50000 
    else:
        # Priority 2: number with k suffix
        k = re.search(r'(\d+)\s*[kK]\b', text_lower)
        if k:
            income = int(k.group(1)) * 1000
        else:
            # Priority 3: largest standalone number
            nums = re.findall(r'\b(\d[\d,]{3,})\b', text_lower)
            if nums:
                income = max(int(n.replace(",", "")) for n in nums)

    consent    = any(w in text_lower for w in
                     ["agree", "yes", "okay", "ok", "consent", "accept", "sure", "i do"])
    risk_level = "low" if income > 0 and consent else "medium"
    logger.debug(f"Regex fallback: income={income} consent={consent}")
    return {"income": income, "consent": consent, "risk_level": risk_level}


def _safe_parse(raw: str) -> dict:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if not m:
            raise ValueError("No JSON found in LLM output")
        data = json.loads(m.group())
    if not all(k in data for k in ("income", "consent", "risk_level")):
        raise ValueError(f"Missing required fields: {data}")
    return data


async def process_llm(transcript: str) -> dict:
    """Extract structured data. Retries once with backoff, then regex fallback."""
    if not transcript or not transcript.strip():
        return _regex_fallback("")

    client = _get_client()
    if client is None:
        return _regex_fallback(transcript)

    for attempt in range(2):
        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": transcript[:1000]},
                ],
                temperature=0,
                max_tokens=80,
            )
            raw    = response.choices[0].message.content.strip()
            result = _safe_parse(raw)
            logger.info(f"LLM extraction success attempt={attempt + 1}")
            return result
        except Exception as e:
            logger.warning(f"LLM attempt {attempt + 1} failed: {e}")
            if attempt == 0:
                await asyncio.sleep(0.5)

    return _regex_fallback(transcript)
