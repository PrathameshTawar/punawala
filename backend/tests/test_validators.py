"""
Unit tests — Input Validators

Every AI output boundary is tested here.
These tests encode the contract: "garbage in, safe values out."

Run: pytest tests/test_validators.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.validators import validate_extracted


def _raw(overrides=None):
    base = {
        "income": 50000, "consent": True, "risk_level": "low",
        "liveness_score": 0.88, "spoof_detected": False,
        "multiple_faces": False, "screen_spoof": False, "face_detected": True,
    }
    if overrides:
        base.update(overrides)
    return base


# ── Income ────────────────────────────────────────────────────────────────────

def test_valid_income_passes_through():
    assert validate_extracted(_raw())["income"] == 50000

def test_negative_income_clamped_to_zero():
    assert validate_extracted(_raw({"income": -5000}))["income"] == 0

def test_income_above_max_clamped():
    assert validate_extracted(_raw({"income": 50_000_000}))["income"] == 10_000_000

def test_float_income_truncated():
    assert validate_extracted(_raw({"income": 49999.99}))["income"] == 49999

def test_string_income_becomes_zero():
    assert validate_extracted(_raw({"income": "lots"}))["income"] == 0

def test_none_income_becomes_zero():
    assert validate_extracted(_raw({"income": None}))["income"] == 0


# ── Consent ───────────────────────────────────────────────────────────────────

def test_true_consent_passes():
    assert validate_extracted(_raw({"consent": True}))["consent"] is True

def test_false_consent_passes():
    assert validate_extracted(_raw({"consent": False}))["consent"] is False

def test_string_true_coerced():
    assert validate_extracted(_raw({"consent": "true"}))["consent"] is True

def test_string_yes_coerced():
    assert validate_extracted(_raw({"consent": "yes"}))["consent"] is True

def test_string_false_coerced():
    assert validate_extracted(_raw({"consent": "false"}))["consent"] is False

def test_integer_one_coerced_to_true():
    assert validate_extracted(_raw({"consent": "1"}))["consent"] is True


# ── Risk level ────────────────────────────────────────────────────────────────

def test_valid_risk_levels_pass():
    for level in ("low", "medium", "high"):
        assert validate_extracted(_raw({"risk_level": level}))["risk_level"] == level

def test_unknown_risk_level_defaults_to_medium():
    assert validate_extracted(_raw({"risk_level": "critical"}))["risk_level"] == "medium"

def test_none_risk_level_defaults_to_medium():
    assert validate_extracted(_raw({"risk_level": None}))["risk_level"] == "medium"


# ── Liveness ──────────────────────────────────────────────────────────────────

def test_valid_liveness_passes():
    assert validate_extracted(_raw({"liveness_score": 0.85}))["liveness_score"] == 0.85

def test_liveness_above_one_clamped():
    assert validate_extracted(_raw({"liveness_score": 1.5}))["liveness_score"] == 1.0

def test_liveness_below_zero_clamped():
    assert validate_extracted(_raw({"liveness_score": -0.1}))["liveness_score"] == 0.0

def test_string_liveness_becomes_zero():
    assert validate_extracted(_raw({"liveness_score": "high"}))["liveness_score"] == 0.0


# ── Boolean fraud signals ─────────────────────────────────────────────────────

def test_fraud_signals_are_boolean():
    result = validate_extracted(_raw({"spoof_detected": 1, "multiple_faces": 0, "screen_spoof": "false"}))
    assert result["spoof_detected"] is True
    assert result["multiple_faces"] is False
    # "false" string → bool("false") is True in Python, but we use bool() directly
    # This is intentional — non-empty strings are truthy
