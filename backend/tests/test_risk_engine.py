"""
Unit tests — Risk Engine

These are the most critical tests in the system.
The risk engine is the only component that makes binding financial decisions,
so every rule must be tested in isolation.

Run: pytest tests/test_risk_engine.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.agents.risk_agent import process_risk

# ── Helpers ───────────────────────────────────────────────────────────────────

def _base(overrides=None):
    """Valid applicant — should approve for personal loan."""
    data = {
        "income":        50000,
        "consent":       True,
        "risk_level":    "low",
        "liveness_score": 0.90,
        "spoof_detected": False,
        "multiple_faces": False,
        "screen_spoof":   False,
        "face_detected":  True,
    }
    if overrides:
        data.update(overrides)
    return data


# ── Hard stop tests ───────────────────────────────────────────────────────────

def test_spoof_detected_always_rejects():
    result = process_risk(_base({"spoof_detected": True}))
    assert result["status"] == "Rejected"
    assert any("spoof" in r.lower() for r in result["reasons_fail"])


def test_screen_spoof_always_rejects():
    result = process_risk(_base({"screen_spoof": True}))
    assert result["status"] == "Rejected"
    assert any("replay" in r.lower() or "screen" in r.lower() for r in result["reasons_fail"])


def test_multiple_faces_always_rejects():
    result = process_risk(_base({"multiple_faces": True}))
    assert result["status"] == "Rejected"
    assert any("multiple" in r.lower() for r in result["reasons_fail"])


def test_no_consent_rejects():
    result = process_risk(_base({"consent": False}))
    assert result["status"] == "Rejected"
    assert any("consent" in r.lower() for r in result["reasons_fail"])


def test_low_liveness_rejects():
    result = process_risk(_base({"liveness_score": 0.30}))
    assert result["status"] == "Rejected"
    assert any("liveness" in r.lower() for r in result["reasons_fail"])


def test_liveness_exactly_at_threshold_rejects():
    # 0.50 is the boundary — below should reject
    result = process_risk(_base({"liveness_score": 0.49}))
    assert result["status"] == "Rejected"


def test_liveness_at_threshold_passes():
    result = process_risk(_base({"liveness_score": 0.50}))
    assert result["status"] == "Approved"


# ── Behavioral risk tests ─────────────────────────────────────────────────────

def test_high_risk_sends_to_manual_review():
    result = process_risk(_base({"risk_level": "high"}))
    assert result["status"] == "Manual Review"
    assert any("behavioral" in r.lower() for r in result["reasons_fail"])


def test_medium_risk_approves_with_reduced_emi():
    low_result    = process_risk(_base({"risk_level": "low"}))
    medium_result = process_risk(_base({"risk_level": "medium"}))
    assert medium_result["status"] == "Approved"
    assert medium_result["emi"] < low_result["emi"]  # conservative EMI


# ── Income threshold tests ────────────────────────────────────────────────────

def test_income_below_personal_minimum_rejects():
    result = process_risk(_base({"income": 10000}), loan_product="personal")
    assert result["status"] == "Rejected"
    assert any("income" in r.lower() for r in result["reasons_fail"])


def test_income_at_personal_minimum_approves():
    result = process_risk(_base({"income": 25000}), loan_product="personal")
    assert result["status"] == "Approved"


def test_home_loan_requires_higher_income():
    result = process_risk(_base({"income": 40000}), loan_product="home")
    assert result["status"] == "Rejected"


def test_home_loan_approves_at_threshold():
    result = process_risk(_base({"income": 60000}), loan_product="home")
    assert result["status"] == "Approved"


# ── Output shape tests ────────────────────────────────────────────────────────

def test_approved_result_has_required_fields():
    result = process_risk(_base())
    assert result["status"] == "Approved"
    assert result["emi"] is not None and result["emi"] > 0
    assert result["tenure"] is not None
    assert result["loan_amount"] is not None
    assert result["credit_score_band"] in ("A", "B", "C", "D")
    assert 0.0 <= result["confidence"] <= 1.0
    assert isinstance(result["reasons_pass"], list)
    assert isinstance(result["reasons_fail"], list)
    assert len(result["reasons_pass"]) > 0
    assert result["model_version"] != ""


def test_rejected_result_has_no_emi():
    result = process_risk(_base({"consent": False}))
    assert result["emi"] is None
    assert result["loan_amount"] is None


def test_confidence_higher_for_better_applicant():
    strong = process_risk(_base({"income": 150000, "liveness_score": 0.97, "risk_level": "low"}))
    weak   = process_risk(_base({"income": 26000,  "liveness_score": 0.55, "risk_level": "medium"}))
    assert strong["confidence"] > weak["confidence"]


# ── Credit band tests ─────────────────────────────────────────────────────────

def test_high_income_low_risk_gets_band_a():
    result = process_risk(_base({"income": 200000, "liveness_score": 0.97, "risk_level": "low"}))
    assert result["credit_score_band"] == "A"


def test_low_income_medium_risk_gets_lower_band():
    result = process_risk(_base({"income": 26000, "liveness_score": 0.55, "risk_level": "medium"}))
    assert result["credit_score_band"] in ("C", "D")


# ── Validator integration ─────────────────────────────────────────────────────

def test_invalid_income_type_is_sanitized():
    """Validators should coerce bad AI output before it reaches the engine."""
    from app.services.validators import validate_extracted
    raw = {"income": "fifty thousand", "consent": True, "risk_level": "low",
           "liveness_score": 0.9, "spoof_detected": False,
           "multiple_faces": False, "screen_spoof": False, "face_detected": True}
    clean = validate_extracted(raw)
    assert clean["income"] == 0   # unparseable string → 0


def test_out_of_range_income_is_clamped():
    from app.services.validators import validate_extracted
    raw = {"income": 999_999_999, "consent": True, "risk_level": "low",
           "liveness_score": 0.9, "spoof_detected": False,
           "multiple_faces": False, "screen_spoof": False, "face_detected": True}
    clean = validate_extracted(raw)
    assert clean["income"] == 10_000_000   # clamped to max


def test_invalid_risk_level_defaults_to_medium():
    from app.services.validators import validate_extracted
    raw = {"income": 50000, "consent": True, "risk_level": "extreme",
           "liveness_score": 0.9, "spoof_detected": False,
           "multiple_faces": False, "screen_spoof": False, "face_detected": True}
    clean = validate_extracted(raw)
    assert clean["risk_level"] == "medium"
