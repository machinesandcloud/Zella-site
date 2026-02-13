import { useState } from "react";
import {
  Box,
  Chip,
  Container,
  Grid,
  IconButton,
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
import IBKRConnection from "./components/Settings/IBKRConnection";
import RiskSettings from "./components/Settings/RiskSettings";
import StrategyConfig from "./components/Settings/StrategyConfig";
import Login from "./components/Auth/Login";
import Register from "./components/Auth/Register";
import AutopilotControl from "./components/AI/AutopilotControl";
import OptionsChain from "./components/Trading/OptionsChain";
import VoiceAssistantSettings from "./components/Settings/VoiceAssistantSettings";
import BacktestPanel from "./components/Trading/BacktestPanel";
import StrategyBuilder from "./components/Trading/StrategyBuilder";
import SystemHealth from "./components/Dashboard/SystemHealth";
import CalendarHeatmap from "./components/Dashboard/CalendarHeatmap";
import Onboarding from "./components/Auth/Onboarding";
import HelpCenter from "./components/Settings/HelpCenter";

const NAV = [
  { label: "Command", value: 0 },
  { label: "Trading", value: 1 },
  { label: "AI Autopilot", value: 2 },
  { label: "Settings", value: 3 },
  { label: "Access", value: 4 }
];

const App = () => {
  const [tab, setTab] = useState(0);

  return (
    <Box sx={{ minHeight: "100vh", pb: 6 }}>
      <Box
        sx={{
          position: "sticky",
          top: 0,
          zIndex: 10,
          backdropFilter: "blur(18px)",
          background: "rgba(8, 12, 18, 0.85)",
          borderBottom: "1px solid rgba(255,255,255,0.06)"
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
                  fontWeight: 700
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
              <Chip label="Paper" color="secondary" size="small" />
              <Chip label="IBKR Mock" size="small" />
              <Button variant="contained">Deploy Report</Button>
              <IconButton sx={{ border: "1px solid rgba(255,255,255,0.08)" }}>
                ⚙️
              </IconButton>
            </Stack>
          </Stack>
        </Container>
      </Box>

      <Container maxWidth="xl" sx={{ mt: 4 }}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={2.5}>
            <Box
              sx={{
                p: 2,
                borderRadius: 3,
                border: "1px solid rgba(255,255,255,0.08)",
                background: "rgba(14, 18, 28, 0.6)",
                boxShadow: "0 18px 40px rgba(5, 10, 20, 0.35)",
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
                    variant={tab === item.value ? "contained" : "text"}
                    color={tab === item.value ? "primary" : "inherit"}
                    onClick={() => setTab(item.value)}
                    sx={{ justifyContent: "flex-start" }}
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
                <Grid item xs={12}>
                  <SystemHealth />
                </Grid>
                <Grid item xs={12} md={7}>
                  <ActivePositions />
                </Grid>
                <Grid item xs={12} md={5}>
                  <PerformanceMetrics />
                </Grid>
                <Grid item xs={12}>
                  <EquityCurve />
                </Grid>
                <Grid item xs={12}>
                  <PerformanceAnalytics />
                </Grid>
                <Grid item xs={12}>
                  <CalendarHeatmap />
                </Grid>
                <Grid item xs={12}>
                  <RiskDashboard />
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

            {tab === 1 && (
              <Grid container spacing={3}>
                <Grid item xs={12} md={8}>
                  <ChartView />
                </Grid>
                <Grid item xs={12} md={4}>
                  <Watchlist />
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
                  <AutopilotControl />
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
    </Box>
  );
};

export default App;
