# Loan Wizard Fix Plan Progress

Approved plan for remaining fixes.

## Steps
- [x] 1. **auth.py**: datetime.utcnow() → _now() ✓
- [x] 2. **database.py**: Add Application.version = Column(Integer, default=0) ✓
- [x] 3. **Alembic**: Failed (sqlite driver); dev skip ✓
- [x] 4. **kyc.py**: Add POST /kyc/simulate ✓
- [x] 5. **api.js**: simulateDecision → /kyc/simulate ✓
- [x] 6. **validators.py**: FAANG cleaned ✓
- [ ] 7. **Test**: pytest --cov=75; npm test; curl /health /kyc/simulate
- [ ] 8. **Done**: attempt_completion

Updated after each step.

