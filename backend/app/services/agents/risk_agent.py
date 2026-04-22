"""
Deterministic Risk Engine

Rules:
- LLM output is NEVER trusted directly — all values are validated before entering this engine
- Every decision includes a full reasons[] trace (explainability)
- Confidence score is computed from signal quality, not AI output
- Model version is stamped on every response for audit reproducibility
"""

from app.services.validators import validate_extracted

MODEL_VERSION = "risk-engine-v2.1"

LOAN_PRODUCTS = {
    "personal": {"min_income": 25000, "emi_ratio": 0.30, "tenure": "24 months",  "multiplier": 12},
    "home":     {"min_income": 60000, "emi_ratio": 0.40, "tenure": "240 months", "multiplier": 60},
    "business": {"min_income": 50000, "emi_ratio": 0.35, "tenure": "60 months",  "multiplier": 24},
    "vehicle":  {"min_income": 30000, "emi_ratio": 0.25, "tenure": "60 months",  "multiplier": 18},
}


def process_risk(raw_data: dict, loan_product: str = "personal") -> dict:
    # Step 1: Validate + sanitize all AI outputs before any logic
    data = validate_extracted(raw_data)

    income        = data["income"]
    consent       = data["consent"]
    risk_level    = data["risk_level"]
    liveness      = data["liveness_score"]
    spoof         = data["spoof_detected"]
    multi_face    = data["multiple_faces"]
    screen_spoof  = data["screen_spoof"]

    reasons_pass = []   # checks that passed
    reasons_fail = []   # checks that failed

    # ── Hard stops (fraud / compliance) ──────────────────────────────────────
    if spoof:
        reasons_fail.append("Identity spoof detected by vision agent")
        return _build("Rejected", reasons_pass, reasons_fail, 0.0, None, None, None, None)

    if screen_spoof:
        reasons_fail.append("Screen replay attack detected")
        return _build("Rejected", reasons_pass, reasons_fail, 0.0, None, None, None, None)

    if multi_face:
        reasons_fail.append("Multiple faces detected — assisted fraud risk")
        return _build("Rejected", reasons_pass, reasons_fail, 0.0, None, None, None, None)

    if not consent:
        reasons_fail.append("Verbal consent not recorded")
        return _build("Rejected", reasons_pass, reasons_fail, 0.05, None, None, None, None)

    reasons_pass.append("Verbal consent confirmed")

    # ── Liveness ─────────────────────────────────────────────────────────────
    if liveness < 0.50:
        reasons_fail.append(f"Liveness score {liveness:.2f} below threshold 0.50")
        return _build("Rejected", reasons_pass, reasons_fail, liveness * 0.3, None, None, None, None)

    reasons_pass.append(f"Liveness verified ({liveness:.2f})")

    # ── Behavioral risk ───────────────────────────────────────────────────────
    if risk_level == "high":
        reasons_fail.append("High behavioral risk — hesitation or inconsistency detected")
        return _build("Manual Review", reasons_pass, reasons_fail, 0.35, None, None, None, None)

    if risk_level == "medium":
        reasons_pass.append("Moderate behavioral confidence — conservative terms applied")
    else:
        reasons_pass.append("Low behavioral risk — clear and confident speech")

    # ── Product eligibility ───────────────────────────────────────────────────
    product = LOAN_PRODUCTS.get(loan_product, LOAN_PRODUCTS["personal"])

    if income < product["min_income"]:
        reasons_fail.append(
            f"Income ₹{income:,} below minimum ₹{product['min_income']:,} for {loan_product} loan"
        )
        return _build("Rejected", reasons_pass, reasons_fail, 0.2, None, None, None, None)

    reasons_pass.append(f"Income ₹{income:,} meets {loan_product} loan threshold")

    # ── Compute outputs ───────────────────────────────────────────────────────
    emi_ratio = product["emi_ratio"]
    if risk_level == "medium":
        emi_ratio *= 0.85
        reasons_pass.append("EMI ratio reduced 15% for medium-risk applicant")

    emi         = int(income * emi_ratio)
    loan_amount = income * product["multiplier"]
    band        = _credit_band(income, risk_level, liveness)
    confidence  = _confidence(income, risk_level, liveness, product["min_income"])

    reasons_pass.append(f"Credit band assigned: {band}")
    reasons_pass.append(f"Decision confidence: {confidence:.0%}")

    return _build("Approved", reasons_pass, reasons_fail, confidence, emi, product["tenure"], loan_amount, band)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build(status, reasons_pass, reasons_fail, confidence, emi, tenure, loan_amount, band) -> dict:
    return {
        "status":            status,
        "reasons_pass":      reasons_pass,
        "reasons_fail":      reasons_fail,
        "confidence":        round(confidence, 3),
        "emi":               emi,
        "tenure":            tenure,
        "loan_amount":       loan_amount,
        "credit_score_band": band,
        "model_version":     MODEL_VERSION,
    }


def _confidence(income: int, risk_level: str, liveness: float, min_income: int) -> float:
    score = 0.0
    # Income headroom above minimum
    headroom = min((income - min_income) / min_income, 1.0)
    score += headroom * 0.35

    # Behavioral signal
    score += {"low": 0.35, "medium": 0.20, "high": 0.0}.get(risk_level, 0.0)

    # Liveness quality
    score += min(liveness, 1.0) * 0.30

    return min(score, 0.99)


def _credit_band(income: int, risk_level: str, liveness: float) -> str:
    score = 0
    if income >= 100000: score += 40
    elif income >= 60000: score += 30
    elif income >= 30000: score += 20
    else: score += 5
    score += {"low": 40, "medium": 20, "high": 0}.get(risk_level, 0)
    score += int(liveness * 20)
    if score >= 80: return "A"
    if score >= 60: return "B"
    if score >= 40: return "C"
    return "D"
