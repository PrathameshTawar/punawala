export default function RiskMeter({ riskLevel, livenessScore, income }) {
  const riskMap = { low: 18, medium: 52, high: 88 };
  const riskWidth = riskMap[riskLevel] ?? 0;
  const riskColor = riskLevel === "low" ? "#22c55e" : riskLevel === "medium" ? "#f59e0b" : "#ef4444";
  const livenessWidth = livenessScore ? Math.round(livenessScore * 100) : 0;
  const livenessColor = livenessWidth >= 80 ? "#22c55e" : livenessWidth >= 60 ? "#f59e0b" : "#ef4444";

  const incomeWidth = income ? Math.min(Math.round((income / 150000) * 100), 100) : 0;

  const bars = [
    { label: "Behavioral Risk",  width: riskWidth,    color: riskColor,    value: riskLevel ?? "—",          suffix: "" },
    { label: "Liveness Score",   width: livenessWidth, color: livenessColor, value: livenessScore ?? "—",    suffix: "" },
    { label: "Income Signal",    width: incomeWidth,  color: "#a78bfa",    value: income ? `₹${income.toLocaleString()}` : "—", suffix: "" },
  ];

  return (
    <div className="glass" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <p style={{ fontSize: 11, color: "#64748b", fontWeight: 600, letterSpacing: "0.05em" }}>SIGNAL ANALYSIS</p>
      {bars.map((b) => (
        <div key={b.label}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
            <span style={{ fontSize: 13 }}>{b.label}</span>
            <span style={{ fontSize: 13, color: b.color, textTransform: "capitalize" }}>{b.value}{b.suffix}</span>
          </div>
          <div className="risk-bar-track">
            <div className="risk-bar-fill" style={{ width: `${b.width}%`, background: b.color }} />
          </div>
        </div>
      ))}
    </div>
  );
}
