import { useState } from "react";
import { login, register } from "../services/api";

export default function LoginPage({ onLogin }) {
  const [mode, setMode] = useState("login"); // login | register
  const [form, setForm] = useState({ username: "", password: "", full_name: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handle = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      let data;
      if (mode === "login") {
        data = await login(form.username, form.password);
      } else {
        data = await register(form.username, form.password, form.full_name);
      }
      localStorage.setItem("token", data.access_token);
      onLogin({ role: data.role, full_name: data.full_name, username: form.username });
    } catch (err) {
      setError(err.response?.data?.detail || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div className="glass" style={{ width: 380, display: "flex", flexDirection: "column", gap: 20 }}>
        {/* Logo */}
        <div style={{ textAlign: "center" }}>
          <p style={{ fontSize: 26, fontWeight: 800, color: "#38bdf8" }}>Loan Wizard</p>
          <p style={{ fontSize: 13, color: "#64748b", marginTop: 4 }}>AI-Powered KYC Platform</p>
        </div>

        {/* Tab toggle */}
        <div style={{ display: "flex", background: "#0f172a", borderRadius: 10, padding: 4 }}>
          {["login", "register"].map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              style={{
                flex: 1, padding: "8px", borderRadius: 8, border: "none",
                background: mode === m ? "#38bdf8" : "transparent",
                color: mode === m ? "#060d1a" : "#64748b",
                fontWeight: 600, fontSize: 13, cursor: "pointer",
                textTransform: "capitalize",
              }}
            >
              {m}
            </button>
          ))}
        </div>

        <form onSubmit={handle} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {mode === "register" && (
            <input
              className="input"
              placeholder="Full Name"
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              required
            />
          )}
          <input
            className="input"
            placeholder="Username"
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
            required
          />
          <input
            className="input"
            type="password"
            placeholder="Password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            required
          />
          {error && <p style={{ color: "#ef4444", fontSize: 13 }}>{error}</p>}
          <button className="btn-primary" type="submit" disabled={loading} style={{ width: "100%", marginTop: 4 }}>
            {loading ? "Please wait..." : mode === "login" ? "Sign In" : "Create Account"}
          </button>
        </form>

        {/* Demo credentials */}
        <div style={{ background: "#0f172a", borderRadius: 10, padding: 12 }}>
          <p style={{ fontSize: 11, color: "#475569", marginBottom: 8, fontWeight: 600 }}>DEMO CREDENTIALS</p>
          {[
            { label: "Applicant", u: "applicant", p: "Demo@12345" },
            { label: "Auditor",   u: "auditor",   p: "Demo@12345" },
          ].map((d) => (
            <div
              key={d.u}
              onClick={() => setForm({ ...form, username: d.u, password: d.p })}
              style={{ cursor: "pointer", padding: "4px 0", fontSize: 12, color: "#38bdf8" }}
            >
              {d.label}: {d.u} / {d.p}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
