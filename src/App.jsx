import { useState, useEffect } from "react";
import { BrowserRouter as Router, Routes, Route, useNavigate, useLocation, Navigate } from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import KYCPage from "./pages/KYCPage";
import AuditorDashboard from "./pages/AuditorDashboard";
import ApplicationHistory from "./pages/ApplicationHistory";
import { getMe } from "./services/api";

function AppContent() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  // Restore session on reload
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (token) {
      getMe()
        .then((u) => {
          setUser(u);
          // Navigate to default page based on role
          if (u.role === "auditor" || u.role === "admin") {
            navigate("/auditor");
          } else {
            navigate("/kyc");
          }
        })
        .catch(() => localStorage.removeItem("token"))
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [navigate]);

  const handleLogin = (u) => {
    setUser(u);
    if (u.role === "auditor" || u.role === "admin") {
      navigate("/auditor");
    } else {
      navigate("/kyc");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    setUser(null);
    navigate("/", { replace: true });
  };

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <p style={{ color: "#475569" }}>Loading...</p>
      </div>
    );
  }

  const isAuditor = user && (user.role === "auditor" || user.role === "admin");

  return (
    <div style={{ minHeight: "100vh" }}>
      {/* Topbar */}
      {user && (
        <div className="topbar">
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <span style={{ fontSize: 20, fontWeight: 800, color: "#38bdf8" }}>Loan Wizard</span>
            <span style={{ fontSize: 11, color: "#475569", background: "#0f172a", padding: "2px 10px", borderRadius: 999, border: "1px solid rgba(255,255,255,0.06)" }}>
              AI KYC v2
            </span>

            {/* Nav */}
            <nav style={{ display: "flex", gap: 4, marginLeft: 16 }}>
              <button
                onClick={() => navigate("/kyc")}
                style={{
                  padding: "6px 14px", borderRadius: 8, border: "none", cursor: "pointer",
                  background: location.pathname === "/kyc" ? "rgba(56,189,248,0.15)" : "transparent",
                  color: location.pathname === "/kyc" ? "#38bdf8" : "#64748b",
                  fontWeight: 600, fontSize: 13,
                  borderBottom: location.pathname === "/kyc" ? "2px solid #38bdf8" : "2px solid transparent",
                }}
              >
                KYC Session
              </button>
              <button
                onClick={() => navigate("/history")}
                style={{
                  padding: "6px 14px", borderRadius: 8, border: "none", cursor: "pointer",
                  background: location.pathname === "/history" ? "rgba(56,189,248,0.15)" : "transparent",
                  color: location.pathname === "/history" ? "#38bdf8" : "#64748b",
                  fontWeight: 600, fontSize: 13,
                  borderBottom: location.pathname === "/history" ? "2px solid #38bdf8" : "2px solid transparent",
                }}
              >
                My Applications
              </button>
              {isAuditor && (
                <button
                  onClick={() => navigate("/auditor")}
                  style={{
                    padding: "6px 14px", borderRadius: 8, border: "none", cursor: "pointer",
                    background: location.pathname === "/auditor" ? "rgba(56,189,248,0.15)" : "transparent",
                    color: location.pathname === "/auditor" ? "#38bdf8" : "#64748b",
                    fontWeight: 600, fontSize: 13,
                    borderBottom: location.pathname === "/auditor" ? "2px solid #38bdf8" : "2px solid transparent",
                  }}
                >
                  Auditor Panel
                </button>
              )}
            </nav>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div style={{ textAlign: "right" }}>
              <p style={{ fontSize: 13, fontWeight: 600 }}>{user.full_name || user.username}</p>
              <p style={{ fontSize: 11, color: "#64748b", textTransform: "capitalize" }}>{user.role}</p>
            </div>
            <button
              onClick={handleLogout}
              style={{ padding: "6px 14px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.08)", background: "transparent", color: "#64748b", fontSize: 13, cursor: "pointer" }}
            >
              Sign Out
            </button>
          </div>
        </div>
      )}

      {/* Page content */}
      <Routes>
        <Route index element={!user ? <LoginPage onLogin={handleLogin} /> : <Navigate to="/kyc" replace />} />
        <Route path="/kyc" element={user ? <KYCPage /> : <Navigate to="/" replace />} />
        <Route path="/history" element={user ? <ApplicationHistory /> : <Navigate to="/" replace />} />
        <Route path="/auditor" element={isAuditor ? <AuditorDashboard /> : <Navigate to="/" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}

export default function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

