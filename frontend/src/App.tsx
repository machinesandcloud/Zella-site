import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Chip,
  Container,
  Grid,
  IconButton,
  Snackbar,
  Stack,
  Typography,
  Button
} from "@mui/material";
import Overview from "./components/Dashboard/Overview";
import ActivePositions from "./components/Dashboard/ActivePositions";
import TradeHistory from "./components/Dashboard/TradeHistory";
import PerformanceMetrics from "./components/Dashboard/PerformanceMetrics";
import RiskDashboard from "./components/Dashboard/RiskDashboard";
import NotificationCenter from "./components/Dashboard/NotificationCenter";
import ChartView from "./components/Trading/ChartView";
import EquityCurve from "./components/Dashboard/EquityCurve";
import TradeJournal from "./components/Dashboard/TradeJournal";
import PerformanceAnalytics from "./components/Dashboard/PerformanceAnalytics";
import PortfolioAnalysis from "./components/Dashboard/PortfolioAnalysis";
import NewsFeed from "./components/Dashboard/NewsFeed";
import OrderEntry from "./components/Trading/OrderEntry";
import Watchlist from "./components/Trading/Watchlist";
import StrategyControlPanel from "./components/Trading/StrategyControlPanel";
import AIMarketScanner from "./components/Trading/AIMarketScanner";
import OrderBook from "./components/Trading/OrderBook";
import TimeSales from "./components/Trading/TimeSales";
import OrderGrid from "./components/Trading/OrderGrid";
import PremarketChecklist from "./components/Trading/PremarketChecklist";
import AlpacaConnection from "./components/Settings/AlpacaConnection";
import RiskSettings from "./components/Settings/RiskSettings";
import StrategyConfig from "./components/Settings/StrategyConfig";
import { autoLogin, fetchAlpacaStatus, fetchIbkrDefaults } from "./services/api";
import AutopilotControl from "./components/AI/AutopilotControl";
import AutonomyTimeline from "./components/AI/AutonomyTimeline";
import AutonomousScannerLive from "./components/AI/AutonomousScannerLive";
import StrategySignalsLive from "./components/AI/StrategySignalsLive";
import OpportunityPipeline from "./components/AI/OpportunityPipeline";
import OptionsChain from "./components/Trading/OptionsChain";
import VoiceAssistantSettings from "./components/Settings/VoiceAssistantSettings";
import BacktestPanel from "./components/Trading/BacktestPanel";
import StrategyBuilder from "./components/Trading/StrategyBuilder";
import SystemHealth from "./components/Dashboard/SystemHealth";
import CalendarHeatmap from "./components/Dashboard/CalendarHeatmap";
import DailyBriefing from "./components/Dashboard/DailyBriefing";
import HelpCenter from "./components/Settings/HelpCenter";

const NAV = [
  { label: "🤖 Autonomous Trading", value: 0 },
  { label: "Manual Trading", value: 1 },
  { label: "Analytics", value: 2 },
  { label: "Settings", value: 3 }
];

