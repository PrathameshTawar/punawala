import { useEffect, useState } from "react";
import { getMyApplications } from "../services/api";

function SkeletonRow() {
  return (
    <div className="glass" style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr 1fr", gap: 16, alignItems: "center" }}>
      {[180, 80, 80, 70, 90].map((w, i) => (
        <div key={i} className="skeleton" style={{ height: 16, width: w, borderRadius: 6 }} />
      ))}
    </div>
  );
}

export default function ApplicationHistory() {
  const [apps,    setApps]    = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState("");

  const load = () => {
    setLoading(true);
    setError("");
    getMyApplications()
      .then(setApps)
      .catch(() => setError("Failed to load applications. Please try again."))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  return (
    <div style={{ maxWidth: 1000, margin: "32px auto", padding: "0 24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <p style={{ fontSize: 18, fontWeight: 700 }}>My Applications</p>
        <button
          onClick={load}
          style={{ padding: "6px 14px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.1)", background: "transparent", color: "#64748b", fontSize: 13, cursor: "pointer" }}
        >
          ↻ Refresh
        </button>
      </div>

      {error && (
        <div style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", borderRadius: 10, padding: 16, marginBottom: 16 }}>
          <p style={{ color: "#ef4444", fontSize: 13, marginBottom: 8 }}>{error}</p>
          <button onClick={load} style={{ padding: "6px 14px", borderRadius: 6, border: "1px solid #ef4444", background: "transparent", color: "#ef4444", fontSize: 12, cursor: "pointer" }}>
            Retry
          </button>
        </div>
      )}

      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {[1, 2, 3].map((i) => <SkeletonRow key={i} />)}
        </div>
      ) : apps.length === 0 ? (
        <div className="glass" style={{ textAlign: "center", padding: 48, color: "#475569" }}>
          No applications yet. Start a KYC session to apply.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {apps.map((a) => (
            <div key={a.session_id} className="glass" style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr 1fr", alignItems: "center", gap: 16 }}>
              <div>
                <p style={{ fontFamily: "monospace", fontSize: 12, color: "#38bdf8" }}>{a.session_id}</p>
                <p style={{ fontSize: 13, color: "#94a3b8", marginTop: 2, textTransform: "capitalize" }}>{a.loan_product} loan</p>
              </div>
              <div>
                <p style={{ fontSize: 11, color: "#64748b" }}>Income</p>
                <p style={{ fontSize: 14, fontWeight: 600 }}>{a.income ? `₹${a.income.toLocaleString()}` : "—"}</p>
              </div>
              <div>
                <p style={{ fontSize: 11, color: "#64748b" }}>EMI</p>
                <p style={{ fontSize: 14, fontWeight: 600, color: "#22c55e" }}>{a.emi ? `₹${a.emi.toLocaleString()}` : "—"}</p>
              </div>
              <div>
                <span className={`badge ${a.status === "Approved" ? "badge-green" : a.status === "Manual Review" ? "badge-yellow" : "badge-red"}`}>
                  {a.status}
                </span>
              </div>
              <div>
                <p style={{ fontSize: 12, color: "#475569" }}>
                  {a.created_at ? new Date(a.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "—"}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
