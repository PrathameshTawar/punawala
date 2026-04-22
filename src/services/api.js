import axios from "axios";

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

const client = axios.create({ baseURL: BASE, timeout: 30000 });

// Attach JWT to every request
client.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Retry once on network errors (not on 4xx/5xx — those are intentional)
client.interceptors.response.use(
  (res) => res,
  async (err) => {
    const isNetworkError = !err.response;
    const isRetried = err.config?._retried;
    if (isNetworkError && !isRetried) {
      err.config._retried = true;
      await new Promise((r) => setTimeout(r, 1000));
      return client(err.config);
    }
    return Promise.reject(err);
  }
);

// ── Auth ──────────────────────────────────────────────────────────────────────
export const login = (username, password) => {
  const form = new URLSearchParams({ username, password });
  return client.post("/auth/login", form).then((r) => r.data);
};
export const register = (username, password, full_name) =>
  client.post("/auth/register", { username, password, full_name }).then((r) => r.data);
export const getMe = () => client.get("/auth/me").then((r) => r.data);

// ── KYC ───────────────────────────────────────────────────────────────────────
export const sendAudio = (audioBlob, loanProduct = "personal", frameBlob = null) => {
  const form = new FormData();
  form.append("file", audioBlob, "audio.wav");
  form.append("loan_product", loanProduct);
  if (frameBlob) {
    form.append("video_frame", frameBlob, "frame.jpg");
  }
  // Use /process (backward-compat alias) — /sessions returns 201
  return client.post("/kyc/process", form).then((r) => r.data);
};
export const getExplain = (sessionId) =>
  client.get(`/kyc/${sessionId}/explain`).then((r) => r.data);

// ── Client-side simulation (no API call) ─────────────────────────────────────
export const simulateDecision = (income, riskLevel, livenessScore, loanProduct) =>
  client.post("/kyc/simulate", { 
    income, 
    risk_level: riskLevel,
    liveness_score: livenessScore, 
    loan_product: loanProduct 
  }).then(r => r.data);

// ── Applications ──────────────────────────────────────────────────────────────
export const getMyApplications = () => client.get("/applications/my").then((r) => r.data);
export const getApplication    = (id) => client.get(`/applications/${id}`).then((r) => r.data);

// ── Auditor ───────────────────────────────────────────────────────────────────
export const getAuditorQueue      = () => client.get("/auditor/queue").then((r) => r.data);
export const getAllApplications    = () => client.get("/auditor/applications").then((r) => r.data);
export const getStats             = () => client.get("/auditor/stats").then((r) => r.data);
export const getRejectionReasons  = () => client.get("/auditor/stats/reasons").then((r) => r.data);
export const reviewApplication    = (sessionId, override, note) =>
  client.post(`/auditor/${sessionId}/review`, { override, note }).then((r) => r.data);

// ── Audit trail ───────────────────────────────────────────────────────────────
export const getAuditTrail = (sessionId) =>
  client.get(`/audit/${sessionId}`).then((r) => r.data);
