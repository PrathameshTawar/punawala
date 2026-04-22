/**
 * Decision Simulation Mode
 * Lets the user drag sliders to see how income / risk / liveness
 * changes the decision in real time — no API call needed.
 * This is a FAANG-level explainability feature used in real fintech tools.
 */
import { useState } from "react";
import { simulateDecision } from "../services/api";

const PRODUCTS = ["personal", "home", "business", "vehicle"];

export default function SimulationPanel() {
  const [income,    setIncome]    = useState(50000);
  const [risk,      setRisk]      = useState("low");
  const [liveness,  setLiveness]  = useState(0.88);
  const [product,   setProduct]   = useState("personal");

  const result = simulateDecision(income, risk, liveness, product);

  const statusColor = result.status === "Approved" ? "#22c55e" : "#ef4444";

  return (
    <div className="glass" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <p style={{ fontSize: 11, color: "#64748b", fontWeight: 600, letterSpacing: "0.05em" }}>
        DECISION SIMULATOR
      </p>
      <p style={{ fontSize: 12, color: "#475569" }}>
        Adjust signals to see how the rule engine responds — no API call.
      </p>

      {/* Income slider */}
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
          <span style={{ fontSize: 13 }}>Monthly Income</span>
          <span style={{ fontSize: 13, fontWeight: 700, color: "#38bdf8" }}>₹{income.toLocaleString()}</span>
        </div>
        <input
          type="range" min={0} max={200000} step={5000}
          value={income} onChange={(e) => setIncome(Number(e.target.value))}
          style={{ width: "100%", accentColor: "#38bdf8" }}
        />
      </div>

      {/* Liveness slider */}
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
          <span style={{ fontSize: 13 }}>Liveness Score</span>
          <span style={{ fontSize: 13, fontWeight: 700, color: "#a78bfa" }}>{liveness.toFixed(2)}</span>
        </div>
        <input
          type="range" min={0} max={1} step={0.01}
          value={liveness} onChange={(e) => setLiveness(Number(e.target.value))}
          style={{ width: "100%", accentColor: "#a78bfa" }}
        />
      </div>

      {/* Risk + Product */}
      <div style={{ display: "flex", gap: 12 }}>
        <div style={{ flex: 1 }}>
          <p style={{ fontSize: 11, color: "#64748b", marginBottom: 6 }}>RISK LEVEL</p>
          <div style={{ display: "flex", gap: 6 }}>
            {["low", "medium", "high"].map((r) => (
              <button
                key={r}
                onClick={() => setRisk(r)}
                style={{
                  flex: 1, padding: "6px 0", borderRadius: 8, border: "none", cursor: "pointer",
                  background: risk === r ? (r === "low" ? "rgba(34,197,94,0.2)" : r === "medium" ? "rgba(245,158,11,0.2)" : "rgba(239,68,68,0.2)") : "rgba(255,255,255,0.04)",
                  color: risk === r ? (r === "low" ? "#22c55e" : r === "medium" ? "#f59e0b" : "#ef4444") : "#475569",
                  fontSize: 12, fontWeight: 600, textTransform: "capitalize",
                  border: risk === r ? `1px solid ${r === "low" ? "#22c55e" : r === "medium" ? "#f59e0b" : "#ef4444"}` : "1px solid transparent",
                }}
              >
                {r}
              </button>
            ))}
          </div>
        </div>
        <div style={{ flex: 1 }}>
          <p style={{ fontSize: 11, color: "#64748b", marginBottom: 6 }}>PRODUCT</p>
          <select
            className="select"
            value={product}
            onChange={(e) => setProduct(e.target.value)}
            style={{ width: "100%", fontSize: 12 }}
          >
            {PRODUCTS.map((p) => (
              <option key={p} value={p} style={{ background: "#0f172a" }}>
                {p.charAt(0).toUpperCase() + p.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Live result */}
      <div className="glass-light" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <p style={{ fontSize: 11, color: "#64748b" }}>SIMULATED DECISION</p>
          <p style={{ fontSize: 22, fontWeight: 800, color: statusColor, marginTop: 2 }}>{result.status}</p>
          {result.reason && <p style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>{result.reason}</p>}
        </div>
        {result.emi && (
          <div style={{ textAlign: "right" }}>
            <p style={{ fontSize: 11, color: "#64748b" }}>EMI</p>
            <p style={{ fontSize: 20, fontWeight: 700, color: "#22c55e" }}>₹{result.emi.toLocaleString()}</p>
            <p style={{ fontSize: 11, color: "#475569" }}>{result.tenure}</p>
          </div>
        )}
      </div>
    </div>
  );
}
