import { useEffect, useState, useRef, useCallback, useMemo } from "react";
import {
  Card,
  CardContent,
  Grid,
  Stack,
  Typography,
  Box,
  Chip,
  LinearProgress,
  Tooltip,
  IconButton,
  Divider,
  Avatar,
  Badge,
  CircularProgress
} from "@mui/material";
import {
  Psychology,
  TrendingUp,
  TrendingDown,
  TrendingFlat,
  Speed,
  Refresh,
  Circle,
  ArrowForward,
  DataUsage,
  Memory,
  Hub,
  Insights,
  Analytics,
  AutoGraph,
  Bolt,
  Radar,
  Timeline,
  ShowChart,
  BarChart,
  Equalizer,
  Visibility,
  ExpandMore,
  ExpandLess
} from "@mui/icons-material";

// Strategy categories with icons and colors
const STRATEGY_CATEGORIES = {
  "Warrior Trading": {
    color: "#f59e0b",
    icon: "bolt",
    strategies: ["bull_flag", "flat_top_breakout", "orb"]
  },
  "Trend Following": {
    color: "#22c55e",
    icon: "trending_up",
    strategies: ["breakout", "ema_cross", "htf_ema_momentum", "momentum", "trend_follow", "first_hour_trend"]
  },
  "Mean Reversion": {
    color: "#3b82f6",
    icon: "autorenew",
    strategies: ["pullback", "range_trading", "rsi_exhaustion", "rsi_extreme_reversal", "vwap_bounce", "nine_forty_five_reversal"]
  },
  "Scalping": {
    color: "#ec4899",
    icon: "speed",
    strategies: ["scalping", "rip_and_dip", "big_bid_scalp"]
  },
  "Pattern Recognition": {
    color: "#8b5cf6",
    icon: "pattern",
    strategies: ["retail_fakeout", "stop_hunt_reversal", "bagholder_bounce", "broken_parabolic_short", "fake_halt_trap"]
  },
  "Smart Money": {
    color: "#06b6d4",
    icon: "account_balance",
    strategies: ["closing_bell_liquidity_grab", "dark_pool_footprints", "market_maker_refill", "premarket_vwap_reclaim"]
  }
};

interface StrategySignal {
  strategy: string;
  action: "BUY" | "SELL" | "HOLD";
  confidence: number;
  reason: string;
  indicators?: Record<string, number>;
}

interface AnalyzedOpportunity {
  symbol: string;
  price: number;
  signals: StrategySignal[];
  final_action: "BUY" | "SELL" | "HOLD";
  aggregate_confidence: number;
  reasoning: string;
  data?: {
    price: number;
    open: number;
    high: number;
    low: number;
    volume: number;
    relative_volume: number;
    volatility: number;
    atr_percent?: number;
    bid?: number;
    ask?: number;
    vwap?: number;
    prev_close?: number;
    rsi?: number;
    macd?: number;
    macd_signal?: number;
    ema_9?: number;
    ema_20?: number;
    sma_50?: number;
    bb_upper?: number;
    bb_lower?: number;
  };
}

interface BotState {
  running: boolean;
  mode: string;
  risk_posture: string;
  symbols_scanned: number;
  last_scan: string | null;
  active_strategies: string[];
  analyzed_opportunities: AnalyzedOpportunity[];
  current_analysis?: {
    symbol: string;
    stage: string;
    progress: number;
  };
}

// Animated number component
const AnimatedNumber = ({ value, decimals = 2, prefix = "", suffix = "", color = "#fff" }: {
  value: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  color?: string;
}) => {
  const [displayValue, setDisplayValue] = useState(value);

  useEffect(() => {
    const duration = 300;
    const startValue = displayValue;
    const diff = value - startValue;
    const startTime = Date.now();

    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayValue(startValue + diff * eased);

      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };

    requestAnimationFrame(animate);
  }, [value]);

  return (
    <Typography
      component="span"
      sx={{
        color,
        fontFamily: "'JetBrains Mono', monospace",
        fontWeight: 600,
        fontSize: "inherit"
      }}
    >
      {prefix}{displayValue.toFixed(decimals)}{suffix}
    </Typography>
  );
};

// Gauge component for indicators
const IndicatorGauge = ({ label, value, min, max, unit = "", zones, size = "medium" }: {
  label: string;
  value: number;
  min: number;
  max: number;
  unit?: string;
  zones?: { start: number; end: number; color: string }[];
  size?: "small" | "medium";
}) => {
  const percentage = Math.max(0, Math.min(100, ((value - min) / (max - min)) * 100));
  const gaugeSize = size === "small" ? 60 : 80;
  const strokeWidth = size === "small" ? 6 : 8;

  const getColor = () => {
    if (!zones) return "#3b82f6";
    for (const zone of zones) {
      if (value >= zone.start && value <= zone.end) return zone.color;
    }
    return "#64748b";
  };

  const circumference = 2 * Math.PI * (gaugeSize / 2 - strokeWidth);
  const strokeDashoffset = circumference - (percentage / 100) * circumference * 0.75;

  return (
    <Box sx={{ textAlign: "center", position: "relative" }}>
      <svg width={gaugeSize} height={gaugeSize * 0.75} style={{ overflow: "visible" }}>
        {/* Background arc */}
        <circle
          cx={gaugeSize / 2}
          cy={gaugeSize / 2}
          r={gaugeSize / 2 - strokeWidth}
          fill="none"
          stroke="rgba(255,255,255,0.1)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={`${circumference * 0.75} ${circumference * 0.25}`}
          transform={`rotate(135 ${gaugeSize / 2} ${gaugeSize / 2})`}
        />
        {/* Value arc */}
        <circle
          cx={gaugeSize / 2}
          cy={gaugeSize / 2}
          r={gaugeSize / 2 - strokeWidth}
          fill="none"
          stroke={getColor()}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          transform={`rotate(135 ${gaugeSize / 2} ${gaugeSize / 2})`}
          style={{
            transition: "stroke-dashoffset 0.5s ease, stroke 0.3s ease",
            filter: `drop-shadow(0 0 4px ${getColor()}40)`
          }}
        />
      </svg>
      <Box sx={{
        position: "absolute",
        bottom: size === "small" ? 0 : 5,
        left: "50%",
        transform: "translateX(-50%)",
        textAlign: "center"
      }}>
        <Typography
          variant={size === "small" ? "caption" : "body2"}
          fontWeight="bold"
          sx={{
            fontFamily: "'JetBrains Mono', monospace",
            color: getColor()
          }}
        >
          {value.toFixed(1)}{unit}
        </Typography>
      </Box>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
        {label}
      </Typography>
    </Box>
  );
};

