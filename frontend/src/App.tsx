import { useState } from "react";
import { Box, Container, Grid, Tab, Tabs, Typography } from "@mui/material";
import Overview from "./components/Dashboard/Overview";
import ActivePositions from "./components/Dashboard/ActivePositions";
import TradeHistory from "./components/Dashboard/TradeHistory";
import PerformanceMetrics from "./components/Dashboard/PerformanceMetrics";
import RiskDashboard from "./components/Dashboard/RiskDashboard";
import NotificationCenter from "./components/Dashboard/NotificationCenter";
import ChartView from "./components/Trading/ChartView";
import EquityCurve from "./components/Dashboard/EquityCurve";
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
import BacktestPanel from "./components/Trading/BacktestPanel";

const App = () => {
  const [tab, setTab] = useState(0);

  return (
    <Box sx={{ minHeight: "100vh", pb: 6 }}>
      <Box
        sx={{
          background: "linear-gradient(120deg, #fff7ed, #f8fafc)",
          borderBottom: "1px solid var(--border)",
          mb: 4
        }}
      >
        <Container maxWidth="lg" sx={{ py: 4 }}>
          <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
            Zella AI Trading Command Center
          </Typography>
          <Typography color="text.secondary">
            Paper-first automation with risk controls and real-time monitoring.
          </Typography>
        </Container>
      </Box>

      <Container maxWidth="lg">
        <Tabs value={tab} onChange={(_, value) => setTab(value)} sx={{ mb: 3 }}>
          <Tab label="Dashboard" />
          <Tab label="Trading" />
          <Tab label="AI Autopilot" />
          <Tab label="Settings" />
          <Tab label="Auth" />
        </Tabs>

        {tab === 0 && (
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Overview />
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
              <RiskDashboard />
            </Grid>
            <Grid item xs={12}>
              <NotificationCenter />
            </Grid>
            <Grid item xs={12}>
              <TradeHistory />
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
          </Grid>
        )}
      </Container>
    </Box>
  );
};

export default App;
