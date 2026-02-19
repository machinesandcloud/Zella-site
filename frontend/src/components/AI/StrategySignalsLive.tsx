import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  Typography,
  Box,
  Stack,
  Chip,
  Grid,
  Avatar,
  LinearProgress,
  Tooltip
} from "@mui/material";
import {
  TrendingUp,
  TrendingDown,
  ShowChart,
  BubbleChart,
  Timeline,
  WaterDrop
} from "@mui/icons-material";

interface StrategySignal {
  strategy: string;
  symbol: string;
  action: "BUY" | "SELL";
  confidence: number;
  reason: string;
  timestamp: string;
}

interface StrategyStats {
  name: string;
  category: string;
  signals_today: number;
  win_rate: number;
  active: boolean;
}

const STRATEGY_CATEGORIES = {
  "Trend Following": ["breakout", "ema_cross", "momentum", "htf_ema_momentum", "trend_follow", "first_hour_trend"],
  "Mean Reversion": ["pullback", "range_trading", "rsi_exhaustion", "rsi_extreme_reversal", "vwap_bounce", "nine_forty_five_reversal"],
  "Scalping": ["scalping", "orb", "rip_and_dip", "big_bid_scalp"],
  "Pattern Recognition": ["retail_fakeout", "stop_hunt_reversal", "bagholder_bounce", "broken_parabolic_short", "fake_halt_trap"],
  "Institutional": ["closing_bell_liquidity_grab", "dark_pool_footprints", "market_maker_refill", "premarket_vwap_reclaim"]
};

const getCategoryIcon = (category: string) => {
  switch (category) {
    case "Trend Following":
      return <TrendingUp />;
    case "Mean Reversion":
      return <ShowChart />;
    case "Scalping":
      return <Timeline />;
    case "Pattern Recognition":
      return <BubbleChart />;
    case "Institutional":
      return <WaterDrop />;
    default:
      return <TrendingUp />;
  }
};

