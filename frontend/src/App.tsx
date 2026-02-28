import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Chip,
  Container,
  Grid,
  Snackbar,
  Stack,
  Typography,
  Button
} from "@mui/material";
import Overview from "./components/Dashboard/Overview";
import ActivePositions from "./components/Dashboard/ActivePositions";
import TradeHistory from "./components/Dashboard/TradeHistory";
import PerformanceMetrics from "./components/Dashboard/PerformanceMetrics";
import AlpacaConnection from "./components/Settings/AlpacaConnection";
import RiskSettings from "./components/Settings/RiskSettings";
import { autoLogin, fetchAlpacaStatus, fetchIbkrDefaults } from "./services/api";
import AutopilotControl from "./components/AI/AutopilotControl";
import SystemHealth from "./components/Dashboard/SystemHealth";
import BotLogs from "./components/AI/BotLogs";
import WatchlistManager from "./components/Dashboard/WatchlistManager";
import StrategyPerformancePanel from "./components/AI/StrategyPerformancePanel";

// Navigation tabs
const NAV = [
  { label: "Dashboard", value: 0 },
  { label: "Bot Logs", value: 1 },
  { label: "Trade History", value: 2 },
  { label: "Settings", value: 3 }
];

// Backend wake-up configuration for Render
const MAX_WAKE_RETRIES = 6;
const WAKE_RETRY_INTERVAL = 10000;

