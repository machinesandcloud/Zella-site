import { useEffect, useState, useRef, useCallback } from "react";
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
  Badge
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
  Radar
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
    volume: number;
    relative_volume: number;
    volatility: number;
    atr_percent?: number;
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

const UnderTheHood = () => {
  const [botState, setBotState] = useState<BotState | null>(null);
  const [connected, setConnected] = useState(false);
  const [updateCount, setUpdateCount] = useState(0);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [animatingStrategy, setAnimatingStrategy] = useState<string | null>(null);
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
                Real-time algorithmic decision visualization
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
                <Typography variant="subtitle1" fontWeight="bold">Signal Aggregation</Typography>
              </Stack>

              {/* Signal Flow Diagram */}
              <Box sx={{ position: "relative", minHeight: 320 }}>
                {/* Data Input Layer */}
                <Box sx={{ mb: 3 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: "block" }}>
                    DATA INPUTS
                  </Typography>
                  <Stack direction="row" spacing={1} justifyContent="center">
                    {["Price", "Volume", "RSI", "MACD", "VWAP"].map((input, i) => (
                      <Box
                        key={input}
                        sx={{
                          px: 1.5,
                          py: 0.5,
                          borderRadius: 1,
                          bgcolor: "rgba(59, 130, 246, 0.1)",
                          border: "1px solid rgba(59, 130, 246, 0.3)",
                          animation: `dataFlow ${1 + i * 0.2}s ease-in-out infinite`,
                          "@keyframes dataFlow": {
                            "0%, 100%": { opacity: 0.7 },
                            "50%": { opacity: 1 }
                          }
                        }}
                      >
                        <Typography variant="caption" sx={{ color: "#60a5fa", fontWeight: 500 }}>
                          {input}
                        </Typography>
                      </Box>
                    ))}
                  </Stack>
                </Box>

                {/* Flow Lines */}
                <Box sx={{
                  height: 40,
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
                <Box sx={{ mb: 3 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: "block", textAlign: "center" }}>
                    STRATEGY PROCESSING
                  </Typography>
                  <Box sx={{
                    p: 2,
                    borderRadius: 2,
                    background: "linear-gradient(135deg, rgba(139,92,246,0.1) 0%, rgba(59,130,246,0.1) 100%)",
                    border: "1px solid rgba(139,92,246,0.3)",
                    textAlign: "center"
                  }}>
                    <Stack direction="row" justifyContent="center" spacing={2}>
                      <Box sx={{ textAlign: "center" }}>
                        <Typography variant="h4" fontWeight="bold" sx={{ color: "#22c55e" }}>
                          {botState?.analyzed_opportunities?.filter(o => o.final_action === "BUY").length || 0}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">BUY</Typography>
                      </Box>
                      <Divider orientation="vertical" flexItem sx={{ bgcolor: "rgba(255,255,255,0.1)" }} />
                      <Box sx={{ textAlign: "center" }}>
                        <Typography variant="h4" fontWeight="bold" sx={{ color: "#ef4444" }}>
                          {botState?.analyzed_opportunities?.filter(o => o.final_action === "SELL").length || 0}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">SELL</Typography>
                      </Box>
                      <Divider orientation="vertical" flexItem sx={{ bgcolor: "rgba(255,255,255,0.1)" }} />
                      <Box sx={{ textAlign: "center" }}>
                        <Typography variant="h4" fontWeight="bold" sx={{ color: "#64748b" }}>
                          {botState?.analyzed_opportunities?.filter(o => o.final_action === "HOLD").length || 0}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">HOLD</Typography>
                      </Box>
                    </Stack>
                  </Box>
                </Box>

                {/* Flow Lines */}
                <Box sx={{
                  height: 40,
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
                    FINAL DECISION
                  </Typography>
                  <Box sx={{
                    p: 2,
                    borderRadius: 2,
                    background: "linear-gradient(135deg, rgba(34,197,94,0.15) 0%, rgba(22,163,74,0.15) 100%)",
                    border: "1px solid rgba(34,197,94,0.4)",
                    textAlign: "center"
                  }}>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                      Confidence Threshold: {botState?.risk_posture === "AGGRESSIVE" ? "50%" : botState?.risk_posture === "CONSERVATIVE" ? "80%" : "65%"}
                    </Typography>
                    <Chip
                      label={botState?.mode || "MONITORING"}
                      color={botState?.running ? "success" : "default"}
                      sx={{ fontWeight: "bold" }}
                    />
                  </Box>
                </Box>
              </Box>
            </Box>
          </Grid>

          {/* Right: Live Opportunities */}
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
              </Stack>

              <Stack spacing={1.5} sx={{ maxHeight: 350, overflow: "auto" }}>
                {botState?.analyzed_opportunities?.slice(0, 8).map((opp, index) => (
                  <Box
                    key={opp.symbol}
                    onClick={() => setSelectedSymbol(selectedSymbol === opp.symbol ? null : opp.symbol)}
                    sx={{
                      p: 1.5,
                      borderRadius: 2,
                      bgcolor: selectedSymbol === opp.symbol ? "rgba(59,130,246,0.1)" : "rgba(255,255,255,0.02)",
                      border: `1px solid ${selectedSymbol === opp.symbol ? "rgba(59,130,246,0.4)" : "rgba(255,255,255,0.04)"}`,
                      cursor: "pointer",
                      transition: "all 0.2s ease",
                      animation: index < 3 ? `slideIn ${0.3 + index * 0.1}s ease-out` : "none",
                      "@keyframes slideIn": {
                        "0%": { opacity: 0, transform: "translateX(20px)" },
                        "100%": { opacity: 1, transform: "translateX(0)" }
                      },
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
                            width: 32,
                            height: 32,
                            borderRadius: "50%",
                            bgcolor: getSignalColor(opp.final_action) + "20",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center"
                          }}
                        >
                          {opp.final_action === "BUY" ? (
                            <TrendingUp sx={{ color: "#22c55e", fontSize: 18 }} />
                          ) : opp.final_action === "SELL" ? (
                            <TrendingDown sx={{ color: "#ef4444", fontSize: 18 }} />
                          ) : (
                            <TrendingFlat sx={{ color: "#64748b", fontSize: 18 }} />
                          )}
                        </Box>
                        <Box>
                          <Typography variant="body2" fontWeight="bold">{opp.symbol}</Typography>
                          <Typography variant="caption" color="text.secondary">
                            ${opp.price?.toFixed(2) || "N/A"}
                          </Typography>
                        </Box>
                      </Stack>
                      <Stack alignItems="flex-end">
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
                        <Typography variant="caption" color="text.secondary">
                          {(opp.aggregate_confidence * 100).toFixed(0)}% conf
                        </Typography>
                      </Stack>
                    </Stack>

                    {/* Expanded details */}
                    {selectedSymbol === opp.symbol && (
                      <Box sx={{ mt: 2, pt: 2, borderTop: "1px solid rgba(255,255,255,0.06)" }}>
                        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
                          CONTRIBUTING STRATEGIES
                        </Typography>
                        <Stack direction="row" spacing={0.5} flexWrap="wrap" gap={0.5}>
                          {opp.signals?.slice(0, 5).map(sig => {
                            const catInfo = getCategoryForStrategy(sig.strategy);
                            return (
                              <Chip
                                key={sig.strategy}
                                label={formatStrategyName(sig.strategy)}
                                size="small"
                                sx={{
                                  height: 18,
                                  fontSize: "0.6rem",
                                  bgcolor: catInfo.color + "20",
                                  color: catInfo.color,
                                  border: `1px solid ${catInfo.color}40`
                                }}
                              />
                            );
                          })}
                        </Stack>
                        {opp.reasoning && (
                          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1, fontStyle: "italic" }}>
                            "{opp.reasoning.slice(0, 100)}..."
                          </Typography>
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
            <Typography variant="caption" color="text.secondary">
              Last update: {botState?.last_scan ? new Date(botState.last_scan).toLocaleTimeString() : "Never"}
            </Typography>
          </Stack>

          <Stack direction="row" spacing={2} sx={{ overflow: "auto", pb: 1 }}>
            {/* Scrolling activity indicators */}
            {[
              { label: "Market Data", value: "Streaming", color: "#22c55e" },
              { label: "Quote Cache", value: `${botState?.symbols_scanned || 0} symbols`, color: "#3b82f6" },
              { label: "Strategies", value: `${botState?.active_strategies?.length || 0} active`, color: "#8b5cf6" },
              { label: "Risk Mode", value: botState?.risk_posture || "MODERATE", color: "#f59e0b" },
              { label: "Engine", value: botState?.running ? "RUNNING" : "STOPPED", color: botState?.running ? "#22c55e" : "#ef4444" },
              { label: "Scan Interval", value: "1 second", color: "#06b6d4" }
            ].map((item, i) => (
              <Box
                key={item.label}
                sx={{
                  minWidth: 140,
                  p: 1.5,
                  borderRadius: 2,
                  bgcolor: "rgba(255,255,255,0.02)",
                  border: "1px solid rgba(255,255,255,0.06)",
                  textAlign: "center"
                }}
              >
                <Typography variant="caption" color="text.secondary">{item.label}</Typography>
                <Typography variant="body2" fontWeight="bold" sx={{ color: item.color }}>
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
