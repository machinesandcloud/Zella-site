import axios, { AxiosError, AxiosRequestConfig, InternalAxiosRequestConfig } from "axios";

// Check if VITE_API_URL is explicitly set (not undefined, not empty)
const API_URL = import.meta.env.VITE_API_URL?.trim();
const hasExplicitApiUrl = API_URL !== undefined && API_URL !== "";

// Use explicit API URL if provided; otherwise default to same-origin in prod
const defaultProdBaseURL =
  typeof window !== "undefined" ? window.location.origin : "http://localhost:8000";
const baseURL = hasExplicitApiUrl
  ? API_URL
  : import.meta.env.PROD
    ? defaultProdBaseURL
    : "http://localhost:8000";

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
  __skipRetry?: boolean;
  __startTime?: number;
}

type ApiTiming = {
  url: string;
  method: string;
  status: number | "ERR";
  durationMs: number;
  ts: number;
  ok: boolean;
};

type CacheEntry = {
  ts: number;
  data: unknown;
};

const TIMINGS_KEY = "zella_api_timings";
const MAX_TIMINGS = 50;
let timingBuffer: ApiTiming[] = [];

const loadTimings = () => {
  try {
    const stored = localStorage.getItem(TIMINGS_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      if (Array.isArray(parsed)) {
        timingBuffer = parsed;
      }
    }
  } catch {
    // ignore
  }
};

const recordTiming = (timing: ApiTiming) => {
  timingBuffer = [timing, ...timingBuffer].slice(0, MAX_TIMINGS);
  try {
    localStorage.setItem(TIMINGS_KEY, JSON.stringify(timingBuffer));
  } catch {
    // ignore storage errors
  }
  window.dispatchEvent(new CustomEvent("api:timing", { detail: timing }));
};

export const getApiTimings = () => {
  if (!timingBuffer.length) loadTimings();
  return timingBuffer.slice();
};

const cacheStore = new Map<string, CacheEntry>();
type CacheableConfig = AxiosRequestConfig & { __skipRetry?: boolean };

const cacheKeyFor = (url: string, config?: AxiosRequestConfig) => {
  const params = config?.params;
  if (!params) return `GET:${url}`;
  const entries = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null)
    .map(([k, v]) => [k, String(v)] as [string, string])
    .sort(([a], [b]) => a.localeCompare(b));
  const qs = new URLSearchParams(entries).toString();
  return `GET:${url}${qs ? `?${qs}` : ""}`;
};

const cacheKeyToStorage = (key: string) => `zella_cache_${encodeURIComponent(key)}`;

const readCache = (key: string): CacheEntry | null => {
  const mem = cacheStore.get(key);
  if (mem) return mem;
  try {
    const raw = localStorage.getItem(cacheKeyToStorage(key));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as CacheEntry;
    if (parsed && typeof parsed.ts === "number") {
      cacheStore.set(key, parsed);
      return parsed;
    }
  } catch {
    // ignore
  }
  return null;
};

const writeCache = (key: string, data: unknown) => {
  const entry: CacheEntry = { ts: Date.now(), data };
  cacheStore.set(key, entry);
  try {
    localStorage.setItem(cacheKeyToStorage(key), JSON.stringify(entry));
  } catch {
    // ignore
  }
};

const cachedGet = async <T = any>(
  url: string,
  config: CacheableConfig = {},
  opts: { ttlMs?: number; revalidate?: boolean } = {}
): Promise<T> => {
  const ttlMs = opts.ttlMs ?? 15000;
  const revalidate = opts.revalidate ?? true;
  const key = cacheKeyFor(url, config);
  const cached = readCache(key);

  if (cached) {
    const isFresh = Date.now() - cached.ts <= ttlMs;
    if (isFresh) {
      if (revalidate) {
        void api.get(url, { ...config, __skipRetry: true } as RetryConfig).then((res) => {
          writeCache(key, res.data);
        }).catch(() => {
          // ignore background errors
        });
      }
      return cached.data as T;
    }
  }

  const { data } = await api.get(url, config);
  writeCache(key, data);
  return data as T;
};

