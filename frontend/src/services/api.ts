import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  headers: {
    "Content-Type": "application/json"
  }
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("zella_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const fetchDashboardOverview = async () => {
  const { data } = await api.get("/api/dashboard/overview");
  return data;
};

export const fetchDashboardMetrics = async () => {
  const { data } = await api.get("/api/dashboard/metrics");
  return data;
};

export const fetchRecentTrades = async () => {
  const { data } = await api.get("/api/dashboard/trades/recent");
  return data;
};

export const fetchAccountSnapshots = async () => {
  const { data } = await api.get("/api/dashboard/account/snapshots");
  return data;
};

export const fetchAccountSummary = async () => {
  const { data } = await api.get("/api/account/summary");
  return data;
};

export const fetchPositions = async () => {
  const { data } = await api.get("/api/account/positions");
  return data;
};

export const fetchOrders = async () => {
  const { data } = await api.get("/api/trading/orders");
  return data;
};

export const cancelOrder = async (orderId: number) => {
  const { data } = await api.delete(`/api/trading/order/${orderId}`);
  return data;
};

export const modifyOrder = async (orderId: number, payload: Record<string, unknown>) => {
  const { data } = await api.put(`/api/trading/order/${orderId}`, payload);
  return data;
};

export const fetchRiskSummary = async () => {
  const { data } = await api.get("/api/risk/summary");
  return data;
};

export const fetchAlerts = async () => {
  const { data } = await api.get("/api/alerts?limit=50");
  return data;
};

export const acknowledgeAlert = async (alertId: string) => {
  const { data } = await api.post("/api/alerts/ack", { alert_id: alertId });
  return data;
};

export const triggerKillSwitch = async () => {
  const { data } = await api.post("/api/trading/kill-switch");
  return data;
};

export const runBacktest = async (payload: Record<string, unknown>) => {
  const { data } = await api.post("/api/backtest/run", payload);
  return data;
};

export default api;
