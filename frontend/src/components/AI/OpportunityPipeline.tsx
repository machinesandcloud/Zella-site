import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  Typography,
  Box,
  Stack,
  Chip,
  LinearProgress,
  Avatar,
  Divider,
  IconButton,
  Collapse,
  Button
} from "@mui/material";
import {
  ExpandMore,
  ExpandLess,
  CheckCircle,
  Schedule,
  Star,
  TrendingUp,
  Info
} from "@mui/icons-material";

interface Opportunity {
  id: string;
  symbol: string;
  action: "BUY" | "SELL";
  confidence: number;
  num_strategies: number;
  strategies: string[];
  current_price: number;
  target_price: number;
  stop_loss: number;
  reasoning: string;
  status: "analyzing" | "ready" | "executing" | "filled" | "rejected";
  ml_score: number;
  momentum_score: number;
  risk_reward_ratio: number;
}

const OpportunityPipeline = () => {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    // Simulate opportunity pipeline - replace with real API
    const mockOpportunities: Opportunity[] = [
      {
        id: "1",
        symbol: "NVDA",
        action: "BUY",
        confidence: 0.87,
        num_strategies: 5,
        strategies: ["breakout", "momentum", "ema_cross", "htf_ema_momentum", "trend_follow"],
        current_price: 485.20,
        target_price: 495.50,
        stop_loss: 480.00,
        reasoning: "Strong breakout above resistance with high volume confirmation",
        status: "ready",
        ml_score: 0.82,
        momentum_score: 0.91,
        risk_reward_ratio: 2.1
      },
      {
        id: "2",
        symbol: "TSLA",
        action: "BUY",
        confidence: 0.74,
        num_strategies: 4,
        strategies: ["pullback", "vwap_bounce", "rsi_exhaustion", "range_trading"],
        current_price: 242.15,
        target_price: 248.00,
        stop_loss: 239.50,
        reasoning: "Mean reversion setup at support level with oversold RSI",
        status: "analyzing",
        ml_score: 0.71,
        momentum_score: 0.76,
        risk_reward_ratio: 1.8
      },
      {
        id: "3",
        symbol: "AMD",
        action: "BUY",
        confidence: 0.69,
        num_strategies: 3,
        strategies: ["scalping", "orb", "big_bid_scalp"],
        current_price: 156.80,
        target_price: 159.20,
        stop_loss: 155.60,
        reasoning: "Opening range breakout with institutional bid support",
        status: "analyzing",
        ml_score: 0.66,
        momentum_score: 0.72,
        risk_reward_ratio: 1.5
      }
    ];

    setOpportunities(mockOpportunities);

    // Simulate status updates
    const interval = setInterval(() => {
      setOpportunities(prev => prev.map(opp => {
        if (opp.status === "analyzing" && Math.random() > 0.7) {
          return { ...opp, status: Math.random() > 0.5 ? "ready" : "analyzing" };
        }
        return opp;
      }));
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: Opportunity["status"]) => {
    switch (status) {
      case "analyzing":
        return "warning";
      case "ready":
        return "success";
      case "executing":
        return "info";
      case "filled":
        return "success";
      case "rejected":
        return "error";
      default:
        return "default";
    }
  };

  const getStatusIcon = (status: Opportunity["status"]) => {
    switch (status) {
      case "analyzing":
        return <Schedule />;
      case "ready":
        return <CheckCircle />;
      case "executing":
        return <TrendingUp />;
      default:
        return <Info />;
    }
  };

  const readyOpps = opportunities.filter(o => o.status === "ready").length;
  const analyzingOpps = opportunities.filter(o => o.status === "analyzing").length;

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        {/* Header */}
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
          <Box>
            <Typography variant="h6" fontWeight="bold">
              Opportunity Pipeline
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Ranked trading opportunities awaiting execution
            </Typography>
          </Box>
          <Stack direction="row" spacing={1}>
            <Chip
              icon={<CheckCircle />}
              label={`${readyOpps} Ready`}
              color="success"
              size="small"
            />
            <Chip
              icon={<Schedule />}
              label={`${analyzingOpps} Analyzing`}
              color="warning"
              size="small"
            />
          </Stack>
        </Stack>

        {/* Pipeline Summary */}
        <Box sx={{ mb: 3 }}>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
            <Typography variant="caption" color="text.secondary">
              Pipeline Status
            </Typography>
            <Typography variant="caption" fontWeight="bold">
              {readyOpps} / {opportunities.length} ready to trade
            </Typography>
          </Stack>
          <LinearProgress
            variant="determinate"
            value={opportunities.length > 0 ? (readyOpps / opportunities.length) * 100 : 0}
            sx={{
              height: 6,
              borderRadius: 3,
              bgcolor: "rgba(255,255,255,0.05)",
              "& .MuiLinearProgress-bar": {
                borderRadius: 3,
                background: "linear-gradient(90deg, #4caf50, #81c784)"
              }
            }}
          />
        </Box>

        {/* Opportunities List */}
        {opportunities.length > 0 ? (
          <Stack spacing={2}>
            {opportunities.map((opp, idx) => (
              <Box
                key={opp.id}
                sx={{
                  borderRadius: 2,
                  border: "1px solid rgba(255,255,255,0.08)",
                  background: opp.status === "ready"
                    ? "linear-gradient(135deg, rgba(46, 125, 50, 0.08), rgba(46, 125, 50, 0.02))"
                    : "rgba(255,255,255,0.02)",
                  overflow: "hidden",
                  transition: "all 0.2s",
                  "&:hover": {
                    borderColor: "primary.main",
                    background: opp.status === "ready"
                      ? "linear-gradient(135deg, rgba(46, 125, 50, 0.12), rgba(46, 125, 50, 0.04))"
                      : "rgba(255,255,255,0.04)"
                  }
                }}
              >
                {/* Main Content */}
                <Stack direction="row" spacing={2} alignItems="center" sx={{ p: 2 }}>
                  {/* Rank Badge */}
                  <Avatar
                    sx={{
                      width: 40,
                      height: 40,
                      bgcolor: idx === 0 ? "warning.main" : "rgba(255,255,255,0.1)",
                      fontWeight: "bold"
                    }}
                  >
                    {idx === 0 ? <Star /> : idx + 1}
                  </Avatar>

                  {/* Symbol & Action */}
                  <Box sx={{ flex: 1 }}>
                    <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }}>
                      <Typography variant="h6" fontWeight="bold">
                        {opp.symbol}
                      </Typography>
                      <Chip
                        label={opp.action}
                        color={opp.action === "BUY" ? "success" : "error"}
                        size="small"
                        sx={{ height: 22 }}
                      />
                      <Chip
                        icon={getStatusIcon(opp.status)}
                        label={opp.status.toUpperCase()}
                        color={getStatusColor(opp.status)}
                        size="small"
                        sx={{ height: 22 }}
                      />
                    </Stack>
                    <Typography variant="caption" color="text.secondary">
                      {opp.num_strategies} strategies agree • {(opp.confidence * 100).toFixed(0)}% confidence
                    </Typography>
                  </Box>

                  {/* Price Info */}
                  <Box sx={{ textAlign: "right", minWidth: 100 }}>
                    <Typography variant="body2" color="text.secondary">
                      Current
                    </Typography>
                    <Typography variant="h6" fontWeight="bold">
                      ${opp.current_price.toFixed(2)}
                    </Typography>
                  </Box>

                  {/* Confidence Bar */}
                  <Box sx={{ width: 80 }}>
                    <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.5 }}>
                      Confidence
                    </Typography>
                    <Box sx={{ position: "relative" }}>
                      <LinearProgress
                        variant="determinate"
                        value={opp.confidence * 100}
                        sx={{
                          height: 8,
                          borderRadius: 4,
                          bgcolor: "rgba(255,255,255,0.05)",
                          "& .MuiLinearProgress-bar": {
                            borderRadius: 4,
                            background: opp.confidence > 0.75
                              ? "linear-gradient(90deg, #4caf50, #81c784)"
                              : "linear-gradient(90deg, #ff9800, #ffb74d)"
                          }
                        }}
                      />
                      <Typography
                        variant="caption"
                        fontWeight="bold"
                        sx={{
                          position: "absolute",
                          top: -1,
                          right: 0,
                          fontSize: "0.65rem"
                        }}
                      >
                        {(opp.confidence * 100).toFixed(0)}%
                      </Typography>
                    </Box>
                  </Box>

                  {/* Expand Button */}
                  <IconButton
                    size="small"
                    onClick={() => setExpanded(expanded === opp.id ? null : opp.id)}
                  >
                    {expanded === opp.id ? <ExpandLess /> : <ExpandMore />}
                  </IconButton>
                </Stack>

                {/* Expanded Details */}
                <Collapse in={expanded === opp.id}>
                  <Divider />
                  <Box sx={{ p: 2, bgcolor: "rgba(0,0,0,0.2)" }}>
                    {/* Reasoning */}
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="caption" color="text.secondary" fontWeight="bold">
                        Reasoning
                      </Typography>
                      <Typography variant="body2" sx={{ mt: 0.5 }}>
                        {opp.reasoning}
                      </Typography>
                    </Box>

                    {/* Strategies */}
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="caption" color="text.secondary" fontWeight="bold">
                        Supporting Strategies
                      </Typography>
                      <Stack direction="row" spacing={0.5} sx={{ mt: 0.5, flexWrap: "wrap", gap: 0.5 }}>
                        {opp.strategies.map(strategy => (
                          <Chip
                            key={strategy}
                            label={strategy.replace(/_/g, " ")}
                            size="small"
                            sx={{ height: 20, fontSize: "0.65rem" }}
                          />
                        ))}
                      </Stack>
                    </Box>

                    {/* Trading Plan */}
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="caption" color="text.secondary" fontWeight="bold">
                        Trading Plan
                      </Typography>
                      <Stack spacing={1} sx={{ mt: 1 }}>
                        <Stack direction="row" justifyContent="space-between">
                          <Typography variant="caption">Entry Price:</Typography>
                          <Typography variant="caption" fontWeight="bold">
                            ${opp.current_price.toFixed(2)}
                          </Typography>
                        </Stack>
                        <Stack direction="row" justifyContent="space-between">
                          <Typography variant="caption">Target Price:</Typography>
                          <Typography variant="caption" fontWeight="bold" color="success.main">
                            ${opp.target_price.toFixed(2)} (+{((opp.target_price / opp.current_price - 1) * 100).toFixed(1)}%)
                          </Typography>
                        </Stack>
                        <Stack direction="row" justifyContent="space-between">
                          <Typography variant="caption">Stop Loss:</Typography>
                          <Typography variant="caption" fontWeight="bold" color="error.main">
                            ${opp.stop_loss.toFixed(2)} (-{((1 - opp.stop_loss / opp.current_price) * 100).toFixed(1)}%)
                          </Typography>
                        </Stack>
                        <Stack direction="row" justifyContent="space-between">
                          <Typography variant="caption">Risk/Reward:</Typography>
                          <Typography variant="caption" fontWeight="bold" color="primary.main">
                            {opp.risk_reward_ratio.toFixed(1)}:1
                          </Typography>
                        </Stack>
                      </Stack>
                    </Box>

                    {/* Scores */}
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="caption" color="text.secondary" fontWeight="bold">
                        ML Scores
                      </Typography>
                      <Stack direction="row" spacing={2} sx={{ mt: 1 }}>
                        <Box sx={{ flex: 1 }}>
                          <Typography variant="caption" color="text.secondary">ML Score</Typography>
                          <LinearProgress
                            variant="determinate"
                            value={opp.ml_score * 100}
                            sx={{ mt: 0.5, height: 6, borderRadius: 3 }}
                          />
                          <Typography variant="caption" fontWeight="bold">
                            {(opp.ml_score * 100).toFixed(0)}%
                          </Typography>
                        </Box>
                        <Box sx={{ flex: 1 }}>
                          <Typography variant="caption" color="text.secondary">Momentum</Typography>
                          <LinearProgress
                            variant="determinate"
                            value={opp.momentum_score * 100}
                            sx={{ mt: 0.5, height: 6, borderRadius: 3 }}
                          />
                          <Typography variant="caption" fontWeight="bold">
                            {(opp.momentum_score * 100).toFixed(0)}%
                          </Typography>
                        </Box>
                      </Stack>
                    </Box>

                    {/* Action Buttons */}
                    {opp.status === "ready" && (
                      <Stack direction="row" spacing={1}>
                        <Button
                          variant="contained"
                          color="success"
                          size="small"
                          fullWidth
                          onClick={() => {
                            window.dispatchEvent(new CustomEvent("app:toast", {
                              detail: { message: `Executing ${opp.action} order for ${opp.symbol}...`, severity: "info" }
                            }));
                          }}
                        >
                          Execute Trade
                        </Button>
                        <Button
                          variant="outlined"
                          color="error"
                          size="small"
                          onClick={() => {
                            window.dispatchEvent(new CustomEvent("app:toast", {
                              detail: { message: `Opportunity for ${opp.symbol} rejected`, severity: "warning" }
                            }));
                          }}
                        >
                          Reject
                        </Button>
                      </Stack>
                    )}
                  </Box>
                </Collapse>
              </Box>
            ))}
          </Stack>
        ) : (
          <Box
            sx={{
              p: 4,
              textAlign: "center",
              borderRadius: 2,
              bgcolor: "rgba(255,255,255,0.02)",
              border: "1px dashed rgba(255,255,255,0.1)"
            }}
          >
            <Typography variant="body2" color="text.secondary">
              No opportunities in pipeline. The autonomous engine will populate this when it finds high-quality setups.
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default OpportunityPipeline;
