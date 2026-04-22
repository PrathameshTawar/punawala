import { useEffect, useState } from "react";
import { getAuditorQueue, getAllApplications, getStats, reviewApplication, getAuditTrail } from "../services/api";

export default function AuditorDashboard() {
  const [tab,      setTab]      = useState("queue");
  const [queue,    setQueue]    = useState([]);
  const [all,      setAll]      = useState([]);
  const [stats,    setStats]    = useState(null);
  const [selected, setSelected] = useState(null);
  const [note,     setNote]     = useState("");
  const [loading,  setLoading]  = useState(false);
  const [trail,    setTrail]    = useState(null);  // audit trail modal
  const [trailLoading, setTrailLoading] = useState(false);

  const load = async () => {
    const [q, a, s] = await Promise.all([getAuditorQueue(), getAllApplications(), getStats()]);
    setQueue(q); setAll(a); setStats(s);
  };

  useEffect(() => { load(); }, []);

  const handleReview = async (override) => {
    if (!selected) return;
    setLoading(true);
    try {
      await reviewApplication(selected.session_id, override, note);
      setSelected(null); setNote("");
      await load();
    } finally {
      setLoading(false);
    }
  };

  const openAuditTrail = async (sessionId) => {
    setTrailLoading(true);
    setTrail({ session_id: sessionId, events: [] });
    try {
      const data = await getAuditTrail(sessionId);
      setTrail(data);
    } catch {
      setTrail({ session_id: sessionId, events: [], error: "Failed to load" });
    } finally {
      setTrailLoading(false);
    }
  };

  const rows = tab === "queue" ? queue : all;

  return (
    <div style={{ maxWidth: 1300, margin: "32px auto", padding: "0 24px", display: "flex", flexDirection: "column", gap: 24 }}>

      {/* Stats */}
      {stats && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 14 }}>
          {[
            { label: "Total",          value: stats.total,          color: "#e2e8f0" },
            { label: "Approved",       value: stats.approved,       color: "#22c55e" },
            { label: "Rejected",       value: stats.rejected,       color: "#ef4444" },
            { label: "Pending Review", value: stats.pending_review, color: "#f59e0b" },
            { label: "Approval Rate",  value: `${stats.approval_rate}%`, color: "#38bdf8" },
          ].map((s) => (
            <div key={s.label} className="stat-card">
              <p style={{ fontSize: 10, color: "#64748b", fontWeight: 600, letterSpacing: "0.05em" }}>{s.label.toUpperCase()}</p>
              <p style={{ fontSize: 28, fontWeight: 800, color: s.color, marginTop: 4 }}>{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: "flex", gap: 8 }}>
        {[["queue", `Review Queue (${queue.length})`], ["all", "All Applications"]].map(([k, label]) => (
          <button key={k} onClick={() => setTab(k)} style={{
            padding: "8px 18px", borderRadius: 8, border: "none", cursor: "pointer",
            background: tab === k ? "#38bdf8" : "rgba(255,255,255,0.05)",
            color: tab === k ? "#060d1a" : "#94a3b8",
            fontWeight: 600, fontSize: 13,
          }}>
            {label}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="glass" style={{ padding: 0, overflow: "auto" }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Session ID</th>
              <th>Applicant</th>
              <th>Product</th>
              <th>Income</th>
              <th>Risk</th>
              <th>Liveness</th>
              <th>Confidence</th>
              <th>AI Decision</th>
              <th>Final</th>
              <th>Date</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr><td colSpan={11} style={{ textAlign: "center", color: "#475569", padding: 32 }}>No applications</td></tr>
            )}
            {rows.map((a) => (
              <tr key={a.session_id}>
                <td>
                  <button
                    onClick={() => openAuditTrail(a.session_id)}
                    style={{ background: "none", border: "none", color: "#38bdf8", fontFamily: "monospace", fontSize: 12, cursor: "pointer", padding: 0 }}
                  >
                    {a.session_id}
                  </button>
                </td>
                <td>{a.applicant_name || "—"}</td>
                <td style={{ textTransform: "capitalize" }}>{a.loan_product}</td>
                <td>{a.income ? `₹${a.income.toLocaleString()}` : "—"}</td>
                <td>
                  <span className={`badge ${a.risk_level === "low" ? "badge-green" : a.risk_level === "medium" ? "badge-yellow" : "badge-red"}`}>
                    {a.risk_level}
                  </span>
                </td>
                <td>{a.liveness_score ? (a.liveness_score * 100).toFixed(0) + "%" : "—"}</td>
                <td>
                  {a.confidence != null ? (
                    <span style={{ fontSize: 13, fontWeight: 600, color: a.confidence > 0.7 ? "#22c55e" : a.confidence > 0.4 ? "#f59e0b" : "#ef4444" }}>
                      {(a.confidence * 100).toFixed(0)}%
                    </span>
                  ) : "—"}
                </td>
                <td>
                  <span className={`badge ${a.ai_status === "Approved" ? "badge-green" : a.ai_status === "Manual Review" ? "badge-yellow" : "badge-red"}`}>
                    {a.ai_status}
                  </span>
                </td>
                <td>
                  <span className={`badge ${a.status === "Approved" ? "badge-green" : a.status === "Manual Review" ? "badge-yellow" : "badge-red"}`}>
                    {a.status}
                  </span>
                </td>
                <td style={{ fontSize: 12, color: "#64748b" }}>
                  {a.created_at ? new Date(a.created_at).toLocaleDateString("en-IN") : "—"}
                </td>
                <td>
                  {(a.flagged || a.ai_status === "Manual Review") && (
                    <button
                      onClick={() => { setSelected(a); setNote(""); }}
                      style={{ padding: "4px 10px", borderRadius: 6, border: "1px solid #38bdf8", background: "transparent", color: "#38bdf8", fontSize: 12, cursor: "pointer" }}
                    >
                      Review
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ── Review modal ── */}
      {selected && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 200 }}>
          <div className="glass" style={{ width: 500, display: "flex", flexDirection: "column", gap: 16, maxHeight: "90vh", overflowY: "auto" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <p style={{ fontWeight: 700, fontSize: 16 }}>Review Application</p>
              <button onClick={() => setSelected(null)} style={{ background: "none", border: "none", color: "#64748b", cursor: "pointer", fontSize: 18 }}>✕</button>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              {[
                ["Session",     selected.session_id],
                ["Applicant",   selected.applicant_name || "—"],
                ["Income",      selected.income ? `₹${selected.income.toLocaleString()}` : "—"],
                ["Risk Level",  selected.risk_level],
                ["Liveness",    selected.liveness_score ? (selected.liveness_score * 100).toFixed(0) + "%" : "—"],
                ["Confidence",  selected.confidence != null ? (selected.confidence * 100).toFixed(0) + "%" : "—"],
                ["AI Decision", selected.ai_status],
                ["Product",     selected.loan_product],
              ].map(([k, v]) => (
                <div key={k} className="glass-light">
                  <p style={{ fontSize: 11, color: "#64748b" }}>{k}</p>
                  <p style={{ fontSize: 13, fontWeight: 600, marginTop: 2 }}>{v}</p>
                </div>
              ))}
            </div>

            {selected.transcript && (
              <div className="glass-light">
                <p style={{ fontSize: 11, color: "#64748b", marginBottom: 4 }}>TRANSCRIPT</p>
                <p style={{ fontSize: 13, lineHeight: 1.6 }}>{selected.transcript}</p>
              </div>
            )}

            <textarea
              className="input"
              placeholder="Auditor note (required for override)"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={3}
              style={{ resize: "vertical" }}
            />

            <div style={{ display: "flex", gap: 10 }}>
              <button className="btn-success" style={{ flex: 1 }} onClick={() => handleReview("Approved")} disabled={loading}>
                ✓ Approve
              </button>
              <button className="btn-danger" style={{ flex: 1 }} onClick={() => handleReview("Rejected")} disabled={loading}>
                ✗ Reject
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Audit trail modal ── */}
      {trail && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 200 }}>
          <div className="glass" style={{ width: 560, display: "flex", flexDirection: "column", gap: 16, maxHeight: "85vh" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <p style={{ fontWeight: 700, fontSize: 15 }}>Audit Trail</p>
                <p style={{ fontSize: 11, color: "#475569", fontFamily: "monospace", marginTop: 2 }}>{trail.session_id}</p>
              </div>
              <button onClick={() => setTrail(null)} style={{ background: "none", border: "none", color: "#64748b", cursor: "pointer", fontSize: 18 }}>✕</button>
            </div>

            <div style={{ overflowY: "auto", display: "flex", flexDirection: "column", gap: 10 }}>
              {trailLoading && <p style={{ color: "#475569", fontSize: 13 }}>Loading...</p>}
              {trail.error && <p style={{ color: "#ef4444", fontSize: 13 }}>{trail.error}</p>}
              {trail.events?.map((ev, i) => (
                <div key={i} className="glass-light" style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: 12, fontWeight: 700, color: "#38bdf8", fontFamily: "monospace" }}>{ev.action}</span>
                    <span style={{ fontSize: 11, color: "#475569" }}>{new Date(ev.timestamp).toLocaleString("en-IN")}</span>
                  </div>
                  <div style={{ display: "flex", gap: 12 }}>
                    <span className={`badge ${ev.actor_role === "auditor" || ev.actor_role === "admin" ? "badge-yellow" : "badge-gray"}`}>
                      {ev.actor_role}
                    </span>
                  </div>
                  {ev.detail && typeof ev.detail === "object" && (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 2 }}>
                      {Object.entries(ev.detail).map(([k, v]) => (
                        <span key={k} style={{ fontSize: 11, color: "#64748b" }}>
                          {k}: <span style={{ color: "#94a3b8" }}>{String(v)}</span>
                        </span>
                      ))}
                    </div>
                  )}
                  {ev.detail && typeof ev.detail === "string" && ev.detail && (
                    <p style={{ fontSize: 12, color: "#64748b" }}>{ev.detail}</p>
                  )}
                </div>
              ))}
              {!trailLoading && trail.events?.length === 0 && (
                <p style={{ color: "#475569", fontSize: 13 }}>No events recorded.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