const App = () => {
  const [tab, setTab] = useState(0);
  const [authRequired, setAuthRequired] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(() => !!localStorage.getItem("zella_token"));
  const [ibkrDefaults, setIbkrDefaults] = useState<{
    is_paper_trading: boolean;
    use_mock_ibkr: boolean;
    use_ibkr_webapi: boolean;
    use_free_data: boolean;
    use_alpaca?: boolean;
  }>({
    is_paper_trading: true,
    use_mock_ibkr: true,
    use_ibkr_webapi: false,
    use_free_data: true,
    use_alpaca: false
  });
  const [alpacaStatus, setAlpacaStatus] = useState<{
    enabled: boolean;
    connected?: boolean;
    mode?: string;
  } | null>(null);
  const [toast, setToast] = useState<{ open: boolean; message: string; severity: "success" | "info" | "warning" | "error" }>({
    open: false,
    message: "",
    severity: "info"
  });
  const [backendConnected, setBackendConnected] = useState(false);
  const [isWakingUp, setIsWakingUp] = useState(true);
  const [wakeAttempt, setWakeAttempt] = useState(0);

  useEffect(() => {
    const logoutHandler = () => {
      setAuthRequired(true);
      setIsAuthenticated(false);
    };
    const loginHandler = () => {
      setIsAuthenticated(true);
      setAuthRequired(false);
    };
    window.addEventListener("auth:logout", logoutHandler);
    window.addEventListener("auth:login", loginHandler);
    return () => {
      window.removeEventListener("auth:logout", logoutHandler);
      window.removeEventListener("auth:login", loginHandler);
    };
  }, []);

  // Auto-login with retry logic for Render cold starts
  useEffect(() => {
    const token = localStorage.getItem("zella_token");
    if (token) {
      setIsAuthenticated(true);
      setIsWakingUp(false);
      setBackendConnected(true);
      return;
    }

    let cancelled = false;
    let attempt = 0;

    const tryConnect = async () => {
      if (cancelled) return;

      attempt++;
      setWakeAttempt(attempt);
      console.log(`[Auth] Auto-login attempt ${attempt}/${MAX_WAKE_RETRIES}`);

      try {
        const data = await autoLogin();
        if (cancelled) return;

        console.log("[Auth] Auto-login response:", data);

        if (data?.access_token) {
          localStorage.setItem("zella_token", data.access_token);
          setIsAuthenticated(true);
          setBackendConnected(true);
          setIsWakingUp(false);
          window.dispatchEvent(new CustomEvent("auth:login"));
          console.log("[Auth] Auto-login successful");
        }
      } catch (error) {
        console.error("[Auth] Auto-login error:", error);
        if (cancelled) return;

        if (attempt < MAX_WAKE_RETRIES) {
          console.log(`[Auth] Retrying in ${WAKE_RETRY_INTERVAL / 1000}s...`);
          setTimeout(tryConnect, WAKE_RETRY_INTERVAL);
        } else {
          console.error("[Auth] All retries exhausted, marking backend as offline");
          setBackendConnected(false);
          setIsWakingUp(false);
        }
      }
    };

    tryConnect();

    return () => {
      cancelled = true;
    };
  }, []);

  // Re-authenticate when auth is required
  useEffect(() => {
    if (!authRequired) return;
    autoLogin()
      .then((data) => {
        if (data?.access_token) {
          localStorage.setItem("zella_token", data.access_token);
          setAuthRequired(false);
          setIsAuthenticated(true);
          setBackendConnected(true);
          window.dispatchEvent(new CustomEvent("auth:login"));
        }
      })
      .catch(() => undefined);
  }, [authRequired]);

  // Fetch IBKR defaults after authenticated
  useEffect(() => {
    if (!isAuthenticated) return;
    fetchIbkrDefaults()
      .then((data) => {
        setIbkrDefaults(data);
        setBackendConnected(true);
      })
      .catch((error) => {
        console.warn("Backend not available, using defaults:", error.message);
        setBackendConnected(false);
      });
  }, [isAuthenticated]);

  // Fetch Alpaca status after authenticated
  useEffect(() => {
    if (!isAuthenticated) return;
    let cancelled = false;
    const loadStatus = () =>
      fetchAlpacaStatus()
        .then((data) => {
          if (!cancelled) setAlpacaStatus(data);
        })
        .catch(() => {
          if (!cancelled) setAlpacaStatus({ enabled: false });
        });
    loadStatus();
    const timer = window.setInterval(loadStatus, 30000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [isAuthenticated]);

  useEffect(() => {
    const toastHandler = (event: Event) => {
      const detail = (event as CustomEvent).detail || {};
      setToast({
        open: true,
        message: detail.message || "Action completed.",
        severity: detail.severity || "info"
      });
    };
    window.addEventListener("app:toast", toastHandler as EventListener);
    return () => {
      window.removeEventListener("app:toast", toastHandler as EventListener);
    };
  }, []);

  return (
    <Box sx={{ minHeight: "100vh", pb: 6 }}>
      {/* Header */}
      <Box
        sx={{
          position: "sticky",
          top: 0,
          zIndex: 10,
          backdropFilter: "blur(18px)",
          background: "linear-gradient(120deg, rgba(10, 15, 22, 0.95), rgba(16, 22, 34, 0.85))",
          borderBottom: "1px solid rgba(255,255,255,0.08)"
        }}
      >
        <Container maxWidth="lg" sx={{ py: 2 }}>
          <Stack direction="row" alignItems="center" spacing={2} justifyContent="space-between">
            <Stack direction="row" alignItems="center" spacing={2}>
              <Box
                sx={{
                  width: 42,
                  height: 42,
                  borderRadius: "14px",
                  background: "linear-gradient(135deg, #3fd0c9, #f4c76f)",
                  display: "grid",
                  placeItems: "center",
                  color: "#0b0f17",
                  fontWeight: 700,
                  fontSize: "1.2rem"
                }}
              >
                Z
              </Box>
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 600 }}>Zella AI</Typography>
                <Typography variant="caption" color="text.secondary">
                  Autonomous Day Trader
                </Typography>
              </Box>
            </Stack>
            <Stack direction="row" spacing={1} alignItems="center">
              <Chip
                label={ibkrDefaults.is_paper_trading ? "Paper" : "Live"}
                color={ibkrDefaults.is_paper_trading ? "secondary" : "success"}
                size="small"
              />
              {alpacaStatus?.connected && (
                <Chip label="Connected" color="success" size="small" variant="outlined" />
              )}
            </Stack>
          </Stack>
        </Container>
      </Box>

      <Container maxWidth="lg" sx={{ mt: 3 }}>
        {/* Wake-up indicator */}
        {isWakingUp && (
          <Box
            sx={{
              mb: 2,
              p: 2,
              borderRadius: 2,
              border: "1px solid rgba(59, 130, 246, 0.3)",
              background: "rgba(59, 130, 246, 0.1)"
            }}
          >
            <Stack direction="row" alignItems="center" spacing={2}>
              <Box
                sx={{
                  width: 16,
                  height: 16,
                  border: "2px solid rgba(59, 130, 246, 0.3)",
                  borderTop: "2px solid #3b82f6",
                  borderRadius: "50%",
                  animation: "spin 1s linear infinite",
                  "@keyframes spin": {
                    "0%": { transform: "rotate(0deg)" },
                    "100%": { transform: "rotate(360deg)" }
                  }
                }}
              />
              <Typography variant="body2">
                Connecting to server... ({wakeAttempt}/{MAX_WAKE_RETRIES})
              </Typography>
            </Stack>
          </Box>
        )}

        {/* Backend disconnected warning */}
        {!backendConnected && !isWakingUp && (
          <Box
            sx={{
              mb: 2,
              p: 2,
              borderRadius: 2,
              border: "1px solid rgba(255,184,77,0.3)",
              background: "rgba(255, 184, 77, 0.1)"
            }}
          >
            <Stack direction="row" alignItems="center" spacing={1}>
              <Typography variant="body2">Backend offline</Typography>
              <Button
                size="small"
                variant="outlined"
                onClick={() => window.location.reload()}
                sx={{ ml: 1, textTransform: "none" }}
              >
                Retry
              </Button>
            </Stack>
          </Box>
        )}

        {/* Tab navigation */}
        <Stack direction="row" spacing={1} sx={{ mb: 3 }}>
          {NAV.map((item) => (
            <Button
              key={item.value}
              variant={tab === item.value ? "contained" : "outlined"}
              onClick={() => setTab(item.value)}
              sx={{
                textTransform: "none",
                borderRadius: 2,
                px: 3
              }}
            >
              {item.label}
            </Button>
          ))}
        </Stack>

        {/* Tab Content - Only render after authentication */}
        {!isAuthenticated ? (
          <Box sx={{ textAlign: "center", py: 8 }}>
            <Typography color="text.secondary">
              {isWakingUp ? "Authenticating..." : "Please wait..."}
            </Typography>
          </Box>
        ) : (
          <>
            {tab === 0 && (
              <Grid container spacing={3}>
                {/* Main Control - Start/Stop Bot */}
                <Grid item xs={12} md={8}>
                  <AutopilotControl />
                </Grid>

                {/* System Status */}
                <Grid item xs={12} md={4}>
                  <SystemHealth />
                </Grid>

                {/* Active Positions */}
                <Grid item xs={12} md={8}>
                  <ActivePositions />
                </Grid>

                {/* Account Overview */}
                <Grid item xs={12} md={4}>
                  <Overview />
                </Grid>

                {/* Performance */}
                <Grid item xs={12}>
                  <PerformanceMetrics />
                </Grid>
              </Grid>
            )}

            {tab === 1 && (
              <Grid container spacing={3}>
                <Grid item xs={12}>
                  <BotLogs />
                </Grid>
              </Grid>
            )}

            {tab === 2 && (
              <Grid container spacing={3}>
                <Grid item xs={12}>
                  <StrategyPerformancePanel />
                </Grid>
                <Grid item xs={12}>
                  <TradeHistory />
                </Grid>
              </Grid>
            )}

            {tab === 3 && (
              <Grid container spacing={3}>
                <Grid item xs={12}>
                  <WatchlistManager />
                </Grid>
                <Grid item xs={12} md={6}>
                  <AlpacaConnection />
                </Grid>
                <Grid item xs={12} md={6}>
                  <RiskSettings />
                </Grid>
              </Grid>
            )}
          </>
        )}
      </Container>

      {/* Toast notifications */}
      <Snackbar
        open={toast.open}
        autoHideDuration={3000}
        onClose={() => setToast((prev) => ({ ...prev, open: false }))}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert
          severity={toast.severity}
          variant="filled"
          onClose={() => setToast((prev) => ({ ...prev, open: false }))}
          sx={{ borderRadius: 2 }}
        >
          {toast.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default App;
