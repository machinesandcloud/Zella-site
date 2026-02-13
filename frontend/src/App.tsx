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
import IBKRConnection from "./components/Settings/IBKRConnection";
import RiskSettings from "./components/Settings/RiskSettings";
import StrategyConfig from "./components/Settings/StrategyConfig";
import Login from "./components/Auth/Login";
import Register from "./components/Auth/Register";
import AutopilotControl from "./components/AI/AutopilotControl";
import AutonomyTimeline from "./components/AI/AutonomyTimeline";
import OptionsChain from "./components/Trading/OptionsChain";
import VoiceAssistantSettings from "./components/Settings/VoiceAssistantSettings";
import BacktestPanel from "./components/Trading/BacktestPanel";
import StrategyBuilder from "./components/Trading/StrategyBuilder";
import SystemHealth from "./components/Dashboard/SystemHealth";
import CalendarHeatmap from "./components/Dashboard/CalendarHeatmap";
import DailyBriefing from "./components/Dashboard/DailyBriefing";
import Onboarding from "./components/Auth/Onboarding";
import HelpCenter from "./components/Settings/HelpCenter";

const NAV = [
  { label: "Command Center", value: 0 },
  { label: "Trading", value: 1 },
  { label: "Analytics", value: 2 },
  { label: "Settings", value: 3 },
  { label: "Access", value: 4 }
];

const App = () => {
  const [tab, setTab] = useState(0);
  const [authRequired, setAuthRequired] = useState(false);
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
                <Typography variant="h5">Zella AI Command Center</Typography>
                <Typography variant="body2" color="text.secondary">
                  Autonomous trading, always-on risk intelligence
                </Typography>
              </Box>
            </Stack>
            <Stack direction="row" spacing={1} alignItems="center">
              <Chip label="Paper Mode" color="secondary" size="small" />
              <Chip label="IBKR Mock" size="small" />
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
              Session expired. Please log in again in the Access tab.
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
                <Grid item xs={12}>
                  <Overview />
                </Grid>
                <Grid item xs={12} md={7}>
                  <AutopilotControl />
                </Grid>
                <Grid item xs={12} md={5}>
                  <SystemHealth />
                </Grid>
                <Grid item xs={12}>
                  <AutonomyTimeline />
                </Grid>
                <Grid item xs={12} md={6}>
                  <RiskDashboard />
                </Grid>
                <Grid item xs={12} md={6}>
                  <PerformanceMetrics />
                </Grid>
                <Grid item xs={12}>
                  <DailyBriefing />
                </Grid>
                <Grid item xs={12} md={7}>
                  <ActivePositions />
                </Grid>
                <Grid item xs={12} md={5}>
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
                  <IBKRConnection />
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

            {tab === 4 && (
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <Login />
                </Grid>
                <Grid item xs={12} md={6}>
                  <Register />
                </Grid>
                <Grid item xs={12}>
                  <Onboarding />
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
