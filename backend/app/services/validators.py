'''
AI Output Guardrails.

Validate and sanitize all AI agent outputs before business logic.
'''

def validate_extracted(raw: dict) -> dict:
    '''
    Sanitize and type-enforce all AI outputs.
    Returns a clean, bounded dict safe for the rule engine.
    '''
    income = raw.get('income', 0)
    if not isinstance(income, (int, float)):
        income = 0
    income = max(0, min(int(income), 10_000_000))  # clamp 0–1Cr

    consent = raw.get('consent', False)
    if not isinstance(consent, bool):
        consent = str(consent).lower() in ('true', '1', 'yes')

    risk_level = raw.get('risk_level', 'medium')
    if risk_level not in ('low', 'medium', 'high'):
        risk_level = 'medium'

    liveness = raw.get('liveness_score', 0.0)
    if not isinstance(liveness, (int, float)):
        liveness = 0.0
    liveness = max(0.0, min(float(liveness), 1.0))

    spoof = bool(raw.get('spoof_detected', False))
    multi_face = bool(raw.get('multiple_faces', False))
    screen_spoof = bool(raw.get('screen_spoof', False))
    face_detected = bool(raw.get('face_detected', True))

    return {
        'income':        income,
        'consent':       consent,
        'risk_level':    risk_level,
        'liveness_score': liveness,
        'spoof_detected': spoof,
        'multiple_faces': multi_face,
        'screen_spoof':   screen_spoof,
        'face_detected':  face_detected,
    }