api.interceptors.request.use((config) => {
  (config as RetryConfig).__startTime = performance.now();
  const token = localStorage.getItem("zella_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => {
    // Any successful API response indicates backend is reachable.
    healthFailures = 0;
    notifyConnectionChange(true);
    const config = response.config as RetryConfig;
    const durationMs = config.__startTime ? Math.round(performance.now() - config.__startTime) : 0;
    recordTiming({
      url: config.url || "",
      method: (config.method || "get").toUpperCase(),
      status: response.status,
      durationMs,
      ts: Date.now(),
      ok: true
    });
    return response;
  },
  async (error: AxiosError) => {
    const config = error.config as RetryConfig;

    // Handle 401 unauthorized
    if (error?.response?.status === 401) {
      localStorage.removeItem("zella_token");
      window.dispatchEvent(new Event("auth:logout"));
      return Promise.reject(error);
    }

    // Check if we should retry
    if (!config || config.__skipRetry || !isRetryableError(error)) {
      const durationMs = config?.__startTime ? Math.round(performance.now() - config.__startTime) : 0;
      recordTiming({
        url: config?.url || "",
        method: (config?.method || "get").toUpperCase(),
        status: (error.response?.status ?? "ERR") as number | "ERR",
        durationMs,
        ts: Date.now(),
        ok: false
      });
      return Promise.reject(error);
    }

    // Initialize or increment retry count
    config.__retryCount = config.__retryCount ?? 0;

    // Check if we've exceeded max retries
    if (config.__retryCount >= MAX_RETRIES) {
      console.warn(`[API] Max retries (${MAX_RETRIES}) exceeded for ${config.url}`);
      const durationMs = config.__startTime ? Math.round(performance.now() - config.__startTime) : 0;
      recordTiming({
        url: config.url || "",
        method: (config.method || "get").toUpperCase(),
        status: (error.response?.status ?? "ERR") as number | "ERR",
        durationMs,
        ts: Date.now(),
        ok: false
      });
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
  return cachedGet("/api/dashboard/overview", {}, { ttlMs: 10000 });
};

export const fetchDashboardMetrics = async () => {
  return cachedGet("/api/dashboard/metrics", {}, { ttlMs: 10000 });
};

export const fetchRecentTrades = async (days: number = 7, limit: number = 50) => {
  return cachedGet("/api/dashboard/trades/recent", { params: { days, limit } }, { ttlMs: 10000 });
};

export const fetchAccountSnapshots = async () => {
  return cachedGet("/api/dashboard/account/snapshots", {}, { ttlMs: 15000 });
};

export const fetchTrades = async () => {
  return cachedGet("/api/trades", {}, { ttlMs: 15000 });
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
  return cachedGet("/api/alpaca/account", {}, { ttlMs: 5000 });
};

export const fetchAlpacaStatus = async () => {
  return cachedGet("/api/alpaca/status", {}, { ttlMs: 5000 });
};

export const fetchAlpacaAccount = async () => {
  return cachedGet("/api/alpaca/account", {}, { ttlMs: 5000 });
};

export const fetchAlpacaPositions = async () => {
  return cachedGet("/api/alpaca/positions", {}, { ttlMs: 5000 });
};

export const autoLogin = async () => {
  const { data } = await api.post("/api/auth/auto-login");
  return data;
};

export const fetchPositions = async () => {
  return cachedGet("/api/alpaca/positions", {}, { ttlMs: 5000 });
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
  return cachedGet(
    "/api/ai/autonomous/status",
    {
      timeout: 5000,
      __skipRetry: true
    } as RetryConfig,
    { ttlMs: 5000 }
  );
};

export const getAutonomousLogs = async () => {
  return cachedGet(
    "/api/ai/autonomous/logs",
    {
      timeout: 5000,
      __skipRetry: true
    } as RetryConfig,
    { ttlMs: 3000 }
  );
};

export const fetchLearningSummary = async () => {
  return cachedGet(
    "/api/ai/learning/summary",
    {
      timeout: 5000,
      __skipRetry: true
    } as RetryConfig,
    { ttlMs: 30000 }
  );
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
  return cachedGet("/api/trades/strategy-performance", {}, { ttlMs: 20000 });
};

export const fetchTradesByStrategy = async (strategyName: string, limit: number = 50) => {
  return cachedGet(
    `/api/trades/by-strategy/${encodeURIComponent(strategyName)}`,
    { params: { limit } },
    { ttlMs: 20000 }
  );
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

// Start periodic health monitoring
let healthCheckInterval: ReturnType<typeof setInterval> | null = null;
let quickRetryTimeout: ReturnType<typeof setTimeout> | null = null;
let healthFailures = 0;
const MAX_HEALTH_FAILURES = 3; // Require 3 failures before showing disconnected
const QUICK_RETRY_DELAY = 2000; // 2 seconds between quick retries
const HEALTH_CHECK_INTERVAL = 30000; // 30 seconds for normal checks

const doHealthCheck = async (): Promise<boolean> => {
  try {
    await checkHealth();
    healthFailures = 0;
    notifyConnectionChange(true);
    return true;
  } catch {
    healthFailures += 1;
    // Only log after first failure to reduce noise
    if (healthFailures === 1) {
      console.warn("[API] Health check failed - will retry");
    }
    // Only notify disconnected after multiple failures
    if (healthFailures >= MAX_HEALTH_FAILURES) {
      console.warn(`[API] ${healthFailures} consecutive health check failures - connection lost`);
      notifyConnectionChange(false);
    }
    // Quick retry on failure
    if (!quickRetryTimeout && healthFailures < MAX_HEALTH_FAILURES) {
      quickRetryTimeout = setTimeout(() => {
        quickRetryTimeout = null;
        void doHealthCheck();
      }, QUICK_RETRY_DELAY);
    }
    return false;
  }
};

export const forceHealthCheck = async (): Promise<boolean> => doHealthCheck();

export const startHealthMonitoring = () => {
  if (healthCheckInterval) return;

  // Initial check
  void doHealthCheck();

  // Periodic checks every 30 seconds (not too aggressive)
  healthCheckInterval = setInterval(() => {
    void doHealthCheck();
  }, HEALTH_CHECK_INTERVAL);
};

export const stopHealthMonitoring = () => {
  if (healthCheckInterval) {
    clearInterval(healthCheckInterval);
    healthCheckInterval = null;
  }
  if (quickRetryTimeout) {
    clearTimeout(quickRetryTimeout);
    quickRetryTimeout = null;
  }
};

export default api;
