import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";

// Check if VITE_API_URL is explicitly set (not undefined, not empty)
const API_URL = import.meta.env.VITE_API_URL?.trim();
const hasExplicitApiUrl = API_URL !== undefined && API_URL !== "";

// Use localhost:8000 as default for development
const baseURL = hasExplicitApiUrl ? API_URL : "http://localhost:8000";

// Debug: Log API configuration (will show in browser console)
console.log("[API Config]", {
  VITE_API_URL: import.meta.env.VITE_API_URL,
  hasExplicitApiUrl,
  baseURL,
  MODE: import.meta.env.MODE,
  PROD: import.meta.env.PROD
});

// Only use fast timeout when explicitly set to empty string (Netlify demo mode)
const isNetlifyDemoMode = import.meta.env.VITE_API_URL === "";
const timeout = isNetlifyDemoMode ? 1000 : 30000;

// Retry configuration
const MAX_RETRIES = 3;
const RETRY_DELAY_BASE = 1000; // 1 second base delay

// Helper to check if error is retryable
const isRetryableError = (error: AxiosError): boolean => {
  // Network errors (no response)
  if (!error.response) return true;

  // Server errors (5xx) are often transient
  const status = error.response.status;
  if (status >= 500 && status < 600) return true;

  // Rate limiting
  if (status === 429) return true;

  // Connection timeout
  if (error.code === "ECONNABORTED") return true;

  return false;
};

// Helper for exponential backoff delay
const getRetryDelay = (retryCount: number): number => {
  // Exponential backoff: 1s, 2s, 4s with jitter
  const delay = RETRY_DELAY_BASE * Math.pow(2, retryCount);
  const jitter = Math.random() * 500; // Add 0-500ms jitter
  return delay + jitter;
};

const api = axios.create({
  baseURL,
  headers: {
    "Content-Type": "application/json"
  },
  timeout
});

// Extend config type to track retries
interface RetryConfig extends InternalAxiosRequestConfig {
  __retryCount?: number;
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("zella_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetryConfig;

    // Handle 401 unauthorized
    if (error?.response?.status === 401) {
      localStorage.removeItem("zella_token");
      window.dispatchEvent(new Event("auth:logout"));
      return Promise.reject(error);
    }

    // Check if we should retry
    if (!config || !isRetryableError(error)) {
      return Promise.reject(error);
    }

    // Initialize or increment retry count
    config.__retryCount = config.__retryCount ?? 0;

    // Check if we've exceeded max retries
    if (config.__retryCount >= MAX_RETRIES) {
      console.warn(`[API] Max retries (${MAX_RETRIES}) exceeded for ${config.url}`);
      return Promise.reject(error);
    }

    config.__retryCount += 1;

    // Calculate delay
    const delay = getRetryDelay(config.__retryCount - 1);
    console.log(`[API] Retry ${config.__retryCount}/${MAX_RETRIES} for ${config.url} in ${Math.round(delay)}ms`);

    // Wait and retry
    await new Promise((resolve) => setTimeout(resolve, delay));

    return api(config);
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

export const liquidateAllPositions = async () => {
  const { data } = await api.post("/api/ai/autonomous/liquidate-all");
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

export const fetchWatchlistSnapshots = async (symbols?: string[]) => {
  const params = symbols ? `?symbols=${symbols.join(",")}` : "";
  const { data } = await api.get(`/api/ai/watchlist/snapshots${params}`);
  return data;
};

// ==================== Strategy Performance API ====================

export const fetchStrategyPerformanceByPeriod = async () => {
  const { data } = await api.get("/api/trades/strategy-performance");
  return data;
};

export const fetchTradesByStrategy = async (strategyName: string, limit: number = 50) => {
  const { data } = await api.get(`/api/trades/by-strategy/${encodeURIComponent(strategyName)}?limit=${limit}`);
  return data;
};

export const fetchAvailableStrategies = async () => {
  const { data } = await api.get("/api/trades/strategies");
  return data;
};

// ==================== Health Check API ====================

export const checkHealth = async (): Promise<{
  status: string;
  service: string;
  components: Record<string, unknown>;
}> => {
  const { data } = await api.get("/health", { timeout: 5000 }); // Short timeout for health checks
  return data;
};

// Connection status tracking
let connectionListeners: ((connected: boolean) => void)[] = [];
let lastConnectionState = true;

export const onConnectionChange = (callback: (connected: boolean) => void) => {
  connectionListeners.push(callback);
  return () => {
    connectionListeners = connectionListeners.filter((cb) => cb !== callback);
  };
};

const notifyConnectionChange = (connected: boolean) => {
  if (connected !== lastConnectionState) {
    lastConnectionState = connected;
    connectionListeners.forEach((cb) => cb(connected));
    window.dispatchEvent(new CustomEvent("connection:change", { detail: { connected } }));
  }
};

// Start periodic health monitoring (every 30 seconds)
let healthCheckInterval: ReturnType<typeof setInterval> | null = null;

export const startHealthMonitoring = () => {
  if (healthCheckInterval) return;

  const doHealthCheck = async () => {
    try {
      await checkHealth();
      notifyConnectionChange(true);
    } catch {
      console.warn("[API] Health check failed - connection may be lost");
      notifyConnectionChange(false);
    }
  };

  // Initial check
  doHealthCheck();

  // Periodic checks
  healthCheckInterval = setInterval(doHealthCheck, 30000);
};

export const stopHealthMonitoring = () => {
  if (healthCheckInterval) {
    clearInterval(healthCheckInterval);
    healthCheckInterval = null;
  }
};

export default api;