const StrategySignalsLive = () => {
  const [recentSignals, setRecentSignals] = useState<StrategySignal[]>([]);
  const [strategyStats, setStrategyStats] = useState<StrategyStats[]>([]);

  useEffect(() => {
    // Fetch real-time strategy signals from backend
    // For now, simulating with demo data
    const mockStats: StrategyStats[] = Object.entries(STRATEGY_CATEGORIES).flatMap(([category, strategies]) =>
      strategies.map(name => ({
        name,
        category,
        signals_today: Math.floor(Math.random() * 15),
        win_rate: 0.55 + Math.random() * 0.3,
        active: Math.random() > 0.3
      }))
    );
    setStrategyStats(mockStats);

    const interval = setInterval(() => {
      // Simulate new signals
      if (Math.random() > 0.7) {
        const categories = Object.keys(STRATEGY_CATEGORIES);
        const randomCategory = categories[Math.floor(Math.random() * categories.length)];
        const strategies = STRATEGY_CATEGORIES[randomCategory as keyof typeof STRATEGY_CATEGORIES];
        const randomStrategy = strategies[Math.floor(Math.random() * strategies.length)];

        const newSignal: StrategySignal = {
          strategy: randomStrategy,
          symbol: ["AAPL", "TSLA", "NVDA", "AMD", "MSFT", "GOOGL"][Math.floor(Math.random() * 6)],
          action: Math.random() > 0.5 ? "BUY" : "SELL",
          confidence: 0.6 + Math.random() * 0.35,
          reason: "Technical setup detected",
          timestamp: new Date().toISOString()
        };

        setRecentSignals(prev => [newSignal, ...prev].slice(0, 10));
      }
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const activeStrategies = strategyStats.filter(s => s.active).length;
  const totalSignalsToday = strategyStats.reduce((sum, s) => sum + s.signals_today, 0);
  const avgWinRate = strategyStats.length > 0
    ? strategyStats.reduce((sum, s) => sum + s.win_rate, 0) / strategyStats.length
    : 0;

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        {/* Header */}
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
          <Box>
            <Typography variant="h6" fontWeight="bold">
              Strategy Signals
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Real-time signals from {activeStrategies} active strategies
            </Typography>
          </Box>
          <Stack direction="row" spacing={1}>
            <Chip
              label={`${activeStrategies} Active`}
              color="success"
              size="small"
            />
            <Chip
              label={`${totalSignalsToday} Signals Today`}
              size="small"
            />
          </Stack>
        </Stack>

        {/* Overview Metrics */}
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={4}>
            <Box sx={{ p: 2, textAlign: "center", borderRadius: 2, bgcolor: "rgba(46, 125, 50, 0.1)" }}>
              <Typography variant="h5" fontWeight="bold" color="success.main">
                {activeStrategies}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Active Strategies
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={4}>
            <Box sx={{ p: 2, textAlign: "center", borderRadius: 2, bgcolor: "rgba(63, 208, 201, 0.1)" }}>
              <Typography variant="h5" fontWeight="bold" color="primary.main">
                {totalSignalsToday}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Signals Today
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={4}>
            <Box sx={{ p: 2, textAlign: "center", borderRadius: 2, bgcolor: "rgba(244, 199, 111, 0.1)" }}>
              <Typography variant="h5" fontWeight="bold" color="warning.main">
                {(avgWinRate * 100).toFixed(0)}%
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Avg Win Rate
              </Typography>
            </Box>
          </Grid>
        </Grid>

        {/* Live Signal Feed */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" fontWeight="bold" sx={{ mb: 2 }}>
            Live Signal Feed
          </Typography>
          {recentSignals.length > 0 ? (
            <Stack spacing={1} sx={{ maxHeight: 250, overflow: "auto" }}>
              {recentSignals.map((signal, idx) => (
                <Box
                  key={`${signal.symbol}-${signal.timestamp}-${idx}`}
                  sx={{
                    p: 2,
                    borderRadius: 2,
                    border: "1px solid rgba(255,255,255,0.06)",
                    background: signal.action === "BUY"
                      ? "linear-gradient(90deg, rgba(46, 125, 50, 0.08), rgba(46, 125, 50, 0.02))"
                      : "linear-gradient(90deg, rgba(211, 47, 47, 0.08), rgba(211, 47, 47, 0.02))",
                    animation: idx === 0 ? "slideIn 0.3s ease-out" : "none",
                    "@keyframes slideIn": {
                      from: {
                        opacity: 0,
                        transform: "translateX(-20px)"
                      },
                      to: {
                        opacity: 1,
                        transform: "translateX(0)"
                      }
                    }
                  }}
                >
                  <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Stack direction="row" spacing={2} alignItems="center">
                      <Avatar
                        sx={{
                          width: 36,
                          height: 36,
                          bgcolor: signal.action === "BUY" ? "success.main" : "error.main"
                        }}
                      >
                        {signal.action === "BUY" ? <TrendingUp /> : <TrendingDown />}
                      </Avatar>
                      <Box>
                        <Stack direction="row" spacing={1} alignItems="center">
                          <Typography variant="body2" fontWeight="bold">
                            {signal.symbol}
                          </Typography>
                          <Chip
                            label={signal.action}
                            size="small"
                            color={signal.action === "BUY" ? "success" : "error"}
                            sx={{ height: 20 }}
                          />
                          <Typography variant="caption" color="text.secondary">
                            {signal.strategy.replace(/_/g, " ")}
                          </Typography>
                        </Stack>
                        <Typography variant="caption" color="text.secondary">
                          {new Date(signal.timestamp).toLocaleTimeString()}
                        </Typography>
                      </Box>
                    </Stack>
                    <Box sx={{ textAlign: "right" }}>
                      <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                        Confidence
                      </Typography>
                      <Typography variant="body2" fontWeight="bold" color={signal.confidence > 0.75 ? "success.main" : "warning.main"}>
                        {(signal.confidence * 100).toFixed(0)}%
                      </Typography>
                    </Box>
                  </Stack>
                </Box>
              ))}
            </Stack>
          ) : (
            <Box
              sx={{
                p: 3,
                textAlign: "center",
                borderRadius: 2,
                bgcolor: "rgba(255,255,255,0.02)",
                border: "1px dashed rgba(255,255,255,0.1)"
              }}
            >
              <Typography variant="body2" color="text.secondary">
                No signals yet. Strategies will generate signals when opportunities are found.
              </Typography>
            </Box>
          )}
        </Box>

        {/* Strategy Categories */}
        <Box>
          <Typography variant="subtitle2" fontWeight="bold" sx={{ mb: 2 }}>
            Strategy Categories
          </Typography>
          <Grid container spacing={2}>
            {Object.entries(STRATEGY_CATEGORIES).map(([category, strategies]) => {
              const categoryStats = strategyStats.filter(s => s.category === category);
              const categorySignals = categoryStats.reduce((sum, s) => sum + s.signals_today, 0);
              const categoryActive = categoryStats.filter(s => s.active).length;

              return (
                <Grid item xs={12} sm={6} key={category}>
                  <Tooltip
                    title={
                      <Box>
                        <Typography variant="caption" fontWeight="bold">
                          {category}
                        </Typography>
                        <Typography variant="caption" sx={{ display: "block" }}>
                          {categoryActive} / {strategies.length} strategies active
                        </Typography>
                      </Box>
                    }
                  >
                    <Box
                      sx={{
                        p: 2,
                        borderRadius: 2,
                        border: "1px solid rgba(255,255,255,0.08)",
                        bgcolor: "rgba(255,255,255,0.02)",
                        cursor: "pointer",
                        transition: "all 0.2s",
                        "&:hover": {
                          bgcolor: "rgba(255,255,255,0.04)",
                          borderColor: "primary.main"
                        }
                      }}
                    >
                      <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 1 }}>
                        <Avatar sx={{ width: 28, height: 28, bgcolor: "primary.main" }}>
                          {getCategoryIcon(category)}
                        </Avatar>
                        <Box sx={{ flex: 1 }}>
                          <Typography variant="body2" fontWeight="bold">
                            {category}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {categorySignals} signals today
                          </Typography>
                        </Box>
                        <Chip
                          label={categoryActive}
                          size="small"
                          color={categoryActive > 0 ? "success" : "default"}
                        />
                      </Stack>
                      <LinearProgress
                        variant="determinate"
                        value={(categoryActive / strategies.length) * 100}
                        sx={{
                          height: 4,
                          borderRadius: 2,
                          bgcolor: "rgba(255,255,255,0.05)"
                        }}
                      />
                    </Box>
                  </Tooltip>
                </Grid>
              );
            })}
          </Grid>
        </Box>
      </CardContent>
    </Card>
  );
};

export default StrategySignalsLive;
