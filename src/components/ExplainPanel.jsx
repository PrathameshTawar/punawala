/**
 * Decision Explainability Panel
 * Shows every rule evaluated — passed and failed — with confidence score.
 * This is what banks require for regulatory compliance.
 */
export default function ExplainPanel({ decision, sessionId }) {
  if (!decision) return null;

  const pass = decision.reasons_pass || [];
  const fail = decision.reasons_fail || [];
  const confidence = decision.confidence ?? null;
  const band = decision.credit_score_band;
  const model = decision.model_version;

  const bandColor = { A: "#22c55e", B: "#38bdf8", C: "#f59e0b", D: "#ef4444" }[band] || "#94a3b8";

  return (
    <div className="glass" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <p style={{ fontSize: 11, color: "#64748b", fontWeight: 600, letterSpacing: "0.05em" }}>
          DECISION REASONING
        </p>
        {model && (
          <span style={{ fontSize: 10, color: "#334155", fontFamily: "monospace" }}>{model}</span>
        )}
      </div>

      {/* Confidence + Band */}
      {confidence !== null && (
        <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
              <span style={{ fontSize: 12, color: "#94a3b8" }}>Decision Confidence</span>
              <span style={{ fontSize: 12, fontWeight: 700, color: confidence > 0.7 ? "#22c55e" : confidence > 0.4 ? "#f59e0b" : "#ef4444" }}>
                {(confidence * 100).toFixed(0)}%
              </span>
            </div>
            <div className="risk-bar-track">
              <div
                className="risk-bar-fill"
                style={{
                  width: `${confidence * 100}%`,
                  background: confidence > 0.7 ? "#22c55e" : confidence > 0.4 ? "#f59e0b" : "#ef4444",
                }}
              />
            </div>
          </div>
          {band && (
            <div style={{ textAlign: "center", minWidth: 48 }}>
              <p style={{ fontSize: 10, color: "#64748b" }}>BAND</p>
              <p style={{ fontSize: 26, fontWeight: 800, color: bandColor, lineHeight: 1 }}>{band}</p>
            </div>
          )}
        </div>
      )}

      {/* Passed checks */}
      {pass.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {pass.map((r, i) => (
            <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
              <span style={{ color: "#22c55e", fontSize: 13, marginTop: 1, flexShrink: 0 }}>✓</span>
              <span style={{ fontSize: 13, color: "#94a3b8", lineHeight: 1.5 }}>{r}</span>
            </div>
          ))}
        </div>
      )}

      {/* Failed checks */}
      {fail.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 6, borderTop: "1px solid rgba(239,68,68,0.15)", paddingTop: 10 }}>
          {fail.map((r, i) => (
            <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
              <span style={{ color: "#ef4444", fontSize: 13, marginTop: 1, flexShrink: 0 }}>✗</span>
              <span style={{ fontSize: 13, color: "#ef4444", lineHeight: 1.5 }}>{r}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