const App = () => {
  const [tab, setTab] = useState(0);
  const [authRequired, setAuthRequired] = useState(false);
  const [ibkrDefaults, setIbkrDefaults] = useState<{
    is_paper_trading: boolean;
    use_mock_ibkr: boolean;
    use_ibkr_webapi: boolean;
    use_free_data: boolean;
    use_alpaca?: boolean;
  } | null>(null);
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

  useEffect(() => {
    const handler = () => setAuthRequired(true);
    window.addEventListener("auth:logout", handler);
    return () => window.removeEventListener("auth:logout", handler);
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("zella_token");
    if (token) return;
    autoLogin()
      .then((data) => {
        if (data?.access_token) {
          localStorage.setItem("zella_token", data.access_token);
          window.dispatchEvent(new CustomEvent("auth:login"));
        }
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!authRequired) return;
    autoLogin()
      .then((data) => {
        if (data?.access_token) {
          localStorage.setItem("zella_token", data.access_token);
          setAuthRequired(false);
          window.dispatchEvent(new CustomEvent("auth:login"));
        }
      })
      .catch(() => undefined);
  }, [authRequired]);

  useEffect(() => {
    fetchIbkrDefaults()
      .then((data) => setIbkrDefaults(data))
      .catch((error) => {
        console.warn("Backend not available, using defaults:", error.message);
        setIbkrDefaults({
          is_paper_trading: true,
          use_mock_ibkr: true,
          use_ibkr_webapi: false,
          use_free_data: true,
          use_alpaca: false
        });
      });
  }, []);

  useEffect(() => {
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
  }, []);

  useEffect(() => {
    const toastHandler = (event: Event) => {
      const detail = (event as CustomEvent).detail || {};
      setToast({
        open: true,
        message: detail.message || "Action queued.",
        severity: detail.severity || "info"
      });
    };
    const navHandler = (event: Event) => {
      const detail = (event as CustomEvent).detail || {};
      if (typeof detail.tab === "number") {
        setTab(detail.tab);
      }
    };
    window.addEventListener("app:toast", toastHandler as EventListener);
    window.addEventListener("app:navigate", navHandler as EventListener);
    return () => {
      window.removeEventListener("app:toast", toastHandler as EventListener);
      window.removeEventListener("app:navigate", navHandler as EventListener);
    };
  }, []);

  return (
    <Box sx={{ minHeight: "100vh", pb: 6 }}>
      <Box
        sx={{
          position: "sticky",
          top: 0,
          zIndex: 10,
          backdropFilter: "blur(18px)",
          background:
            "linear-gradient(120deg, rgba(10, 15, 22, 0.92), rgba(16, 22, 34, 0.78))",
          borderBottom: "1px solid rgba(255,255,255,0.08)"
        }}
      >
        <Container maxWidth="xl" sx={{ py: 2 }}>
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
                  boxShadow: "0 12px 28px rgba(20, 196, 184, 0.3)"
                }}
              >
                Z
              </Box>
              <Box>
                <Typography variant="h5">Zella AI Trading Platform</Typography>
                <Typography variant="body2" color="text.secondary">
                  Fully Autonomous Trading • 25+ Strategies • Real-Time Intelligence
                </Typography>
              </Box>
            </Stack>
            <Stack direction="row" spacing={1} alignItems="center">
              {ibkrDefaults ? (
                <Chip
                  label={ibkrDefaults.is_paper_trading ? "Paper Mode" : "Live Mode"}
                  color={ibkrDefaults.is_paper_trading ? "secondary" : "success"}
                  size="small"
                />
              ) : (
                <Chip label="Trading Mode" size="small" />
              )}
              {ibkrDefaults?.use_alpaca && <Chip label="Alpaca" size="small" />}
              {ibkrDefaults?.use_free_data && <Chip label="Free Data" size="small" />}
              {alpacaStatus?.enabled && (
                <Chip
                  label={alpacaStatus.connected ? "Alpaca Connected" : "Alpaca Disconnected"}
                  color={alpacaStatus.connected ? "success" : "warning"}
                  size="small"
                />
              )}
              <Button
                variant="contained"
                color="primary"
                onClick={() =>
                  window.dispatchEvent(
                    new CustomEvent("app:toast", {
                      detail: {
                        message: "Deployment report generated for this session.",
                        severity: "success"
                      }
                    })
                  )
                }
              >
                Deploy Report
              </Button>
              <IconButton
                sx={{ border: "1px solid rgba(255,255,255,0.12)" }}
                onClick={() =>
                  window.dispatchEvent(new CustomEvent("app:navigate", { detail: { tab: 3 } }))
                }
              >
                ⚙️
              </IconButton>
            </Stack>
          </Stack>
        </Container>
      </Box>

      <Container maxWidth="xl" sx={{ mt: 4 }}>
        {!ibkrDefaults && (
          <Box
            sx={{
              mb: 2,
              p: 2,
              borderRadius: 3,
              border: "1px solid rgba(255,184,77,0.3)",
              background: "rgba(255, 184, 77, 0.1)"
            }}
          >
            <Typography variant="body2" sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <span>⚠️</span>
              <span>
                Backend not connected - Running in demo mode. To enable full functionality, start the backend server.
              </span>
            </Typography>
          </Box>
        )}
        {authRequired && (
          <Box
            sx={{
              mb: 2,
              p: 2,
              borderRadius: 3,
              border: "1px solid rgba(255,255,255,0.08)",
              background: "rgba(255, 92, 92, 0.1)"
            }}
          >
            <Typography variant="body2">
              Session expired. Auto-login is retrying in the background.
            </Typography>
          </Box>
        )}
        <Grid container spacing={3}>
          <Grid item xs={12} md={2.5}>
            <Box
              sx={{
                p: 2,
                borderRadius: 3,
                border: "1px solid rgba(255,255,255,0.1)",
                background:
                  "linear-gradient(160deg, rgba(18, 24, 36, 0.92), rgba(9, 12, 20, 0.72))",
                boxShadow: "0 20px 50px rgba(4, 8, 18, 0.45)",
                position: "sticky",
                top: 96
              }}
            >
              <Typography variant="overline" color="text.secondary">
                Navigation
              </Typography>
              <Stack spacing={1} sx={{ mt: 1 }}>
                {NAV.map((item) => (
                  <Button
                    key={item.value}
                    variant="text"
                    color="inherit"
                    onClick={() => setTab(item.value)}
                    sx={{
                      justifyContent: "flex-start",
                      borderRadius: 2,
                      px: 2,
                      py: 1.2,
                      backgroundColor: tab === item.value ? "rgba(47, 227, 207, 0.15)" : "transparent",
                      border: tab === item.value ? "1px solid rgba(47, 227, 207, 0.35)" : "1px solid transparent",
                      color: tab === item.value ? "#e8edf6" : "text.secondary",
                      boxShadow: tab === item.value ? "0 12px 24px rgba(15, 135, 126, 0.2)" : "none"
                    }}
                  >
                    {item.label}
                  </Button>
                ))}
              </Stack>
            </Box>
          </Grid>

          <Grid item xs={12} md={9.5}>
            {tab === 0 && (
              <Grid container spacing={3}>
                {/* Autonomous Trading Control - Full Width */}
                <Grid item xs={12}>
                  <AutopilotControl />
                </Grid>

                {/* Real-Time Autonomous Monitoring - 3 Column Layout */}
                <Grid item xs={12} md={4}>
                  <AutonomousScannerLive />
                </Grid>
                <Grid item xs={12} md={4}>
                  <StrategySignalsLive />
                </Grid>
                <Grid item xs={12} md={4}>
                  <SystemHealth />
                </Grid>

                {/* Opportunity Pipeline - Full Width */}
                <Grid item xs={12}>
                  <OpportunityPipeline />
                </Grid>

                {/* Decision Timeline - Full Width */}
                <Grid item xs={12}>
                  <AutonomyTimeline />
                </Grid>

                {/* Portfolio Status */}
                <Grid item xs={12} md={8}>
                  <ActivePositions />
                </Grid>
                <Grid item xs={12} md={4}>
                  <Overview />
                </Grid>

                {/* Risk & Performance */}
                <Grid item xs={12} md={6}>
                  <RiskDashboard />
                </Grid>
                <Grid item xs={12} md={6}>
                  <PerformanceMetrics />
                </Grid>

                {/* Equity Curve */}
                <Grid item xs={12}>
                  <EquityCurve />
                </Grid>
              </Grid>
            )}

            {tab === 1 && (
              <Grid container spacing={3}>
                <Grid item xs={12} md={8}>
                  <ChartView />
                </Grid>
                <Grid item xs={12} md={4}>
                  <Watchlist />
                </Grid>
                <Grid item xs={12} md={4}>
                  <PremarketChecklist />
                </Grid>
                <Grid item xs={12} md={4}>
                  <OrderBook />
                </Grid>
                <Grid item xs={12} md={4}>
                  <TimeSales />
                </Grid>
                <Grid item xs={12} md={4}>
                  <OptionsChain />
                </Grid>
                <Grid item xs={12} md={4}>
                  <AIMarketScanner />
                </Grid>
                <Grid item xs={12} md={8}>
                  <OrderEntry />
                </Grid>
                <Grid item xs={12}>
                  <OrderGrid />
                </Grid>
                <Grid item xs={12}>
                  <BacktestPanel />
                </Grid>
                <Grid item xs={12}>
                  <StrategyBuilder />
                </Grid>
                <Grid item xs={12}>
                  <StrategyControlPanel />
                </Grid>
              </Grid>
            )}

            {tab === 2 && (
              <Grid container spacing={3}>
                <Grid item xs={12}>
                  <PerformanceAnalytics />
                </Grid>
                <Grid item xs={12}>
                  <CalendarHeatmap />
                </Grid>
                <Grid item xs={12}>
                  <PortfolioAnalysis />
                </Grid>
                <Grid item xs={12}>
                  <NewsFeed />
                </Grid>
                <Grid item xs={12}>
                  <NotificationCenter />
                </Grid>
                <Grid item xs={12}>
                  <TradeHistory />
                </Grid>
                <Grid item xs={12}>
                  <TradeJournal />
                </Grid>
              </Grid>
            )}

            {tab === 3 && (
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <AlpacaConnection />
                </Grid>
                <Grid item xs={12} md={6}>
                  <RiskSettings />
                </Grid>
                <Grid item xs={12} md={6}>
                  <VoiceAssistantSettings />
                </Grid>
                <Grid item xs={12} md={6}>
                  <HelpCenter />
                </Grid>
                <Grid item xs={12}>
                  <StrategyConfig />
                </Grid>
              </Grid>
            )}

          </Grid>
        </Grid>
      </Container>
      <Snackbar
        open={toast.open}
        autoHideDuration={3500}
        onClose={() => setToast((prev) => ({ ...prev, open: false }))}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert
          severity={toast.severity}
          variant="filled"
          onClose={() => setToast((prev) => ({ ...prev, open: false }))}
          sx={{ borderRadius: 2, alignItems: "center" }}
        >
          {toast.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default App;
