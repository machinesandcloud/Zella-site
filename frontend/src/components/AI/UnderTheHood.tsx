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
  CircularProgress,
  Collapse,
  Modal,
  Backdrop,
  Fade
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
  ExpandLess,
  Close,
  Code,
  Functions,
  Calculate,
  KeyboardArrowRight,
  PlayArrow
} from "@mui/icons-material";

// Strategy definitions with formulas and descriptions
const STRATEGY_FORMULAS: Record<string, {
  name: string;
  description: string;
  category: string;
  formula: string;
  inputs: string[];
  conditions: string[];
  buySignal: string;
  sellSignal: string;
}> = {
  bull_flag: {
    name: "Bull Flag",
    description: "Identifies consolidation patterns after a strong upward move, anticipating continuation.",
    category: "Warrior Trading",
    formula: "BUY when: (Price > VWAP) AND (Volume > 1.5x Avg) AND (Pullback < 50% of Flag Pole)",
    inputs: ["Price", "VWAP", "Volume", "ATR", "Previous High"],
    conditions: [
      "Flag pole: 5-15% move in < 30 mins",
      "Consolidation: 3-7 candles, tight range",
      "Volume: Decreasing during flag formation"
    ],
    buySignal: "Price breaks above flag resistance with volume surge",
    sellSignal: "Price breaks below flag support or reaches 1.5x flag pole target"
  },
  flat_top_breakout: {
    name: "Flat Top Breakout",
    description: "Resistance level breakout with high volume confirmation.",
    category: "Warrior Trading",
    formula: "BUY when: (Price > Resistance) AND (Volume > 2x Avg) AND (RSI < 70)",
    inputs: ["Price", "Resistance Level", "Volume", "RSI"],
    conditions: [
      "Multiple touches of resistance (3+)",
      "Price action forming flat top",
      "Building volume on each test"
    ],
    buySignal: "Break above resistance with 2x average volume",
    sellSignal: "Failed breakout (price falls back below resistance)"
  },
  orb: {
    name: "Opening Range Breakout",
    description: "Trades the breakout of the first 15-30 minutes price range.",
    category: "Warrior Trading",
    formula: "BUY when: (Price > ORB_High) AND (Time < 10:30 AM) AND (Volume > Avg)",
    inputs: ["Opening High", "Opening Low", "Current Price", "Volume", "Time"],
    conditions: [
      "Define range: First 15-30 mins",
      "Wait for clear breakout direction",
      "Confirm with relative volume > 1.5x"
    ],
    buySignal: "Price breaks above opening range high",
    sellSignal: "Price breaks below opening range low or hits 2x range target"
  },
  breakout: {
    name: "Breakout Strategy",
    description: "Identifies price breaking through key support/resistance levels.",
    category: "Trend Following",
    formula: "BUY when: (Price > 20-day High) AND (Volume > 1.5x Avg) AND (ADX > 25)",
    inputs: ["Price", "20-day High", "Volume", "ADX"],
    conditions: [
      "Price consolidating for 5+ days",
      "ADX > 25 indicating trend strength",
      "Volume confirmation on breakout"
    ],
    buySignal: "New 20-day high with volume surge",
    sellSignal: "Price falls back below breakout level"
  },
  ema_cross: {
    name: "EMA Crossover",
    description: "Trades based on exponential moving average crossovers.",
    category: "Trend Following",
    formula: "BUY when: (EMA_9 > EMA_20) AND (Price > EMA_9) AND (EMA_20 > EMA_50)",
    inputs: ["EMA(9)", "EMA(20)", "EMA(50)", "Price"],
    conditions: [
      "Fast EMA crosses above slow EMA",
      "Price above both EMAs",
      "Upward slope on all EMAs"
    ],
    buySignal: "EMA(9) crosses above EMA(20)",
    sellSignal: "EMA(9) crosses below EMA(20)"
  },
  htf_ema_momentum: {
    name: "HTF EMA Momentum",
    description: "Uses higher timeframe EMA alignment for trend confirmation.",
    category: "Trend Following",
    formula: "BUY when: (Daily_EMA_20 Slope > 0) AND (4H_EMA_9 > 4H_EMA_20) AND (Price > VWAP)",
    inputs: ["Daily EMA(20)", "4H EMA(9)", "4H EMA(20)", "VWAP"],
    conditions: [
      "Daily EMA(20) trending up",
      "4H EMAs aligned bullish",
      "Intraday price above VWAP"
    ],
    buySignal: "Pullback to 4H EMA(9) in uptrend",
    sellSignal: "4H EMA bearish cross or daily EMA flattens"
  },
  momentum: {
    name: "Momentum Strategy",
    description: "Trades stocks with strong price momentum.",
    category: "Trend Following",
    formula: "BUY when: (ROC_10 > 5%) AND (RSI > 50) AND (Volume > 2x Avg)",
    inputs: ["Rate of Change (10)", "RSI(14)", "Volume", "Price"],
    conditions: [
      "10-day ROC > 5%",
      "RSI between 50-70 (not overbought)",
      "Increasing volume trend"
    ],
    buySignal: "Strong momentum with RSI not overbought",
    sellSignal: "Momentum weakening (ROC declining) or RSI > 80"
  },
  trend_follow: {
    name: "Trend Following",
    description: "Follows established trends using multiple indicators.",
    category: "Trend Following",
    formula: "BUY when: (Price > SMA_50) AND (SMA_50 > SMA_200) AND (ADX > 25)",
    inputs: ["SMA(50)", "SMA(200)", "ADX", "Price"],
    conditions: [
      "Golden cross (SMA50 > SMA200)",
      "ADX indicating strong trend",
      "Price making higher highs"
    ],
    buySignal: "Pullback to SMA(50) in uptrend",
    sellSignal: "Price closes below SMA(50) or death cross"
  },
  first_hour_trend: {
    name: "First Hour Trend",
    description: "Trades the dominant trend established in the first hour.",
    category: "Trend Following",
    formula: "BUY when: (First_Hour_Close > First_Hour_Open) AND (Price > First_Hour_High)",
    inputs: ["First Hour Open", "First Hour Close", "First Hour High", "Current Price"],
    conditions: [
      "Clear directional move in first hour",
      "Volume above average",
      "Break of first hour range"
    ],
    buySignal: "Break above first hour high with momentum",
    sellSignal: "Break below first hour low"
  },
  pullback: {
    name: "Pullback Strategy",
    description: "Buys dips in an uptrend when price pulls back to support.",
    category: "Mean Reversion",
    formula: "BUY when: (Price at EMA_20) AND (RSI < 40) AND (Uptrend Intact)",
    inputs: ["EMA(20)", "RSI(14)", "Trend Direction", "Support Level"],
    conditions: [
      "Overall uptrend (higher highs/lows)",
      "RSI showing oversold on pullback",
      "Price at key support (EMA or fib level)"
    ],
    buySignal: "Bounce from EMA(20) with bullish candle",
    sellSignal: "Break below EMA(20) or trend reversal"
  },
  range_trading: {
    name: "Range Trading",
    description: "Trades between support and resistance in sideways markets.",
    category: "Mean Reversion",
    formula: "BUY when: (Price at Support) AND (RSI < 30) AND (ADX < 20)",
    inputs: ["Support Level", "Resistance Level", "RSI", "ADX"],
    conditions: [
      "ADX < 20 (no trend)",
      "Clear support/resistance levels",
      "Multiple touches of range boundaries"
    ],
    buySignal: "Price bounces from support with bullish signal",
    sellSignal: "Price reaches resistance or breaks support"
  },
  rsi_exhaustion: {
    name: "RSI Exhaustion",
    description: "Trades RSI divergences at extreme levels.",
    category: "Mean Reversion",
    formula: "BUY when: (RSI < 25) AND (Bullish Divergence) AND (Support Nearby)",
    inputs: ["RSI(14)", "Price", "Support Level"],
    conditions: [
      "RSI < 25 (extremely oversold)",
      "Price making lower lows, RSI making higher lows",
      "Near key support level"
    ],
    buySignal: "RSI divergence with bullish reversal candle",
    sellSignal: "RSI reaches 50 or price fails to reverse"
  },
  rsi_extreme_reversal: {
    name: "RSI Extreme Reversal",
    description: "Fades extreme RSI readings expecting mean reversion.",
    category: "Mean Reversion",
    formula: "BUY when: (RSI < 20) AND (Price at -2 StdDev) AND (Volume Spike)",
    inputs: ["RSI(14)", "Bollinger Bands", "Volume", "ATR"],
    conditions: [
      "RSI < 20 (extreme oversold)",
      "Price at lower Bollinger Band",
      "Capitulation volume"
    ],
    buySignal: "Reversal candle at extreme oversold",
    sellSignal: "RSI returns to 50 or new lows made"
  },
  vwap_bounce: {
    name: "VWAP Bounce",
    description: "Trades bounces off the Volume Weighted Average Price.",
    category: "Mean Reversion",
    formula: "BUY when: (Price touches VWAP from above) AND (Uptrend) AND (Volume decreasing)",
    inputs: ["VWAP", "Price", "Volume", "Trend"],
    conditions: [
      "Price in uptrend (above VWAP most of day)",
      "Pullback to VWAP with decreasing volume",
      "Bullish price action at VWAP"
    ],
    buySignal: "Bounce off VWAP with increasing volume",
    sellSignal: "Close below VWAP or reaches prior high"
  },
  nine_forty_five_reversal: {
    name: "9:45 Reversal",
    description: "Fades the initial move after the first 15 minutes.",
    category: "Mean Reversion",
    formula: "FADE when: (Gap > 2%) AND (Time = 9:45) AND (Reversal Candle)",
    inputs: ["Gap Size", "Time", "Price Action", "Volume"],
    conditions: [
      "Large gap (> 2%)",
      "Initial move extending gap",
      "Reversal candle forming at 9:45"
    ],
    buySignal: "Gap down reversal with bullish engulfing",
    sellSignal: "Gap up reversal with bearish engulfing"
  },
  scalping: {
    name: "Scalping",
    description: "Quick trades capturing small price movements.",
    category: "Scalping",
    formula: "BUY when: (Bid/Ask Spread < 0.02%) AND (Volume > 3x Avg) AND (Momentum Positive)",
    inputs: ["Bid/Ask Spread", "Volume", "1-min Momentum", "Level 2 Data"],
    conditions: [
      "Tight spread (< $0.02)",
      "High volume for liquidity",
      "Clear short-term momentum"
    ],
    buySignal: "Large bid stacking with momentum",
    sellSignal: "Target: 0.1-0.3% or momentum reversal"
  },
  rip_and_dip: {
    name: "Rip and Dip",
    description: "Buys the first pullback after a strong initial move.",
    category: "Scalping",
    formula: "BUY when: (Initial Rip > 3%) AND (Pullback 30-50%) AND (Volume High)",
    inputs: ["Initial Move %", "Pullback %", "Volume", "Time"],
    conditions: [
      "Strong initial move (rip) > 3%",
      "Pullback retraces 30-50%",
      "Within first 30 minutes"
    ],
    buySignal: "Bounce from pullback level with volume",
    sellSignal: "Retest of high or new high target"
  },
  big_bid_scalp: {
    name: "Big Bid Scalp",
    description: "Scalps based on large bid orders in Level 2.",
    category: "Scalping",
    formula: "BUY when: (Bid Size > 5x Normal) AND (Price Holding) AND (Tape Positive)",
    inputs: ["Level 2 Bids", "Bid Size", "Time & Sales", "Price"],
    conditions: [
      "Large bid size relative to normal",
      "Bid being defended (not pulled)",
      "Positive tape (more buys than sells)"
    ],
    buySignal: "Price bouncing off big bid with buying tape",
    sellSignal: "Big bid pulled or price breaks below"
  },
  retail_fakeout: {
    name: "Retail Fakeout",
    description: "Identifies and fades false breakouts designed to trap retail.",
    category: "Pattern Recognition",
    formula: "FADE when: (Breakout on low volume) AND (Quick reversal) AND (Back inside range)",
    inputs: ["Breakout Level", "Volume", "Price Action", "Time"],
    conditions: [
      "Breakout with below-average volume",
      "Quick reversal back inside range",
      "Trapped traders visible in tape"
    ],
    buySignal: "False breakdown reversal with volume",
    sellSignal: "False breakout reversal with volume"
  },
  stop_hunt_reversal: {
    name: "Stop Hunt Reversal",
    description: "Trades reversals after obvious stop levels are triggered.",
    category: "Pattern Recognition",
    formula: "BUY when: (Price Spikes Below Support) AND (Quick Reversal) AND (Volume Spike)",
    inputs: ["Support Level", "Price", "Volume", "Stop Level"],
    conditions: [
      "Price spikes through obvious stop level",
      "Immediate reversal (< 5 min)",
      "Volume spike on reversal"
    ],
    buySignal: "V-reversal after stop hunt with volume",
    sellSignal: "Price fails to reclaim or makes new low"
  },
  bagholder_bounce: {
    name: "Bagholder Bounce",
    description: "Identifies bounce opportunities from trapped short sellers.",
    category: "Pattern Recognition",
    formula: "BUY when: (Short Interest > 20%) AND (Positive Catalyst) AND (Price Breaking Out)",
    inputs: ["Short Interest %", "News/Catalyst", "Price", "Volume"],
    conditions: [
      "High short interest (> 20%)",
      "Positive news or catalyst",
      "Price breaking key resistance"
    ],
    buySignal: "Short squeeze starting with volume explosion",
    sellSignal: "Volume declining or exhaustion candle"
  },
  broken_parabolic_short: {
    name: "Broken Parabolic Short",
    description: "Shorts stocks after parabolic moves break down.",
    category: "Pattern Recognition",
    formula: "SHORT when: (Parabolic Move > 50%) AND (Break Below Trend) AND (Exhaustion)",
    inputs: ["Move %", "Trendline", "Volume", "RSI"],
    conditions: [
      "Parabolic move (> 50% in days)",
      "Trendline or support break",
      "Exhaustion signs (doji, volume decline)"
    ],
    buySignal: "N/A (Short strategy)",
    sellSignal: "First major support break with volume"
  },
  fake_halt_trap: {
    name: "Fake Halt Trap",
    description: "Trades continuation after trading halt releases.",
    category: "Pattern Recognition",
    formula: "TRADE when: (Halt Lifted) AND (Direction Confirmed) AND (Volume > 5x)",
    inputs: ["Halt Status", "Pre-halt Price", "Post-halt Price", "Volume"],
    conditions: [
      "Trading halt just lifted",
      "Clear direction on resumption",
      "Massive volume surge"
    ],
    buySignal: "Resume higher with buying pressure",
    sellSignal: "Resume lower or fails to hold direction"
  },
  closing_bell_liquidity_grab: {
    name: "Closing Bell Liquidity",
    description: "Trades the liquidity surge in the last 30 minutes.",
    category: "Smart Money",
    formula: "TRADE when: (Time > 3:30 PM) AND (Price at Key Level) AND (Volume Surging)",
    inputs: ["Time", "Daily VWAP", "Volume", "MOC Orders"],
    conditions: [
      "Last 30 minutes of trading",
      "Price at significant level (VWAP, whole number)",
      "Institutional flow visible"
    ],
    buySignal: "Strong close above VWAP with volume",
    sellSignal: "Weak close below VWAP with volume"
  },
  dark_pool_footprints: {
    name: "Dark Pool Footprints",
    description: "Identifies large block trades suggesting institutional activity.",
    category: "Smart Money",
    formula: "FOLLOW when: (Block Trades > $1M) AND (Direction Consistent) AND (Price Holding)",
    inputs: ["Block Trade Size", "Direction", "Price Level", "Time"],
    conditions: [
      "Large block trades (> $1M)",
      "Consistent direction of blocks",
      "Price holding after blocks"
    ],
    buySignal: "Multiple large buy blocks, price holding support",
    sellSignal: "Multiple large sell blocks, price at resistance"
  },
  market_maker_refill: {
    name: "Market Maker Refill",
    description: "Trades the refill pattern after market maker inventory depletion.",
    category: "Smart Money",
    formula: "BUY when: (MM Inventory Low) AND (Spread Widening) AND (Price at Support)",
    inputs: ["Bid/Ask Spread", "Order Book Depth", "Price", "Volume"],
    conditions: [
      "Spread widening (MM needs inventory)",
      "Order book thinning",
      "Price at key support level"
    ],
    buySignal: "Spread normalizing with price bounce",
    sellSignal: "Spread widening further or support breaks"
  },
  premarket_vwap_reclaim: {
    name: "Premarket VWAP Reclaim",
    description: "Trades reclaim of VWAP after premarket gap.",
    category: "Smart Money",
    formula: "BUY when: (Gap Down) AND (Price Reclaims PM_VWAP) AND (Volume Increasing)",
    inputs: ["Premarket VWAP", "Gap Size", "Current Price", "Volume"],
    conditions: [
      "Significant gap (> 1%)",
      "Price trading below PM VWAP",
      "Attempting to reclaim"
    ],
    buySignal: "Price reclaims and holds PM VWAP",
    sellSignal: "Fails to hold PM VWAP or new low"
  }
};

