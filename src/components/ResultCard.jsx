export default function ResultCard({ decision, extracted, sessionId }) {
  if (!decision) return null;

  const statusClass =
    decision.status === "Approved" ? "status-approved" :
    decision.status === "Manual Review" ? "status-review" : "status-rejected";

  const badgeClass =
    decision.status === "Approved" ? "badge-green" :
    decision.status === "Manual Review" ? "badge-yellow" : "badge-red";

  return (
    <div className="glass" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <p style={{ fontSize: 11, color: "#64748b", fontWeight: 600, letterSpacing: "0.05em" }}>DECISION</p>
        {sessionId && (
          <span style={{ fontSize: 11, color: "#475569", fontFamily: "monospace" }}>{sessionId}</span>
        )}
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        <p className={statusClass} style={{ fontSize: 30, fontWeight: 800 }}>{decision.status}</p>
        {decision.credit_score_band && (
          <div style={{ textAlign: "center" }}>
            <p style={{ fontSize: 11, color: "#64748b" }}>Credit Band</p>
            <p style={{ fontSize: 22, fontWeight: 800, color: "#38bdf8" }}>{decision.credit_score_band}</p>
          </div>
        )}
      </div>

      {/* Primary failure reason (first failed check) */}
      {(decision.reasons_fail?.[0] || decision.reason) && (
        <p style={{ fontSize: 13, color: "#64748b" }}>
          {decision.reasons_fail?.[0] || decision.reason}
        </p>
      )}

      {decision.emi && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
          {[
            { label: "Monthly EMI",  value: `₹${decision.emi.toLocaleString()}`,         color: "#22c55e" },
            { label: "Loan Amount",  value: `₹${(decision.loan_amount||0).toLocaleString()}`, color: "#38bdf8" },
            { label: "Tenure",       value: decision.tenure,                              color: "#e2e8f0" },
          ].map((item) => (
            <div key={item.label} className="glass-light">
              <p style={{ fontSize: 11, color: "#64748b", marginBottom: 4 }}>{item.label}</p>
              <p style={{ fontSize: 16, fontWeight: 700, color: item.color }}>{item.value}</p>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        <span className={`badge ${extracted?.consent ? "badge-green" : "badge-red"}`}>
          {extracted?.consent ? "✓ Consent" : "✗ No Consent"}
        </span>
        <span className={`badge ${decision.status !== "Rejected" ? "badge-green" : "badge-red"}`}>
          {decision.status !== "Rejected" ? "✓ Face Verified" : "✗ Face Failed"}
        </span>
        <span className={`badge ${extracted?.risk_level === "low" ? "badge-green" : extracted?.risk_level === "medium" ? "badge-yellow" : "badge-red"}`}>
          Risk: {extracted?.risk_level ?? "—"}
        </span>
      </div>
    </div>
  );
}
