import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";

const BASE = [
  { t: "0s", risk: 35 }, { t: "1s", risk: 48 }, { t: "2s", risk: 38 },
  { t: "3s", risk: 25 }, { t: "4s", risk: 18 },
];

export default function RiskChart({ riskLevel }) {
  const final = riskLevel === "high" ? 82 : riskLevel === "medium" ? 48 : 12;
  const data = [...BASE, { t: "5s", risk: final }];

  return (
    <div className="glass">
      <p style={{ fontSize: 11, color: "#64748b", fontWeight: 600, letterSpacing: "0.05em", marginBottom: 12 }}>
        RISK TIMELINE
      </p>
      <ResponsiveContainer width="100%" height={110}>
        <LineChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
          <XAxis dataKey="t" tick={{ fill: "#475569", fontSize: 10 }} axisLine={false} tickLine={false} />
          <YAxis domain={[0, 100]} tick={{ fill: "#475569", fontSize: 10 }} axisLine={false} tickLine={false} />
          <ReferenceLine y={60} stroke="#ef4444" strokeDasharray="3 3" strokeOpacity={0.4} />
          <Tooltip
            contentStyle={{ background: "#0f172a", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: "#94a3b8" }}
            itemStyle={{ color: "#38bdf8" }}
          />
          <Line
            type="monotone" dataKey="risk" stroke="#38bdf8"
            strokeWidth={2} dot={false} animationDuration={1400}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
