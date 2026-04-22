const AGENTS = [
  { icon: "🎤", label: "Voice Agent",  sub: "Whisper STT",        key: "voice"  },
  { icon: "👁️", label: "Vision Agent", sub: "Face & Liveness",    key: "vision" },
  { icon: "🧠", label: "LLM Agent",    sub: "GPT-4o Extraction",  key: "llm"    },
  { icon: "⚖️", label: "Risk Agent",   sub: "Rule Engine",        key: "risk"   },
];

export default function AgentStatus({ phase }) {
  // phase: null | "voice_vision" | "llm" | "risk" | "done"
  const getState = (key) => {
    if (!phase) return "idle";
    if (phase === "done") return "done";
    if (key === "voice" || key === "vision") return phase === "voice_vision" ? "active" : "done";
    if (key === "llm") return phase === "llm" ? "active" : phase === "risk" || phase === "done" ? "done" : "idle";
    if (key === "risk") return phase === "risk" ? "active" : phase === "done" ? "done" : "idle";
    return "idle";
  };

  const stateStyle = (s) => ({
    idle:   { color: "#475569", label: "○ Idle" },
    active: { color: "#38bdf8", label: "● Running" },
    done:   { color: "#22c55e", label: "✓ Done" },
  }[s]);

  return (
    <div className="glass">
      <p style={{ fontSize: 11, color: "#64748b", marginBottom: 14, fontWeight: 600, letterSpacing: "0.05em" }}>
        AI PIPELINE
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {AGENTS.map((a) => {
          const s = getState(a.key);
          const st = stateStyle(s);
          return (
            <div key={a.key} style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: 18, width: 28, textAlign: "center" }}>{a.icon}</span>
              <div style={{ flex: 1 }}>
                <p style={{ fontSize: 13, fontWeight: 600 }}>{a.label}</p>
                <p style={{ fontSize: 11, color: "#475569" }}>{a.sub}</p>
              </div>
              <span style={{ fontSize: 12, color: st.color, fontWeight: 600, minWidth: 70, textAlign: "right" }}>
                {st.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