// Strategy categories with icons and colors
const STRATEGY_CATEGORIES: Record<string, {
  color: string;
  icon: string;
  description: string;
  strategies: string[];
}> = {
  "Warrior Trading": {
    color: "#f59e0b",
    icon: "bolt",
    description: "High-momentum day trading patterns popularized by Ross Cameron",
    strategies: ["bull_flag", "flat_top_breakout", "orb"]
  },
  "Trend Following": {
    color: "#22c55e",
    icon: "trending_up",
    description: "Strategies that identify and ride established market trends",
    strategies: ["breakout", "ema_cross", "htf_ema_momentum", "momentum", "trend_follow", "first_hour_trend"]
  },
  "Mean Reversion": {
    color: "#3b82f6",
    icon: "autorenew",
    description: "Strategies that profit from prices returning to their average",
    strategies: ["pullback", "range_trading", "rsi_exhaustion", "rsi_extreme_reversal", "vwap_bounce", "nine_forty_five_reversal"]
  },
  "Scalping": {
    color: "#ec4899",
    icon: "speed",
    description: "Ultra-short-term trades capturing small price movements",
    strategies: ["scalping", "rip_and_dip", "big_bid_scalp"]
  },
  "Pattern Recognition": {
    color: "#8b5cf6",
    icon: "pattern",
    description: "Identifies market manipulation patterns and traps",
    strategies: ["retail_fakeout", "stop_hunt_reversal", "bagholder_bounce", "broken_parabolic_short", "fake_halt_trap"]
  },
  "Smart Money": {
    color: "#06b6d4",
    icon: "account_balance",
    description: "Follows institutional order flow and market maker activity",
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
}

// Strategy Detail Modal Component
const StrategyDetailModal = ({
  open,
  onClose,
  strategyId,
  liveData
}: {
  open: boolean;
  onClose: () => void;
  strategyId: string | null;
  liveData: AnalyzedOpportunity | null;
}) => {
  const strategy = strategyId ? STRATEGY_FORMULAS[strategyId] : null;
  const [animationStep, setAnimationStep] = useState(0);

  useEffect(() => {
    if (open) {
      const interval = setInterval(() => {
        setAnimationStep(s => (s + 1) % 4);
      }, 800);
      return () => clearInterval(interval);
    }
  }, [open]);

  if (!strategy) return null;

  const getCategoryColor = () => {
    for (const [, cat] of Object.entries(STRATEGY_CATEGORIES)) {
      if (cat.strategies.includes(strategyId || "")) return cat.color;
    }
    return "#64748b";
  };

  const color = getCategoryColor();

  return (
    <Modal
      open={open}
      onClose={onClose}
      closeAfterTransition
      slots={{ backdrop: Backdrop }}
      slotProps={{ backdrop: { timeout: 500 } }}
    >
      <Fade in={open}>
        <Box sx={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          width: { xs: "95%", md: 800 },
          maxHeight: "90vh",
          overflow: "auto",
          bgcolor: "rgba(10, 15, 25, 0.98)",
          border: `1px solid ${color}40`,
          borderRadius: 3,
          boxShadow: `0 20px 60px ${color}20`,
          p: 3
        }}>
          {/* Header */}
          <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 3 }}>
            <Stack direction="row" alignItems="center" spacing={2}>
              <Box sx={{
                width: 48,
                height: 48,
                borderRadius: 2,
                bgcolor: color + "20",
                display: "flex",
                alignItems: "center",
                justifyContent: "center"
              }}>
                <Functions sx={{ color, fontSize: 28 }} />
              </Box>
              <Box>
                <Typography variant="h5" fontWeight="bold" sx={{ color }}>{strategy.name}</Typography>
                <Typography variant="body2" color="text.secondary">{strategy.category}</Typography>
              </Box>
            </Stack>
            <IconButton onClick={onClose} sx={{ color: "text.secondary" }}>
              <Close />
            </IconButton>
          </Stack>

          {/* Description */}
          <Box sx={{ mb: 3, p: 2, borderRadius: 2, bgcolor: "rgba(255,255,255,0.03)" }}>
            <Typography variant="body2" color="text.secondary">{strategy.description}</Typography>
          </Box>

          {/* Live Calculation Visualization */}
          <Box sx={{
            mb: 3,
            p: 2,
            borderRadius: 2,
            bgcolor: "rgba(59, 130, 246, 0.05)",
            border: "1px solid rgba(59, 130, 246, 0.2)"
          }}>
            <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
              <PlayArrow sx={{ color: "#4ade80", fontSize: 20 }} />
              <Typography variant="subtitle2" fontWeight="bold">Live Calculation Pipeline</Typography>
            </Stack>

            <Grid container spacing={2} alignItems="center">
              {/* Inputs */}
              <Grid item xs={12} md={3}>
                <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: "block" }}>
                  DATA INPUTS
                </Typography>
                <Stack spacing={0.5}>
                  {strategy.inputs.slice(0, 4).map((input, i) => (
                    <Box
                      key={input}
                      sx={{
                        px: 1.5,
                        py: 0.75,
                        borderRadius: 1,
                        bgcolor: animationStep >= 1 ? color + "15" : "rgba(255,255,255,0.03)",
                        border: `1px solid ${animationStep >= 1 ? color + "40" : "rgba(255,255,255,0.06)"}`,
                        transition: "all 0.3s ease",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center"
                      }}
                    >
                      <Typography variant="caption" sx={{ color: animationStep >= 1 ? color : "#94a3b8" }}>
                        {input}
                      </Typography>
                      <Typography variant="caption" sx={{ fontFamily: "'JetBrains Mono', monospace", color: "#fff" }}>
                        {liveData?.data ? (
                          input.toLowerCase().includes("price") ? `$${liveData.price?.toFixed(2)}` :
                          input.toLowerCase().includes("volume") ? `${((liveData.data.volume || 0) / 1000).toFixed(0)}K` :
                          input.toLowerCase().includes("rsi") ? `${(liveData.data.rsi || 50).toFixed(1)}` :
                          input.toLowerCase().includes("vwap") ? `$${(liveData.data.vwap || 0).toFixed(2)}` :
                          "..."
                        ) : "..."}
                      </Typography>
                    </Box>
                  ))}
                </Stack>
              </Grid>

              {/* Arrow */}
              <Grid item xs={12} md={1} sx={{ textAlign: "center" }}>
                <KeyboardArrowRight sx={{
                  color: animationStep >= 2 ? color : "#64748b",
                  fontSize: 32,
                  transition: "color 0.3s ease"
                }} />
              </Grid>

              {/* Formula */}
              <Grid item xs={12} md={5}>
                <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: "block" }}>
                  ALGORITHM FORMULA
                </Typography>
                <Box sx={{
                  p: 1.5,
                  borderRadius: 2,
                  bgcolor: animationStep >= 2 ? "rgba(139, 92, 246, 0.1)" : "rgba(255,255,255,0.03)",
                  border: `1px solid ${animationStep >= 2 ? "#8b5cf660" : "rgba(255,255,255,0.06)"}`,
                  fontFamily: "'JetBrains Mono', monospace",
                  transition: "all 0.3s ease"
                }}>
                  <Typography variant="caption" sx={{ color: animationStep >= 2 ? "#a78bfa" : "#94a3b8", whiteSpace: "pre-wrap" }}>
                    {strategy.formula}
                  </Typography>
                </Box>
              </Grid>

              {/* Arrow */}
              <Grid item xs={12} md={1} sx={{ textAlign: "center" }}>
                <KeyboardArrowRight sx={{
                  color: animationStep >= 3 ? "#22c55e" : "#64748b",
                  fontSize: 32,
                  transition: "color 0.3s ease"
                }} />
              </Grid>

              {/* Output */}
              <Grid item xs={12} md={2}>
                <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: "block" }}>
                  SIGNAL OUTPUT
                </Typography>
                <Box sx={{
                  p: 1.5,
                  borderRadius: 2,
                  bgcolor: animationStep >= 3 ? "rgba(34, 197, 94, 0.15)" : "rgba(255,255,255,0.03)",
                  border: `1px solid ${animationStep >= 3 ? "#22c55e60" : "rgba(255,255,255,0.06)"}`,
                  textAlign: "center",
                  transition: "all 0.3s ease"
                }}>
                  <Typography variant="h6" fontWeight="bold" sx={{
                    color: animationStep >= 3 ? (liveData?.final_action === "BUY" ? "#22c55e" : liveData?.final_action === "SELL" ? "#ef4444" : "#64748b") : "#64748b"
                  }}>
                    {liveData?.final_action || "HOLD"}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {((liveData?.aggregate_confidence || 0) * 100).toFixed(0)}% conf
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          </Box>

          {/* Conditions & Signals */}
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Box sx={{ p: 2, borderRadius: 2, bgcolor: "rgba(255,255,255,0.02)", height: "100%" }}>
                <Typography variant="subtitle2" fontWeight="bold" sx={{ mb: 1.5, color }}>
                  Entry Conditions
                </Typography>
                <Stack spacing={1}>
                  {strategy.conditions.map((condition, i) => (
                    <Stack key={i} direction="row" spacing={1} alignItems="flex-start">
                      <Box sx={{
                        width: 6,
                        height: 6,
                        borderRadius: "50%",
                        bgcolor: color,
                        mt: 0.8,
                        flexShrink: 0
                      }} />
                      <Typography variant="caption" color="text.secondary">{condition}</Typography>
                    </Stack>
                  ))}
                </Stack>
              </Box>
            </Grid>
            <Grid item xs={12} md={6}>
              <Stack spacing={2}>
                <Box sx={{ p: 2, borderRadius: 2, bgcolor: "rgba(34, 197, 94, 0.05)", border: "1px solid rgba(34, 197, 94, 0.2)" }}>
                  <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.5 }}>
                    BUY SIGNAL
                  </Typography>
                  <Typography variant="body2" sx={{ color: "#4ade80" }}>{strategy.buySignal}</Typography>
                </Box>
                <Box sx={{ p: 2, borderRadius: 2, bgcolor: "rgba(239, 68, 68, 0.05)", border: "1px solid rgba(239, 68, 68, 0.2)" }}>
                  <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.5 }}>
                    SELL/EXIT SIGNAL
                  </Typography>
                  <Typography variant="body2" sx={{ color: "#f87171" }}>{strategy.sellSignal}</Typography>
                </Box>
              </Stack>
            </Grid>
          </Grid>
        </Box>
      </Fade>
    </Modal>
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
          sx={{ fontFamily: "'JetBrains Mono', monospace", color: getColor() }}
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
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);
  const [selectedStrategy, setSelectedStrategy] = useState<string | null>(null);
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
    return { category: "Other", color: "#64748b", strategies: [], description: "" };
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

  // Get live data for selected strategy (first opportunity that uses it)
  const liveDataForStrategy = useMemo(() => {
    if (!selectedStrategy || !botState?.analyzed_opportunities) return null;
    const opp = botState.analyzed_opportunities.find(o =>
      o.signals?.some(s => s.strategy === selectedStrategy)
    );
    return opp || botState.analyzed_opportunities[0] || null;
  }, [selectedStrategy, botState?.analyzed_opportunities]);

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
      {/* Strategy Detail Modal */}
      <StrategyDetailModal
        open={!!selectedStrategy}
        onClose={() => setSelectedStrategy(null)}
        strategyId={selectedStrategy}
        liveData={liveDataForStrategy}
      />

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
                Click any strategy to see its formula and live calculation
              </Typography>
            </Box>
          </Stack>

          <Stack direction="row" spacing={2} alignItems="center">
            <Chip
              icon={<Memory sx={{ fontSize: 16 }} />}
              label={`${botState?.active_strategies?.length || 0} Active`}
              size="small"
              sx={{ bgcolor: "rgba(139, 92, 246, 0.15)", color: "#a78bfa" }}
            />
            <Chip
              icon={<Radar sx={{ fontSize: 16 }} />}
              label={`${botState?.symbols_scanned || 0} Scanned`}
              size="small"
              sx={{ bgcolor: "rgba(34, 197, 94, 0.15)", color: "#4ade80" }}
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
                Processing @ 100ms intervals
              </Typography>
            </Box>
          </Stack>

          <Grid container spacing={3}>
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
                        sx={{ fontFamily: "'JetBrains Mono', monospace", color: item.color }}
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

        {/* Main Grid: Strategy Neural Network */}
        <Grid container spacing={3}>
          {/* Strategy Categories - Expandable */}
          <Grid item xs={12} md={5}>
            <Box sx={{
              p: 2,
              borderRadius: 3,
              bgcolor: "rgba(255,255,255,0.02)",
              border: "1px solid rgba(255,255,255,0.06)"
            }}>
              <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
                <Hub sx={{ color: "primary.main" }} />
                <Typography variant="subtitle1" fontWeight="bold">Strategy Neural Network</Typography>
                <Typography variant="caption" color="text.secondary" sx={{ ml: "auto" }}>
                  Click to explore
                </Typography>
              </Stack>

              <Stack spacing={1.5}>
                {Object.entries(STRATEGY_CATEGORIES).map(([category, data]) => {
                  const activeInCategory = botState?.active_strategies?.filter(s =>
                    data.strategies.includes(s)
                  ).length || 0;
                  const isExpanded = expandedCategory === category;

                  return (
                    <Box key={category}>
                      <Box
                        onClick={() => setExpandedCategory(isExpanded ? null : category)}
                        sx={{
                          p: 1.5,
                          borderRadius: 2,
                          bgcolor: isExpanded ? data.color + "10" : "rgba(255,255,255,0.02)",
                          border: `1px solid ${isExpanded || activeInCategory > 0 ? data.color + '40' : 'rgba(255,255,255,0.04)'}`,
                          cursor: "pointer",
                          transition: "all 0.3s ease",
                          "&:hover": {
                            bgcolor: data.color + "15",
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
                          <Stack direction="row" alignItems="center" spacing={1}>
                            <Chip
                              label={`${activeInCategory} active`}
                              size="small"
                              sx={{
                                height: 20,
                                fontSize: "0.65rem",
                                bgcolor: activeInCategory > 0 ? data.color + "20" : "transparent",
                                color: activeInCategory > 0 ? data.color : "text.secondary"
                              }}
                            />
                            {isExpanded ? (
                              <ExpandLess sx={{ color: data.color }} />
                            ) : (
                              <ExpandMore sx={{ color: "text.secondary" }} />
                            )}
                          </Stack>
                        </Stack>
                      </Box>

                      {/* Expanded Strategies List */}
                      <Collapse in={isExpanded}>
                        <Box sx={{ pl: 2, pt: 1 }}>
                          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
                            {data.description}
                          </Typography>
                          <Stack spacing={0.5}>
                            {data.strategies.map(stratId => {
                              const stratInfo = STRATEGY_FORMULAS[stratId];
                              const isActive = botState?.active_strategies?.includes(stratId);
                              return (
                                <Box
                                  key={stratId}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setSelectedStrategy(stratId);
                                  }}
                                  sx={{
                                    p: 1,
                                    borderRadius: 1,
                                    bgcolor: isActive ? data.color + "15" : "rgba(255,255,255,0.02)",
                                    border: `1px solid ${isActive ? data.color + "30" : "rgba(255,255,255,0.04)"}`,
                                    cursor: "pointer",
                                    transition: "all 0.2s ease",
                                    "&:hover": {
                                      bgcolor: data.color + "20",
                                      borderColor: data.color + "50"
                                    }
                                  }}
                                >
                                  <Stack direction="row" justifyContent="space-between" alignItems="center">
                                    <Stack direction="row" spacing={1} alignItems="center">
                                      <Box sx={{
                                        width: 6,
                                        height: 6,
                                        borderRadius: "50%",
                                        bgcolor: isActive ? data.color : "rgba(255,255,255,0.2)"
                                      }} />
                                      <Typography variant="caption" sx={{ color: isActive ? data.color : "text.primary" }}>
                                        {stratInfo?.name || formatStrategyName(stratId)}
                                      </Typography>
                                    </Stack>
                                    <Stack direction="row" spacing={0.5} alignItems="center">
                                      <Code sx={{ fontSize: 14, color: "text.secondary" }} />
                                      <Typography variant="caption" color="text.secondary">
                                        View Formula
                                      </Typography>
                                    </Stack>
                                  </Stack>
                                </Box>
                              );
                            })}
                          </Stack>
                        </Box>
                      </Collapse>
                    </Box>
                  );
                })}
              </Stack>
            </Box>
          </Grid>

          {/* Live Analysis Panel */}
          <Grid item xs={12} md={7}>
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
                  {botState?.analyzed_opportunities?.length || 0} opportunities
                </Typography>
              </Stack>

              <Stack spacing={1.5} sx={{ maxHeight: 450, overflow: "auto" }}>
                {botState?.analyzed_opportunities?.slice(0, 10).map((opp, index) => (
                  <Box
                    key={opp.symbol}
                    sx={{
                      p: 1.5,
                      borderRadius: 2,
                      bgcolor: expandedOpportunity === opp.symbol ? "rgba(59,130,246,0.08)" : "rgba(255,255,255,0.02)",
                      border: `1px solid ${expandedOpportunity === opp.symbol ? "rgba(59,130,246,0.3)" : "rgba(255,255,255,0.04)"}`,
                      cursor: "pointer",
                      transition: "all 0.2s ease",
                      "&:hover": { bgcolor: "rgba(255,255,255,0.04)" }
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
                            justifyContent: "center"
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
                          <Typography variant="caption" sx={{ fontFamily: "'JetBrains Mono', monospace", color: "#94a3b8" }}>
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

                    {/* Expanded Details */}
                    <Collapse in={expandedOpportunity === opp.symbol}>
                      <Box sx={{ mt: 2, pt: 2, borderTop: "1px solid rgba(255,255,255,0.06)" }}>
                        <Grid container spacing={1} sx={{ mb: 2 }}>
                          {[
                            { label: "Open", value: opp.data?.open, format: (v: number) => `$${v.toFixed(2)}` },
                            { label: "High", value: opp.data?.high, format: (v: number) => `$${v.toFixed(2)}` },
                            { label: "Low", value: opp.data?.low, format: (v: number) => `$${v.toFixed(2)}` },
                            { label: "Vol", value: opp.data?.volume, format: (v: number) => `${(v / 1000).toFixed(0)}K` },
                            { label: "RSI", value: opp.data?.rsi, format: (v: number) => v.toFixed(1) },
                            { label: "VWAP", value: opp.data?.vwap, format: (v: number) => `$${v.toFixed(2)}` }
                          ].map(item => (
                            <Grid item xs={4} key={item.label}>
                              <Box sx={{ p: 0.75, borderRadius: 1, bgcolor: "rgba(255,255,255,0.03)", textAlign: "center" }}>
                                <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.6rem" }}>
                                  {item.label}
                                </Typography>
                                <Typography variant="caption" sx={{ display: "block", fontFamily: "'JetBrains Mono', monospace", color: "#fff", fontWeight: 600 }}>
                                  {item.value ? item.format(item.value) : "N/A"}
                                </Typography>
                              </Box>
                            </Grid>
                          ))}
                        </Grid>

                        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
                          CONTRIBUTING STRATEGIES ({opp.signals?.length || 0})
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
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setSelectedStrategy(sig.strategy);
                                }}
                                sx={{
                                  px: 1,
                                  py: 0.5,
                                  borderRadius: 1,
                                  bgcolor: catInfo.color + "10",
                                  border: `1px solid ${catInfo.color}20`,
                                  cursor: "pointer",
                                  "&:hover": { bgcolor: catInfo.color + "20" }
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
                                  <Typography variant="caption" sx={{ fontFamily: "'JetBrains Mono', monospace", color: "#94a3b8", fontSize: "0.6rem" }}>
                                    {(sig.confidence * 100).toFixed(0)}%
                                  </Typography>
                                </Stack>
                              </Stack>
                            );
                          })}
                        </Stack>
                      </Box>
                    </Collapse>
                  </Box>
                ))}

                {(!botState?.analyzed_opportunities || botState.analyzed_opportunities.length === 0) && (
                  <Box sx={{ textAlign: "center", py: 4 }}>
                    <Analytics sx={{ fontSize: 48, color: "text.secondary", opacity: 0.3, mb: 1 }} />
                    <Typography variant="body2" color="text.secondary">
                      Waiting for market scan...
                    </Typography>
                  </Box>
                )}
              </Stack>
            </Box>
          </Grid>
        </Grid>

        {/* Bottom Activity Stream */}
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
                {botState?.last_scan ? new Date(botState.last_scan).toLocaleTimeString() : "Never"}
              </Typography>
            </Stack>
          </Stack>

          <Stack direction="row" spacing={2} sx={{ overflow: "auto", pb: 1 }}>
            {[
              { label: "Market Feed", value: connected ? "STREAMING" : "OFFLINE", color: connected ? "#22c55e" : "#ef4444", icon: <ShowChart sx={{ fontSize: 14 }} /> },
              { label: "Strategies", value: `${botState?.active_strategies?.length || 0} active`, color: "#8b5cf6", icon: <Hub sx={{ fontSize: 14 }} /> },
              { label: "Risk Mode", value: botState?.risk_posture || "MODERATE", color: "#f59e0b", icon: <Speed sx={{ fontSize: 14 }} /> },
              { label: "Engine", value: botState?.running ? "RUNNING" : "STOPPED", color: botState?.running ? "#22c55e" : "#ef4444", icon: <Memory sx={{ fontSize: 14 }} /> },
              { label: "Updates", value: `${updateCount}`, color: "#06b6d4", icon: <Timeline sx={{ fontSize: 14 }} /> }
            ].map((item) => (
              <Box
                key={item.label}
                sx={{
                  minWidth: 120,
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
                <Typography variant="body2" fontWeight="bold" sx={{ color: item.color, fontFamily: "'JetBrains Mono', monospace" }}>
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
