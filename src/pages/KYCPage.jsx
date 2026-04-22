import { useState } from "react";
import VideoCall       from "../components/VideoCall";
import Transcript      from "../components/Transcript";
import AgentStatus     from "../components/AgentStatus";
import RiskMeter       from "../components/RiskMeter";
import RiskChart       from "../components/RiskChart";
import ResultCard      from "../components/ResultCard";
import ExplainPanel    from "../components/ExplainPanel";
import SimulationPanel from "../components/SimulationPanel";
import { sendAudio }   from "../services/api";

const PRODUCTS = ["personal", "home", "business", "vehicle"];

export default function KYCPage() {
  const [isRecording,  setIsRecording]  = useState(false);
  const [phase,        setPhase]        = useState(null);
  const [result,       setResult]       = useState(null);
  const [loanProduct,  setLoanProduct]  = useState("personal");
  const [error,        setError]        = useState("");
  const [activeTab,    setActiveTab]    = useState("live");

  const handleAudio = async (audioBlob, frameBlob) => {
    setError("");
    setPhase("voice_vision");
    try {
      const data = await sendAudio(audioBlob, loanProduct, frameBlob);
      setResult(data);
      setPhase("done");
    } catch (err) {
      const msg = err.response?.data?.detail || "Processing failed — is the backend running?";
      setError(msg);
      setPhase(null);
    } finally {
      setIsRecording(false);
    }
  };

  const startVerification = () => {
    setResult(null);
    setPhase(null);
    setError("");
    setIsRecording(true);
  };

  const decision  = result?.decision;
  const extracted = result?.extracted;
  const vision    = result?.vision;
  const isProcessing = phase && phase !== "done";

  return (
    <div style={{ maxWidth: 1200, margin: "32px auto", padding: "0 24px", display: "flex", flexDirection: "column", gap: 20 }}>

      {/* Tab toggle */}
      <div style={{ display: "flex", gap: 8 }}>
        {[["live", "▶ Live KYC"], ["simulate", "⚡ Simulation Mode"]].map(([k, label]) => (
          <button key={k} onClick={() => setActiveTab(k)} style={{
            padding: "8px 18px", borderRadius: 8, border: "none", cursor: "pointer",
            background: activeTab === k ? "#38bdf8" : "rgba(255,255,255,0.05)",
            color: activeTab === k ? "#060d1a" : "#64748b",
            fontWeight: 600, fontSize: 13,
          }}>
            {label}
          </button>
        ))}
      </div>

      {activeTab === "simulate" ? (
        <SimulationPanel />
      ) : (
        /* Responsive: 2-col on desktop, 1-col on mobile */
        <div className="kyc-grid" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>

          {/* LEFT */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div className="glass" style={{ padding: 0, overflow: "hidden" }}>
              <VideoCall onAudioReady={handleAudio} isRecording={isRecording} />
            </div>

            <div className="glass" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div>
                <p style={{ fontSize: 11, color: "#64748b", marginBottom: 6, fontWeight: 600 }}>LOAN PRODUCT</p>
                <select
                  className="select"
                  value={loanProduct}
                  onChange={(e) => setLoanProduct(e.target.value)}
                  style={{ width: "100%" }}
                  disabled={isRecording || isProcessing}
                >
                  {PRODUCTS.map((p) => (
                    <option key={p} value={p} style={{ background: "#0f172a" }}>
                      {p.charAt(0).toUpperCase() + p.slice(1)} Loan
                    </option>
                  ))}
                </select>
              </div>

              <button
                className="btn-primary"
                onClick={startVerification}
                disabled={isRecording || isProcessing}
                style={{ width: "100%", padding: "14px" }}
              >
                {isProcessing
                  ? "⏳ Processing..."
                  : isRecording
                  ? "🎙️ Recording (5s)..."
                  : "▶ Start KYC Verification"}
              </button>

              {/* Error with retry button */}
              {error && (
                <div style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", borderRadius: 10, padding: 12 }}>
                  <p style={{ color: "#ef4444", fontSize: 13, marginBottom: 8 }}>{error}</p>
                  <button
                    onClick={startVerification}
                    style={{ padding: "6px 14px", borderRadius: 6, border: "1px solid #ef4444", background: "transparent", color: "#ef4444", fontSize: 12, cursor: "pointer" }}
                  >
                    Try Again
                  </button>
                </div>
              )}

              <p style={{ fontSize: 12, color: "#475569", lineHeight: 1.6 }}>
                Say: <span style={{ color: "#38bdf8" }}>
                  "I earn ₹50,000 and I agree to the loan terms."
                </span>
              </p>
            </div>

            <AgentStatus phase={phase} />

            {/* Real timing from server */}
            {result?.timing_ms && (
              <div className="glass-light" style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
                {[
                  ["Voice + Vision", result.timing_ms.voice_vision],
                  ["LLM",            result.timing_ms.llm],
                  ["Risk Engine",    result.timing_ms.risk],
                  ["Total",          result.timing_ms.total],
                ].map(([label, ms]) => (
                  <div key={label}>
                    <p style={{ fontSize: 10, color: "#475569", textTransform: "uppercase" }}>{label}</p>
                    <p style={{ fontSize: 13, fontWeight: 700, color: label === "Total" ? "#22c55e" : "#38bdf8" }}>{ms}ms</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* RIGHT */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <Transcript text={result?.transcript} />
            <RiskMeter
              riskLevel={extracted?.risk_level}
              livenessScore={vision?.liveness_score}
              income={extracted?.income}
            />
            <RiskChart riskLevel={extracted?.risk_level} />
            <ResultCard decision={decision} extracted={extracted} sessionId={result?.session_id} />
            <ExplainPanel decision={decision} sessionId={result?.session_id} />
          </div>

        </div>
      )}
    </div>
  );
}
