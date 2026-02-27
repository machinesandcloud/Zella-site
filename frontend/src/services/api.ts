import axios from "axios";

// Check if VITE_API_URL is explicitly set (not undefined, not empty)
const API_URL = import.meta.env.VITE_API_URL?.trim();
const hasExplicitApiUrl = API_URL !== undefined && API_URL !== "";

// Use localhost:8000 as default for development
const baseURL = hasExplicitApiUrl ? API_URL : "http://localhost:8000";

// Only use fast timeout when explicitly set to empty string (Netlify demo mode)
const isNetlifyDemoMode = import.meta.env.VITE_API_URL === "";
const timeout = isNetlifyDemoMode ? 1000 : 30000;

const api = axios.create({
  baseURL,
  headers: {
    "Content-Type": "application/json"
  },
  timeout
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("zella_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem("zella_token");
      window.dispatchEvent(new Event("auth:logout"));
    }
    return Promise.reject(error);
  }
);

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

export const fetchTrades = async () => {
  const { data } = await api.get("/api/trades");
  return data;
};

export const fetchSetupStats = async () => {
  const { data } = await api.get("/api/trades/setup-stats");
  return data;
};

export const updateTradeNotes = async (
  tradeId: number,
  payload: { notes?: string; setup_tag?: string; catalyst?: string; stop_method?: string; risk_mode?: string }
) => {
  const { data } = await api.put(`/api/trades/${tradeId}/notes`, payload);
  return data;
};

export const fetchNews = async () => {
  const { data } = await api.get("/api/news");
  return data;
};

export const fetchCatalysts = async (symbols: string[]) => {
  const { data } = await api.get(`/api/news/catalysts?symbols=${symbols.join(",")}`);
  return data;
};

export const fetchMarketSession = async () => {
  const { data } = await api.get("/api/market/session");
  return data;
};

export const fetchAccountSummary = async () => {
  const { data } = await api.get("/api/alpaca/account");
  return data;
};

export const fetchIbkrStatus = async () => {
  const { data } = await api.get("/api/ibkr/status");
  return data;
};

export const fetchIbkrWebapiStatus = async () => {
  const { data } = await api.get("/api/ibkr/webapi/status");
  return data;
};

export const fetchIbkrDefaults = async () => {
  const { data } = await api.get("/api/settings/ibkr-defaults");
  return data;
};

export const fetchAlpacaStatus = async () => {
  const { data } = await api.get("/api/alpaca/status");
  return data;
};

export const fetchAlpacaAccount = async () => {
  const { data } = await api.get("/api/alpaca/account");
  return data;
};

export const fetchAlpacaPositions = async () => {
  const { data } = await api.get("/api/alpaca/positions");
  return data;
};

export const autoLogin = async () => {
  const { data } = await api.post("/api/auth/auto-login");
  return data;
};

export const fetchPositions = async () => {
  const { data } = await api.get("/api/alpaca/positions");
  return data;
};

export const closePosition = async (symbol: string) => {
  const { data } = await api.post("/api/trading/positions/close", { symbol });
  return data;
};

export const fetchOrders = async () => {
  const { data } = await api.get("/api/alpaca/orders");
  return data;
};

export const cancelOrder = async (orderId: number) => {
  const { data } = await api.delete(`/api/alpaca/order/${orderId}`);
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

export const fetchAlertSettings = async () => {
  const { data } = await api.get("/api/alerts/settings");
  return data;
};

export const updateAlertSettings = async (payload: Record<string, unknown>) => {
  const { data } = await api.put("/api/alerts/settings", payload);
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

export const fetchStrategies = async () => {
  const { data } = await api.get("/api/strategies");
  return data;
};

export const fetchAiActivity = async () => {
  const { data } = await api.get("/api/ai/activity");
  return data;
};

export const fetchAiStatus = async () => {
  const { data } = await api.get("/api/ai/status");
  return data;
};

export const startStrategy = async (strategyId: string, payload: Record<string, unknown>) => {
  const { data } = await api.post(`/api/strategies/${strategyId}/start`, payload);
  return data;
};

export const stopStrategy = async (strategyId: string) => {
  const { data } = await api.post(`/api/strategies/${strategyId}/stop`);
  return data;
};

export const fetchStrategyConfig = async (strategyId: string) => {
  const { data } = await api.get(`/api/strategies/${strategyId}`);
  return data;
};

export const updateStrategyConfig = async (strategyId: string, payload: Record<string, unknown>) => {
  const { data } = await api.put(`/api/strategies/${strategyId}/config`, payload);
  return data;
};

export const fetchStrategyPerformance = async (strategyId: string) => {
  const { data } = await api.get(`/api/strategies/${strategyId}/performance`);
  return data;
};

export const fetchStrategyLogs = async (strategyId: string) => {
  const { data } = await api.get(`/api/strategies/${strategyId}/logs`);
  return data;
};

// ==================== Autonomous Engine API ====================

export const startAutonomousEngine = async () => {
  const { data } = await api.post("/api/ai/autonomous/start");
  return data;
};

export const stopAutonomousEngine = async () => {
  const { data } = await api.post("/api/ai/autonomous/stop");
  return data;
};

export const getAutonomousStatus = async () => {
  const { data } = await api.get("/api/ai/autonomous/status");
  return data;
};

export const updateAutonomousConfig = async (config: Record<string, unknown>) => {
  const { data } = await api.post("/api/ai/autonomous/config", config);
  return data;
};

export const getStrategyPerformance = async () => {
  const { data } = await api.get("/api/ai/autonomous/strategies");
  return data;
};

export const triggerManualScan = async () => {
  const { data } = await api.post("/api/ai/autonomous/scan");
  return data;
};

// ==================== Watchlist API ====================

export const fetchWatchlist = async () => {
  const { data } = await api.get("/api/ai/watchlist");
  return data;
};

export const addToWatchlist = async (symbols: string[]) => {
  const { data } = await api.post("/api/ai/watchlist/add", { symbols });
  return data;
};

export const removeFromWatchlist = async (symbols: string[]) => {
  const { data } = await api.post("/api/ai/watchlist/remove", { symbols });
  return data;
};

export const searchSymbols = async (query: string, limit: number = 15) => {
  const { data } = await api.get(`/api/ai/symbols/search?q=${encodeURIComponent(query)}&limit=${limit}`);
  return data;
};

export const validateSymbol = async (symbol: string) => {
  const { data } = await api.get(`/api/ai/symbols/validate?symbol=${encodeURIComponent(symbol)}`);
  return data;
};

export default api;