// Mini sparkline component
const MiniSparkline = ({ data, color = "#3b82f6", width = 60, height = 20 }: {
  data: number[];
  color?: string;
  width?: number;
  height?: number;
}) => {
  if (data.length < 2) return null;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const points = data.map((val, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((val - min) / range) * height;
    return `${x},${y}`;
  }).join(" ");

  return (
    <svg width={width} height={height} style={{ overflow: "visible" }}>
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        style={{ filter: `drop-shadow(0 0 2px ${color}40)` }}
      />
    </svg>
  );
};

const UnderTheHood = () => {
  const [botState, setBotState] = useState<BotState | null>(null);
  const [connected, setConnected] = useState(false);
  const [updateCount, setUpdateCount] = useState(0);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [animatingStrategy, setAnimatingStrategy] = useState<string | null>(null);
  const [expandedOpportunity, setExpandedOpportunity] = useState<string | null>(null);
  const [priceHistory, setPriceHistory] = useState<Record<string, number[]>>({});
  const wsRef = useRef<WebSocket | null>(null);

  const getWebSocketUrl = useCallback(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = import.meta.env.VITE_API_URL?.replace(/^https?:\/\//, "") || "localhost:8000";
    return `${protocol}//${host}/ws/bot-activity`;
  }, []);

  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(getWebSocketUrl());

      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        setTimeout(connect, 2000);
      };
      ws.onerror = () => setConnected(false);

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === "status" && message.data) {
            setBotState(prev => ({
              ...prev,
              ...message.data,
              analyzed_opportunities: message.data.analyzed_opportunities || prev?.analyzed_opportunities || []
            }));
            setUpdateCount(c => c + 1);

            // Track price history for sparklines
            if (message.data.analyzed_opportunities) {
              setPriceHistory(prev => {
                const updated = { ...prev };
                message.data.analyzed_opportunities.forEach((opp: AnalyzedOpportunity) => {
                  if (opp.price) {
                    const history = updated[opp.symbol] || [];
                    updated[opp.symbol] = [...history.slice(-19), opp.price];
                  }
                });
                return updated;
              });
            }

            // Animate strategy when new signals come in
            if (message.data.new_decisions?.length > 0) {
              const strategies = message.data.new_decisions[0]?.strategies || [];
              if (strategies.length > 0) {
                setAnimatingStrategy(strategies[0]);
                setTimeout(() => setAnimatingStrategy(null), 1500);
              }
            }
          }
        } catch (e) {
          console.error("Error parsing bot activity:", e);
        }
      };

      wsRef.current = ws;
    };

    connect();
    return () => wsRef.current?.close();
  }, [getWebSocketUrl]);

  const getCategoryForStrategy = (strategyName: string) => {
    for (const [category, data] of Object.entries(STRATEGY_CATEGORIES)) {
      if (data.strategies.includes(strategyName)) {
        return { category, ...data };
      }
    }
    return { category: "Other", color: "#64748b", strategies: [] };
  };

  const formatStrategyName = (name: string) => {
    return name.split("_").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
  };

  const getSignalColor = (action: string) => {
    switch (action) {
      case "BUY": return "#22c55e";
      case "SELL": return "#ef4444";
      default: return "#64748b";
    }
  };

  // Aggregate data for the data crunch panel
  const aggregatedData = useMemo(() => {
    const opps = botState?.analyzed_opportunities || [];
    if (opps.length === 0) return null;

    const prices = opps.map(o => o.price).filter(Boolean);
    const volumes = opps.map(o => o.data?.volume || 0).filter(Boolean);
    const volatilities = opps.map(o => o.data?.volatility || 0).filter(Boolean);
    const rsis = opps.map(o => o.data?.rsi || 0).filter(v => v > 0);

    return {
      avgPrice: prices.length ? prices.reduce((a, b) => a + b, 0) / prices.length : 0,
      totalVolume: volumes.reduce((a, b) => a + b, 0),
      avgVolatility: volatilities.length ? volatilities.reduce((a, b) => a + b, 0) / volatilities.length : 0,
      avgRsi: rsis.length ? rsis.reduce((a, b) => a + b, 0) / rsis.length : 50,
      buySignals: opps.filter(o => o.final_action === "BUY").length,
      sellSignals: opps.filter(o => o.final_action === "SELL").length,
      holdSignals: opps.filter(o => o.final_action === "HOLD").length,
      totalConfidence: opps.reduce((sum, o) => sum + (o.aggregate_confidence || 0), 0) / opps.length
    };
  }, [botState?.analyzed_opportunities]);

  const selectedOpportunity = botState?.analyzed_opportunities?.find(o => o.symbol === selectedSymbol);

  return (
    <Card
      elevation={0}
      sx={{
        border: "1px solid var(--border)",
        background: "linear-gradient(180deg, rgba(10,15,25,0.95) 0%, rgba(5,10,18,0.98) 100%)",
        position: "relative",
        overflow: "hidden"
      }}
    >
      {/* Animated background grid */}
      <Box
        sx={{
          position: "absolute",
          inset: 0,
          backgroundImage: `
            linear-gradient(rgba(59, 130, 246, 0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(59, 130, 246, 0.03) 1px, transparent 1px)
          `,
          backgroundSize: "50px 50px",
          animation: "gridMove 20s linear infinite",
          "@keyframes gridMove": {
            "0%": { backgroundPosition: "0 0" },
            "100%": { backgroundPosition: "50px 50px" }
          }
        }}
      />

      {/* Scanning beam effect */}
      {botState?.running && (
        <Box
          sx={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: 2,
            background: "linear-gradient(90deg, transparent, #3b82f6, transparent)",
            animation: "scanBeam 2s ease-in-out infinite",
            "@keyframes scanBeam": {
              "0%": { transform: "translateX(-100%)" },
              "100%": { transform: "translateX(100%)" }
            }
          }}
        />
      )}

      <CardContent sx={{ position: "relative", zIndex: 1 }}>
        {/* Header */}
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 3 }}>
          <Stack direction="row" alignItems="center" spacing={2}>
            <Box
              sx={{
                width: 56,
                height: 56,
                borderRadius: 3,
                background: "linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 8px 32px rgba(59, 130, 246, 0.3)",
                animation: botState?.running ? "pulse 2s ease-in-out infinite" : "none",
                "@keyframes pulse": {
                  "0%, 100%": { boxShadow: "0 8px 32px rgba(59, 130, 246, 0.3)" },
                  "50%": { boxShadow: "0 8px 48px rgba(59, 130, 246, 0.5)" }
                }
              }}
            >
              <Psychology sx={{ fontSize: 32, color: "white" }} />
            </Box>
            <Box>
              <Stack direction="row" alignItems="center" spacing={1}>
                <Typography variant="h5" fontWeight="bold" sx={{
                  background: "linear-gradient(90deg, #fff 0%, #94a3b8 100%)",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent"
                }}>
                  Under The Hood
                </Typography>
                <Badge
                  badgeContent={connected ? "LIVE" : "OFF"}
                  color={connected ? "success" : "error"}
                  sx={{ "& .MuiBadge-badge": { fontSize: "0.6rem", height: 16, minWidth: 32 } }}
                />
              </Stack>
              <Typography variant="body2" color="text.secondary">
                Real-time algorithmic decision visualization • Data Granularity View
              </Typography>
            </Box>
          </Stack>

          <Stack direction="row" spacing={2} alignItems="center">
            <Chip
              icon={<Memory sx={{ fontSize: 16 }} />}
              label={`${botState?.active_strategies?.length || 0} Strategies`}
              size="small"
              sx={{ bgcolor: "rgba(139, 92, 246, 0.15)", color: "#a78bfa" }}
            />
            <Chip
              icon={<Radar sx={{ fontSize: 16 }} />}
              label={`${botState?.symbols_scanned || 0} Scanned`}
              size="small"
              sx={{ bgcolor: "rgba(34, 197, 94, 0.15)", color: "#4ade80" }}
            />
            <Chip
              label={`${updateCount} updates`}
              size="small"
              sx={{ bgcolor: "rgba(59, 130, 246, 0.15)", color: "#60a5fa" }}
            />
          </Stack>
        </Stack>

        {/* Real-Time Data Crunch Panel */}
        <Box sx={{
          mb: 3,
          p: 2,
          borderRadius: 3,
          background: "linear-gradient(135deg, rgba(59, 130, 246, 0.08) 0%, rgba(139, 92, 246, 0.08) 100%)",
          border: "1px solid rgba(59, 130, 246, 0.2)"
        }}>
          <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
            <Equalizer sx={{ color: "#60a5fa" }} />
            <Typography variant="subtitle1" fontWeight="bold">Real-Time Data Crunch</Typography>
            <Box sx={{ flexGrow: 1 }} />
            <Box sx={{
              px: 1.5,
              py: 0.5,
              borderRadius: 1,
              bgcolor: "rgba(34, 197, 94, 0.1)",
              border: "1px solid rgba(34, 197, 94, 0.3)"
            }}>
              <Typography variant="caption" sx={{ color: "#4ade80", fontFamily: "'JetBrains Mono', monospace" }}>
                Processing {botState?.analyzed_opportunities?.length || 0} symbols @ 100ms
              </Typography>
            </Box>
          </Stack>

          <Grid container spacing={3}>
            {/* Indicator Gauges */}
            <Grid item xs={12} md={5}>
              <Stack direction="row" spacing={2} justifyContent="space-around" alignItems="flex-start">
                <IndicatorGauge
                  label="Avg RSI"
                  value={aggregatedData?.avgRsi || 50}
                  min={0}
                  max={100}
                  zones={[
                    { start: 0, end: 30, color: "#22c55e" },
                    { start: 30, end: 70, color: "#f59e0b" },
                    { start: 70, end: 100, color: "#ef4444" }
                  ]}
                />
                <IndicatorGauge
                  label="Volatility"
                  value={(aggregatedData?.avgVolatility || 0) * 100}
                  min={0}
                  max={10}
                  unit="%"
                  zones={[
                    { start: 0, end: 2, color: "#64748b" },
                    { start: 2, end: 5, color: "#3b82f6" },
                    { start: 5, end: 10, color: "#f59e0b" }
                  ]}
                />
                <IndicatorGauge
                  label="Confidence"
                  value={(aggregatedData?.totalConfidence || 0) * 100}
                  min={0}
                  max={100}
                  unit="%"
                  zones={[
                    { start: 0, end: 50, color: "#ef4444" },
                    { start: 50, end: 70, color: "#f59e0b" },
                    { start: 70, end: 100, color: "#22c55e" }
                  ]}
                />
              </Stack>
            </Grid>

            {/* Live Numbers */}
            <Grid item xs={12} md={7}>
              <Grid container spacing={2}>
                {[
                  { label: "Total Volume", value: aggregatedData?.totalVolume || 0, format: (v: number) => (v / 1000000).toFixed(2) + "M", color: "#3b82f6" },
                  { label: "Avg Price", value: aggregatedData?.avgPrice || 0, format: (v: number) => "$" + v.toFixed(2), color: "#22c55e" },
                  { label: "BUY Signals", value: aggregatedData?.buySignals || 0, format: (v: number) => v.toString(), color: "#22c55e" },
                  { label: "SELL Signals", value: aggregatedData?.sellSignals || 0, format: (v: number) => v.toString(), color: "#ef4444" },
                  { label: "HOLD Signals", value: aggregatedData?.holdSignals || 0, format: (v: number) => v.toString(), color: "#64748b" },
                  { label: "Active Strats", value: botState?.active_strategies?.length || 0, format: (v: number) => v.toString(), color: "#8b5cf6" }
                ].map(item => (
                  <Grid item xs={4} key={item.label}>
                    <Box sx={{
                      p: 1.5,
                      borderRadius: 2,
                      bgcolor: "rgba(255,255,255,0.03)",
                      border: "1px solid rgba(255,255,255,0.06)",
                      textAlign: "center"
                    }}>
                      <Typography variant="caption" color="text.secondary">{item.label}</Typography>
                      <Typography
                        variant="h6"
                        fontWeight="bold"
                        sx={{
                          fontFamily: "'JetBrains Mono', monospace",
                          color: item.color,
                          animation: "numberPulse 0.5s ease-out",
                          "@keyframes numberPulse": {
                            "0%": { opacity: 0.7 },
                            "100%": { opacity: 1 }
                          }
                        }}
                      >
                        {item.format(item.value)}
                      </Typography>
                    </Box>
                  </Grid>
                ))}
              </Grid>
            </Grid>
          </Grid>
        </Box>

        {/* Main Visualization Grid */}
        <Grid container spacing={3}>
          {/* Left: Strategy Categories */}
          <Grid item xs={12} md={4}>
            <Box sx={{
              p: 2,
              borderRadius: 3,
              bgcolor: "rgba(255,255,255,0.02)",
              border: "1px solid rgba(255,255,255,0.06)",
              height: "100%"
            }}>
              <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
                <Hub sx={{ color: "primary.main" }} />
                <Typography variant="subtitle1" fontWeight="bold">Strategy Neural Network</Typography>
              </Stack>

              <Stack spacing={2}>
                {Object.entries(STRATEGY_CATEGORIES).map(([category, data]) => {
                  const activeInCategory = botState?.active_strategies?.filter(s =>
                    data.strategies.includes(s)
                  ).length || 0;

                  return (
                    <Box
                      key={category}
                      sx={{
                        p: 1.5,
                        borderRadius: 2,
                        bgcolor: "rgba(255,255,255,0.02)",
                        border: `1px solid ${activeInCategory > 0 ? data.color + '40' : 'rgba(255,255,255,0.04)'}`,
                        transition: "all 0.3s ease",
                        "&:hover": {
                          bgcolor: "rgba(255,255,255,0.04)",
                          transform: "translateX(4px)"
                        }
                      }}
                    >
                      <Stack direction="row" justifyContent="space-between" alignItems="center">
                        <Stack direction="row" spacing={1.5} alignItems="center">
                          <Box
                            sx={{
                              width: 36,
                              height: 36,
                              borderRadius: 2,
                              bgcolor: data.color + "20",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center"
                            }}
                          >
                            <Bolt sx={{ color: data.color, fontSize: 20 }} />
                          </Box>
                          <Box>
                            <Typography variant="body2" fontWeight="bold" sx={{ color: data.color }}>
                              {category}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {data.strategies.length} strategies
                            </Typography>
                          </Box>
                        </Stack>
                        <Chip
                          label={`${activeInCategory} active`}
                          size="small"
                          sx={{
                            height: 20,
                            fontSize: "0.65rem",
                            bgcolor: activeInCategory > 0 ? data.color + "20" : "transparent",
                            color: activeInCategory > 0 ? data.color : "text.secondary",
                            border: `1px solid ${activeInCategory > 0 ? data.color + '40' : 'rgba(255,255,255,0.1)'}`
                          }}
                        />
                      </Stack>

                      {/* Mini strategy indicators */}
                      <Stack direction="row" spacing={0.5} sx={{ mt: 1, flexWrap: "wrap", gap: 0.5 }}>
                        {data.strategies.slice(0, 4).map(strat => {
                          const isActive = botState?.active_strategies?.includes(strat);
                          const isAnimating = animatingStrategy === strat;
                          return (
                            <Tooltip key={strat} title={formatStrategyName(strat)}>
                              <Box
                                sx={{
                                  width: 8,
                                  height: 8,
                                  borderRadius: "50%",
                                  bgcolor: isActive ? data.color : "rgba(255,255,255,0.1)",
                                  animation: isAnimating ? "stratPulse 0.5s ease-in-out infinite" : "none",
                                  "@keyframes stratPulse": {
                                    "0%, 100%": { transform: "scale(1)", opacity: 1 },
                                    "50%": { transform: "scale(1.5)", opacity: 0.7 }
                                  }
                                }}
                              />
                            </Tooltip>
                          );
                        })}
                        {data.strategies.length > 4 && (
                          <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.6rem" }}>
                            +{data.strategies.length - 4}
                          </Typography>
                        )}
                      </Stack>
                    </Box>
                  );
                })}
              </Stack>
            </Box>
          </Grid>

          {/* Center: Signal Flow Visualization */}
          <Grid item xs={12} md={4}>
            <Box sx={{
              p: 2,
              borderRadius: 3,
              bgcolor: "rgba(255,255,255,0.02)",
              border: "1px solid rgba(255,255,255,0.06)",
              minHeight: 400
            }}>
              <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
                <DataUsage sx={{ color: "primary.main" }} />
                <Typography variant="subtitle1" fontWeight="bold">Calculation Pipeline</Typography>
              </Stack>

              {/* Signal Flow Diagram */}
              <Box sx={{ position: "relative", minHeight: 350 }}>
                {/* Data Input Layer - Now with actual values */}
                <Box sx={{ mb: 2 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: "block" }}>
                    RAW DATA INPUTS
                  </Typography>
                  <Stack spacing={1}>
                    {[
                      { name: "Price", value: `$${(aggregatedData?.avgPrice || 0).toFixed(2)}`, color: "#22c55e" },
                      { name: "Volume", value: `${((aggregatedData?.totalVolume || 0) / 1000000).toFixed(1)}M`, color: "#3b82f6" },
                      { name: "RSI", value: `${(aggregatedData?.avgRsi || 50).toFixed(1)}`, color: "#f59e0b" }
                    ].map((input, i) => (
                      <Box
                        key={input.name}
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          px: 2,
                          py: 1,
                          borderRadius: 1,
                          bgcolor: "rgba(59, 130, 246, 0.05)",
                          border: "1px solid rgba(59, 130, 246, 0.2)",
                          animation: `dataFlow ${1 + i * 0.2}s ease-in-out infinite`,
                          "@keyframes dataFlow": {
                            "0%, 100%": { borderColor: "rgba(59, 130, 246, 0.2)" },
                            "50%": { borderColor: "rgba(59, 130, 246, 0.5)" }
                          }
                        }}
                      >
                        <Typography variant="caption" sx={{ color: "#94a3b8" }}>
                          {input.name}
                        </Typography>
                        <Typography
                          variant="caption"
                          sx={{
                            color: input.color,
                            fontFamily: "'JetBrains Mono', monospace",
                            fontWeight: 600
                          }}
                        >
                          {input.value}
                        </Typography>
                      </Box>
                    ))}
                  </Stack>
                </Box>

                {/* Flow Lines */}
                <Box sx={{
                  height: 30,
                  display: "flex",
                  justifyContent: "center",
                  alignItems: "center",
                  position: "relative"
                }}>
                  <Box sx={{
                    width: 2,
                    height: "100%",
                    background: "linear-gradient(180deg, rgba(59,130,246,0.5) 0%, rgba(139,92,246,0.5) 100%)",
                    animation: "flowDown 1s ease-in-out infinite",
                    "@keyframes flowDown": {
                      "0%": { opacity: 0.3 },
                      "50%": { opacity: 1 },
                      "100%": { opacity: 0.3 }
                    }
                  }} />
                  <ArrowForward sx={{
                    position: "absolute",
                    bottom: 0,
                    transform: "rotate(90deg)",
                    color: "rgba(139,92,246,0.5)",
                    fontSize: 16
                  }} />
                </Box>

                {/* Strategy Processing Layer */}
                <Box sx={{ mb: 2 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: "block", textAlign: "center" }}>
                    STRATEGY AGGREGATION
                  </Typography>
                  <Box sx={{
                    p: 2,
                    borderRadius: 2,
                    background: "linear-gradient(135deg, rgba(139,92,246,0.1) 0%, rgba(59,130,246,0.1) 100%)",
                    border: "1px solid rgba(139,92,246,0.3)",
                    textAlign: "center"
                  }}>
                    <Stack direction="row" justifyContent="center" spacing={3}>
                      <Box sx={{ textAlign: "center" }}>
                        <Typography variant="h4" fontWeight="bold" sx={{ color: "#22c55e", fontFamily: "'JetBrains Mono', monospace" }}>
                          {botState?.analyzed_opportunities?.filter(o => o.final_action === "BUY").length || 0}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">BUY</Typography>
                      </Box>
                      <Divider orientation="vertical" flexItem sx={{ bgcolor: "rgba(255,255,255,0.1)" }} />
                      <Box sx={{ textAlign: "center" }}>
                        <Typography variant="h4" fontWeight="bold" sx={{ color: "#ef4444", fontFamily: "'JetBrains Mono', monospace" }}>
                          {botState?.analyzed_opportunities?.filter(o => o.final_action === "SELL").length || 0}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">SELL</Typography>
                      </Box>
                      <Divider orientation="vertical" flexItem sx={{ bgcolor: "rgba(255,255,255,0.1)" }} />
                      <Box sx={{ textAlign: "center" }}>
                        <Typography variant="h4" fontWeight="bold" sx={{ color: "#64748b", fontFamily: "'JetBrains Mono', monospace" }}>
                          {botState?.analyzed_opportunities?.filter(o => o.final_action === "HOLD").length || 0}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">HOLD</Typography>
                      </Box>
                    </Stack>
                  </Box>
                </Box>

                {/* Flow Lines */}
                <Box sx={{
                  height: 30,
                  display: "flex",
                  justifyContent: "center",
                  alignItems: "center",
                  position: "relative"
                }}>
                  <Box sx={{
                    width: 2,
                    height: "100%",
                    background: "linear-gradient(180deg, rgba(139,92,246,0.5) 0%, rgba(34,197,94,0.5) 100%)"
                  }} />
                  <ArrowForward sx={{
                    position: "absolute",
                    bottom: 0,
                    transform: "rotate(90deg)",
                    color: "rgba(34,197,94,0.5)",
                    fontSize: 16
                  }} />
                </Box>

                {/* Decision Output */}
                <Box>
                  <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: "block", textAlign: "center" }}>
                    FINAL DECISION LAYER
                  </Typography>
                  <Box sx={{
                    p: 2,
                    borderRadius: 2,
                    background: "linear-gradient(135deg, rgba(34,197,94,0.15) 0%, rgba(22,163,74,0.15) 100%)",
                    border: "1px solid rgba(34,197,94,0.4)",
                    textAlign: "center"
                  }}>
                    <Stack spacing={1}>
                      <Stack direction="row" justifyContent="space-between" alignItems="center">
                        <Typography variant="caption" color="text.secondary">
                          Confidence Threshold
                        </Typography>
                        <Typography variant="caption" sx={{ color: "#4ade80", fontFamily: "'JetBrains Mono', monospace" }}>
                          {botState?.risk_posture === "AGGRESSIVE" ? "50%" : botState?.risk_posture === "CONSERVATIVE" ? "80%" : "65%"}
                        </Typography>
                      </Stack>
                      <Stack direction="row" justifyContent="space-between" alignItems="center">
                        <Typography variant="caption" color="text.secondary">
                          Risk Posture
                        </Typography>
                        <Typography variant="caption" sx={{ color: "#f59e0b", fontFamily: "'JetBrains Mono', monospace" }}>
                          {botState?.risk_posture || "MODERATE"}
                        </Typography>
                      </Stack>
                      <Divider sx={{ bgcolor: "rgba(255,255,255,0.1)", my: 1 }} />
                      <Chip
                        label={botState?.mode || "MONITORING"}
                        color={botState?.running ? "success" : "default"}
                        sx={{ fontWeight: "bold" }}
                      />
                    </Stack>
                  </Box>
                </Box>
              </Box>
            </Box>
          </Grid>

          {/* Right: Live Opportunities with Granular Data */}
          <Grid item xs={12} md={4}>
            <Box sx={{
              p: 2,
              borderRadius: 3,
              bgcolor: "rgba(255,255,255,0.02)",
              border: "1px solid rgba(255,255,255,0.06)",
              height: "100%"
            }}>
              <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
                <Insights sx={{ color: "primary.main" }} />
                <Typography variant="subtitle1" fontWeight="bold">Live Analysis</Typography>
                <Box sx={{ flexGrow: 1 }} />
                <Typography variant="caption" color="text.secondary">
                  {botState?.analyzed_opportunities?.length || 0} active
                </Typography>
              </Stack>

              <Stack spacing={1.5} sx={{ maxHeight: 380, overflow: "auto" }}>
                {botState?.analyzed_opportunities?.slice(0, 8).map((opp, index) => (
                  <Box
                    key={opp.symbol}
                    sx={{
                      p: 1.5,
                      borderRadius: 2,
                      bgcolor: expandedOpportunity === opp.symbol ? "rgba(59,130,246,0.08)" : "rgba(255,255,255,0.02)",
                      border: `1px solid ${expandedOpportunity === opp.symbol ? "rgba(59,130,246,0.3)" : "rgba(255,255,255,0.04)"}`,
                      cursor: "pointer",
                      transition: "all 0.2s ease",
                      animation: index < 3 ? `slideIn ${0.3 + index * 0.1}s ease-out` : "none",
                      "@keyframes slideIn": {
                        "0%": { opacity: 0, transform: "translateX(20px)" },
                        "100%": { opacity: 1, transform: "translateX(0)" }
                      },
                      "&:hover": {
                        bgcolor: "rgba(255,255,255,0.04)"
                      }
                    }}
                    onClick={() => setExpandedOpportunity(expandedOpportunity === opp.symbol ? null : opp.symbol)}
                  >
                    <Stack direction="row" justifyContent="space-between" alignItems="center">
                      <Stack direction="row" spacing={1.5} alignItems="center">
                        <Box
                          sx={{
                            width: 36,
                            height: 36,
                            borderRadius: "50%",
                            bgcolor: getSignalColor(opp.final_action) + "15",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            border: `1px solid ${getSignalColor(opp.final_action)}30`
                          }}
                        >
                          {opp.final_action === "BUY" ? (
                            <TrendingUp sx={{ color: "#22c55e", fontSize: 20 }} />
                          ) : opp.final_action === "SELL" ? (
                            <TrendingDown sx={{ color: "#ef4444", fontSize: 20 }} />
                          ) : (
                            <TrendingFlat sx={{ color: "#64748b", fontSize: 20 }} />
                          )}
                        </Box>
                        <Box>
                          <Stack direction="row" alignItems="center" spacing={1}>
                            <Typography variant="body2" fontWeight="bold">{opp.symbol}</Typography>
                            {priceHistory[opp.symbol]?.length > 1 && (
                              <MiniSparkline
                                data={priceHistory[opp.symbol]}
                                color={getSignalColor(opp.final_action)}
                                width={40}
                                height={16}
                              />
                            )}
                          </Stack>
                          <Typography
                            variant="caption"
                            sx={{
                              fontFamily: "'JetBrains Mono', monospace",
                              color: "#94a3b8"
                            }}
                          >
                            ${opp.price?.toFixed(2) || "N/A"}
                          </Typography>
                        </Box>
                      </Stack>
                      <Stack alignItems="flex-end" spacing={0.5}>
                        <Chip
                          label={opp.final_action}
                          size="small"
                          sx={{
                            height: 20,
                            fontSize: "0.65rem",
                            fontWeight: "bold",
                            bgcolor: getSignalColor(opp.final_action) + "20",
                            color: getSignalColor(opp.final_action)
                          }}
                        />
                        <Typography variant="caption" sx={{ fontFamily: "'JetBrains Mono', monospace", color: "#94a3b8" }}>
                          {(opp.aggregate_confidence * 100).toFixed(0)}%
                        </Typography>
                      </Stack>
                    </Stack>

                    {/* Expanded Granular Data */}
                    {expandedOpportunity === opp.symbol && (
                      <Box sx={{ mt: 2, pt: 2, borderTop: "1px solid rgba(255,255,255,0.06)" }}>
                        {/* Raw Data Section */}
                        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
                          RAW MARKET DATA
                        </Typography>
                        <Grid container spacing={1} sx={{ mb: 2 }}>
                          {[
                            { label: "Open", value: opp.data?.open, format: (v: number) => `$${v.toFixed(2)}` },
                            { label: "High", value: opp.data?.high, format: (v: number) => `$${v.toFixed(2)}` },
                            { label: "Low", value: opp.data?.low, format: (v: number) => `$${v.toFixed(2)}` },
                            { label: "Vol", value: opp.data?.volume, format: (v: number) => `${(v / 1000).toFixed(0)}K` },
                            { label: "RVol", value: opp.data?.relative_volume, format: (v: number) => `${v?.toFixed(1)}x` },
                            { label: "ATR%", value: opp.data?.atr_percent, format: (v: number) => `${(v * 100).toFixed(2)}%` }
                          ].map(item => (
                            <Grid item xs={4} key={item.label}>
                              <Box sx={{
                                p: 0.75,
                                borderRadius: 1,
                                bgcolor: "rgba(255,255,255,0.03)",
                                textAlign: "center"
                              }}>
                                <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.6rem" }}>
                                  {item.label}
                                </Typography>
                                <Typography
                                  variant="caption"
                                  sx={{
                                    display: "block",
                                    fontFamily: "'JetBrains Mono', monospace",
                                    color: "#fff",
                                    fontWeight: 600
                                  }}
                                >
                                  {item.value ? item.format(item.value) : "N/A"}
                                </Typography>
                              </Box>
                            </Grid>
                          ))}
                        </Grid>

                        {/* Indicator Values */}
                        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
                          INDICATOR VALUES
                        </Typography>
                        <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
                          {[
                            { label: "RSI", value: opp.data?.rsi, color: opp.data?.rsi && opp.data.rsi > 70 ? "#ef4444" : opp.data?.rsi && opp.data.rsi < 30 ? "#22c55e" : "#f59e0b" },
                            { label: "VWAP", value: opp.data?.vwap, prefix: "$" },
                            { label: "Bid", value: opp.data?.bid, prefix: "$" },
                            { label: "Ask", value: opp.data?.ask, prefix: "$" }
                          ].map(item => (
                            <Box
                              key={item.label}
                              sx={{
                                flex: 1,
                                p: 0.75,
                                borderRadius: 1,
                                bgcolor: "rgba(59, 130, 246, 0.05)",
                                border: "1px solid rgba(59, 130, 246, 0.1)",
                                textAlign: "center"
                              }}
                            >
                              <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.55rem" }}>
                                {item.label}
                              </Typography>
                              <Typography
                                variant="caption"
                                sx={{
                                  display: "block",
                                  fontFamily: "'JetBrains Mono', monospace",
                                  color: item.color || "#60a5fa",
                                  fontWeight: 600
                                }}
                              >
                                {item.value ? `${item.prefix || ""}${item.value.toFixed(2)}` : "N/A"}
                              </Typography>
                            </Box>
                          ))}
                        </Stack>

                        {/* Contributing Strategies */}
                        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
                          STRATEGY SIGNALS ({opp.signals?.length || 0})
                        </Typography>
                        <Stack spacing={0.5}>
                          {opp.signals?.slice(0, 4).map(sig => {
                            const catInfo = getCategoryForStrategy(sig.strategy);
                            return (
                              <Stack
                                key={sig.strategy}
                                direction="row"
                                justifyContent="space-between"
                                alignItems="center"
                                sx={{
                                  px: 1,
                                  py: 0.5,
                                  borderRadius: 1,
                                  bgcolor: catInfo.color + "10",
                                  border: `1px solid ${catInfo.color}20`
                                }}
                              >
                                <Typography variant="caption" sx={{ color: catInfo.color }}>
                                  {formatStrategyName(sig.strategy)}
                                </Typography>
                                <Stack direction="row" spacing={1} alignItems="center">
                                  <Chip
                                    label={sig.action}
                                    size="small"
                                    sx={{
                                      height: 16,
                                      fontSize: "0.55rem",
                                      bgcolor: getSignalColor(sig.action) + "20",
                                      color: getSignalColor(sig.action)
                                    }}
                                  />
                                  <Typography
                                    variant="caption"
                                    sx={{
                                      fontFamily: "'JetBrains Mono', monospace",
                                      color: "#94a3b8",
                                      fontSize: "0.6rem"
                                    }}
                                  >
                                    {(sig.confidence * 100).toFixed(0)}%
                                  </Typography>
                                </Stack>
                              </Stack>
                            );
                          })}
                        </Stack>

                        {opp.reasoning && (
                          <Box sx={{ mt: 1.5, p: 1, borderRadius: 1, bgcolor: "rgba(255,255,255,0.02)" }}>
                            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.5 }}>
                              REASONING
                            </Typography>
                            <Typography variant="caption" sx={{ color: "#94a3b8", fontStyle: "italic" }}>
                              "{opp.reasoning.slice(0, 150)}..."
                            </Typography>
                          </Box>
                        )}
                      </Box>
                    )}
                  </Box>
                ))}

                {(!botState?.analyzed_opportunities || botState.analyzed_opportunities.length === 0) && (
                  <Box sx={{ textAlign: "center", py: 4 }}>
                    <Analytics sx={{ fontSize: 48, color: "text.secondary", opacity: 0.3, mb: 1 }} />
                    <Typography variant="body2" color="text.secondary">
                      Waiting for market scan...
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Click "Scan Now" on the scanner panel
                    </Typography>
                  </Box>
                )}
              </Stack>
            </Box>
          </Grid>
        </Grid>

        {/* Bottom: Real-time Indicator Feed */}
        <Box sx={{
          mt: 3,
          p: 2,
          borderRadius: 3,
          bgcolor: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.06)"
        }}>
          <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 2 }}>
            <Stack direction="row" alignItems="center" spacing={1}>
              <AutoGraph sx={{ color: "primary.main" }} />
              <Typography variant="subtitle1" fontWeight="bold">Algorithm Activity Stream</Typography>
            </Stack>
            <Stack direction="row" spacing={1} alignItems="center">
              <Box sx={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                bgcolor: connected ? "#22c55e" : "#ef4444",
                animation: connected ? "livePulse 1s ease-in-out infinite" : "none",
                "@keyframes livePulse": {
                  "0%, 100%": { opacity: 1 },
                  "50%": { opacity: 0.5 }
                }
              }} />
              <Typography variant="caption" color="text.secondary">
                Last update: {botState?.last_scan ? new Date(botState.last_scan).toLocaleTimeString() : "Never"}
              </Typography>
            </Stack>
          </Stack>

          <Stack direction="row" spacing={2} sx={{ overflow: "auto", pb: 1 }}>
            {/* Scrolling activity indicators with live values */}
            {[
              { label: "Market Feed", value: connected ? "STREAMING" : "OFFLINE", color: connected ? "#22c55e" : "#ef4444", icon: <ShowChart sx={{ fontSize: 14 }} /> },
              { label: "Quote Cache", value: `${botState?.symbols_scanned || 0} symbols`, color: "#3b82f6", icon: <DataUsage sx={{ fontSize: 14 }} /> },
              { label: "Strategies", value: `${botState?.active_strategies?.length || 0} active`, color: "#8b5cf6", icon: <Hub sx={{ fontSize: 14 }} /> },
              { label: "Risk Mode", value: botState?.risk_posture || "MODERATE", color: "#f59e0b", icon: <Speed sx={{ fontSize: 14 }} /> },
              { label: "Engine", value: botState?.running ? "RUNNING" : "STOPPED", color: botState?.running ? "#22c55e" : "#ef4444", icon: <Memory sx={{ fontSize: 14 }} /> },
              { label: "Latency", value: "~100ms", color: "#06b6d4", icon: <Timeline sx={{ fontSize: 14 }} /> },
              { label: "Throughput", value: `${updateCount}/s`, color: "#ec4899", icon: <BarChart sx={{ fontSize: 14 }} /> }
            ].map((item) => (
              <Box
                key={item.label}
                sx={{
                  minWidth: 130,
                  p: 1.5,
                  borderRadius: 2,
                  bgcolor: "rgba(255,255,255,0.02)",
                  border: "1px solid rgba(255,255,255,0.06)",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 0.5
                }}
              >
                <Stack direction="row" alignItems="center" spacing={0.5}>
                  <Box sx={{ color: item.color }}>{item.icon}</Box>
                  <Typography variant="caption" color="text.secondary">{item.label}</Typography>
                </Stack>
                <Typography
                  variant="body2"
                  fontWeight="bold"
                  sx={{
                    color: item.color,
                    fontFamily: "'JetBrains Mono', monospace"
                  }}
                >
                  {item.value}
                </Typography>
              </Box>
            ))}
          </Stack>
        </Box>
      </CardContent>
    </Card>
  );
};

export default UnderTheHood;
