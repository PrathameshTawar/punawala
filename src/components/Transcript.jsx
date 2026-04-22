import { useEffect, useState } from "react";

export default function Transcript({ text }) {
  const [displayed, setDisplayed] = useState("");

  useEffect(() => {
    if (!text) return;
    setDisplayed("");
    let i = 0;
    const iv = setInterval(() => {
      setDisplayed(text.slice(0, i + 1));
      i++;
      if (i >= text.length) clearInterval(iv);
    }, 22);
    return () => clearInterval(iv);
  }, [text]);

  return (
    <div className="glass" style={{ minHeight: 72 }}>
      <p style={{ fontSize: 11, color: "#64748b", fontWeight: 600, letterSpacing: "0.05em", marginBottom: 8 }}>
        TRANSCRIPT
      </p>
      <p style={{ fontSize: 14, lineHeight: 1.7, color: displayed ? "#e2e8f0" : "#334155" }}>
        {displayed || "Waiting for speech..."}
        {displayed && displayed.length < (text?.length ?? 0) && (
          <span style={{ borderRight: "2px solid #38bdf8", marginLeft: 2, animation: "pulse 1s infinite" }} />
        )}
      </p>
    </div>
  );
}
