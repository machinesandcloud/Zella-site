import { useEffect, useState, useCallback } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Stack,
  IconButton,
  Collapse,
  CircularProgress,
  Tabs,
  Tab,
  Tooltip,
  LinearProgress,
  Alert
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import RefreshIcon from "@mui/icons-material/Refresh";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import {
  fetchStrategyPerformanceByPeriod,
  fetchTradesByStrategy
} from "../../services/api";

interface PeriodStats {
  total_pnl: number;
  trades: number;
  wins: number;
  losses: number;
  win_rate: number;
  avg_pnl: number;
}

interface StrategyPerformance {
  strategy: string;
  all_time: PeriodStats;
  daily: PeriodStats;
  three_day: PeriodStats;
  weekly: PeriodStats;
  monthly: PeriodStats;
}

interface Trade {
  id: number;
  symbol: string;
  action: string;
  quantity: number;
  entry_price: number | null;
  exit_price: number | null;
  pnl: number | null;
  pnl_percent: number | null;
  entry_time: string | null;
  exit_time: string | null;
  status: string | null;
  strategy_name: string | null;
}

type TimePeriod = "daily" | "three_day" | "weekly" | "monthly" | "all_time";

const formatPnl = (pnl: number) => {
  const sign = pnl >= 0 ? "+" : "";
  return `${sign}$${pnl.toFixed(2)}`;
};

const formatPercent = (value: number) => {
  return `${value.toFixed(1)}%`;
};

const formatDateTime = (dateStr: string | null) => {
  if (!dateStr) return "-";
  const date = new Date(dateStr);
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
};

const StrategyPerformancePanel = () => {
  const [strategies, setStrategies] = useState<StrategyPerformance[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<TimePeriod>("monthly");
  const [expandedStrategy, setExpandedStrategy] = useState<string | null>(null);
  const [strategyTrades, setStrategyTrades] = useState<Record<string, Trade[]>>({});
  const [tradesLoading, setTradesLoading] = useState<string | null>(null);

  const fetchPerformance = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchStrategyPerformanceByPeriod();
      setStrategies(data.strategies || []);
      setError(null);
    } catch (err) {
      console.error("Failed to fetch strategy performance:", err);
      setError("Failed to load strategy performance");
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchTrades = useCallback(async (strategyName: string) => {
    if (strategyTrades[strategyName]) return; // Already loaded

    setTradesLoading(strategyName);
    try {
      const trades = await fetchTradesByStrategy(strategyName, 50);
      setStrategyTrades(prev => ({
        ...prev,
        [strategyName]: trades
      }));
    } catch (err) {
      console.error(`Failed to fetch trades for ${strategyName}:`, err);
    } finally {
      setTradesLoading(null);
    }
  }, [strategyTrades]);

  useEffect(() => {
    fetchPerformance();
  }, [fetchPerformance]);

  const toggleStrategy = (strategyName: string) => {
    if (expandedStrategy === strategyName) {
      setExpandedStrategy(null);
    } else {
      setExpandedStrategy(strategyName);
      fetchTrades(strategyName);
    }
  };

  const getStatsForPeriod = (strategy: StrategyPerformance, period: TimePeriod): PeriodStats => {
    return strategy[period];
  };

  const periodLabels: Record<TimePeriod, string> = {
    daily: "Today",
    three_day: "3 Days",
    weekly: "7 Days",
    monthly: "30 Days",
    all_time: "All Time"
  };

  // Calculate totals for current period
  const totals = strategies.reduce((acc, s) => {
    const stats = getStatsForPeriod(s, selectedPeriod);
    acc.pnl += stats.total_pnl;
    acc.trades += stats.trades;
    acc.wins += stats.wins;
    acc.losses += stats.losses;
    return acc;
  }, { pnl: 0, trades: 0, wins: 0, losses: 0 });

  if (loading) {
    return (
      <Card elevation={0} sx={{ border: "1px solid rgba(255,255,255,0.1)", borderRadius: 3 }}>
        <CardContent sx={{ p: 3, textAlign: "center" }}>
          <CircularProgress size={24} />
          <Typography sx={{ mt: 1 }}>Loading strategy performance...</Typography>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card elevation={0} sx={{ border: "1px solid rgba(255,255,255,0.1)", borderRadius: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <Alert severity="error">{error}</Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card elevation={0} sx={{ border: "1px solid rgba(255,255,255,0.1)", borderRadius: 3 }}>
      <CardContent sx={{ p: 3 }}>
        {/* Header */}
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
          <Box>
            <Stack direction="row" alignItems="center" spacing={1}>
              <ShowChartIcon color="primary" />
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Strategy Performance
              </Typography>
            </Stack>
            <Typography variant="caption" color="text.secondary">
              {strategies.length} strategies tracked
            </Typography>
          </Box>
          <IconButton size="small" onClick={fetchPerformance}>
            <RefreshIcon fontSize="small" />
          </IconButton>
        </Stack>

        {/* Period Tabs */}
        <Tabs
          value={selectedPeriod}
          onChange={(_, newValue) => setSelectedPeriod(newValue)}
          sx={{ mb: 2, borderBottom: "1px solid rgba(255,255,255,0.1)" }}
          variant="scrollable"
          scrollButtons="auto"
        >
          {(Object.keys(periodLabels) as TimePeriod[]).map(period => (
            <Tab
              key={period}
              value={period}
              label={periodLabels[period]}
              sx={{ textTransform: "none", minWidth: 80 }}
            />
          ))}
        </Tabs>

        {/* Summary Stats */}
        <Stack direction="row" spacing={2} sx={{ mb: 3 }}>
          <Box sx={{ p: 2, borderRadius: 2, bgcolor: "rgba(255,255,255,0.03)", flex: 1, textAlign: "center" }}>
            <Typography variant="caption" color="text.secondary">Total P&L</Typography>
            <Typography
              variant="h5"
              sx={{
                fontWeight: 700,
                color: totals.pnl >= 0 ? "success.main" : "error.main",
                fontFamily: "'JetBrains Mono', monospace"
              }}
            >
              {formatPnl(totals.pnl)}
            </Typography>
          </Box>
          <Box sx={{ p: 2, borderRadius: 2, bgcolor: "rgba(255,255,255,0.03)", flex: 1, textAlign: "center" }}>
            <Typography variant="caption" color="text.secondary">Trades</Typography>
            <Typography variant="h5" sx={{ fontWeight: 700 }}>
              {totals.trades}
            </Typography>
          </Box>
          <Box sx={{ p: 2, borderRadius: 2, bgcolor: "rgba(255,255,255,0.03)", flex: 1, textAlign: "center" }}>
            <Typography variant="caption" color="text.secondary">Win Rate</Typography>
            <Typography
              variant="h5"
              sx={{
                fontWeight: 700,
                color: totals.trades > 0 && (totals.wins / totals.trades) >= 0.5 ? "success.main" : "warning.main"
              }}
            >
              {totals.trades > 0 ? formatPercent((totals.wins / totals.trades) * 100) : "-"}
            </Typography>
          </Box>
          <Box sx={{ p: 2, borderRadius: 2, bgcolor: "rgba(255,255,255,0.03)", flex: 1, textAlign: "center" }}>
            <Typography variant="caption" color="text.secondary">W / L</Typography>
            <Typography variant="h5" sx={{ fontWeight: 700 }}>
              <span style={{ color: "#22c55e" }}>{totals.wins}</span>
              {" / "}
              <span style={{ color: "#ef4444" }}>{totals.losses}</span>
            </Typography>
          </Box>
        </Stack>

        {strategies.length === 0 ? (
          <Alert severity="info">
            No strategy trades recorded yet. Strategy performance will appear here once trades are made.
          </Alert>
        ) : (
          /* Strategy Table */
          <TableContainer
            component={Paper}
            sx={{
              bgcolor: "rgba(255,255,255,0.02)",
              border: "1px solid rgba(255,255,255,0.1)"
            }}
          >
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600 }}>Strategy</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 600 }}>P&L</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 600 }}>Trades</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 600 }}>Win Rate</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 600 }}>W / L</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 600 }}>Avg P&L</TableCell>
                  <TableCell align="center" sx={{ fontWeight: 600 }}></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {strategies.map(strategy => {
                  const stats = getStatsForPeriod(strategy, selectedPeriod);
                  const isExpanded = expandedStrategy === strategy.strategy;
                  const trades = strategyTrades[strategy.strategy] || [];

                  return (
                    <>
                      <TableRow
                        key={strategy.strategy}
                        sx={{
                          cursor: "pointer",
                          "&:hover": { bgcolor: "rgba(255,255,255,0.05)" },
                          bgcolor: isExpanded ? "rgba(25, 118, 210, 0.08)" : "transparent"
                        }}
                        onClick={() => toggleStrategy(strategy.strategy)}
                      >
                        <TableCell>
                          <Stack direction="row" alignItems="center" spacing={1}>
                            {stats.total_pnl >= 0 ? (
                              <TrendingUpIcon sx={{ fontSize: 16, color: "success.main" }} />
                            ) : (
                              <TrendingDownIcon sx={{ fontSize: 16, color: "error.main" }} />
                            )}
                            <Typography variant="body2" sx={{ fontWeight: 600 }}>
                              {strategy.strategy.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())}
                            </Typography>
                          </Stack>
                        </TableCell>
                        <TableCell align="right">
                          <Typography
                            variant="body2"
                            sx={{
                              fontWeight: 600,
                              color: stats.total_pnl >= 0 ? "success.main" : "error.main",
                              fontFamily: "'JetBrains Mono', monospace"
                            }}
                          >
                            {formatPnl(stats.total_pnl)}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2">{stats.trades}</Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Stack direction="row" alignItems="center" justifyContent="flex-end" spacing={1}>
                            <Box sx={{ width: 50 }}>
                              <LinearProgress
                                variant="determinate"
                                value={stats.win_rate}
                                sx={{
                                  height: 6,
                                  borderRadius: 1,
                                  bgcolor: "rgba(255,255,255,0.1)",
                                  "& .MuiLinearProgress-bar": {
                                    bgcolor: stats.win_rate >= 50 ? "success.main" : "warning.main"
                                  }
                                }}
                              />
                            </Box>
                            <Typography
                              variant="body2"
                              sx={{ color: stats.win_rate >= 50 ? "success.main" : "warning.main" }}
                            >
                              {formatPercent(stats.win_rate)}
                            </Typography>
                          </Stack>
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2">
                            <span style={{ color: "#22c55e" }}>{stats.wins}</span>
                            {" / "}
                            <span style={{ color: "#ef4444" }}>{stats.losses}</span>
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography
                            variant="body2"
                            sx={{
                              color: stats.avg_pnl >= 0 ? "success.main" : "error.main",
                              fontFamily: "'JetBrains Mono', monospace"
                            }}
                          >
                            {formatPnl(stats.avg_pnl)}
                          </Typography>
                        </TableCell>
                        <TableCell align="center">
                          <IconButton size="small">
                            {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                          </IconButton>
                        </TableCell>
                      </TableRow>

                      {/* Expanded Trades */}
                      <TableRow>
                        <TableCell colSpan={7} sx={{ p: 0, border: 0 }}>
                          <Collapse in={isExpanded}>
                            <Box sx={{ p: 2, bgcolor: "rgba(0,0,0,0.2)" }}>
                              <Typography variant="subtitle2" sx={{ mb: 1.5, fontWeight: 600 }}>
                                Recent Trades ({trades.length})
                              </Typography>
                              {tradesLoading === strategy.strategy ? (
                                <Box sx={{ textAlign: "center", py: 2 }}>
                                  <CircularProgress size={20} />
                                </Box>
                              ) : trades.length === 0 ? (
                                <Typography variant="body2" color="text.secondary">
                                  No trades recorded for this strategy.
                                </Typography>
                              ) : (
                                <TableContainer>
                                  <Table size="small">
                                    <TableHead>
                                      <TableRow>
                                        <TableCell sx={{ fontSize: "0.75rem" }}>Symbol</TableCell>
                                        <TableCell sx={{ fontSize: "0.75rem" }}>Action</TableCell>
                                        <TableCell align="right" sx={{ fontSize: "0.75rem" }}>Qty</TableCell>
                                        <TableCell align="right" sx={{ fontSize: "0.75rem" }}>Entry</TableCell>
                                        <TableCell align="right" sx={{ fontSize: "0.75rem" }}>Exit</TableCell>
                                        <TableCell align="right" sx={{ fontSize: "0.75rem" }}>P&L</TableCell>
                                        <TableCell align="right" sx={{ fontSize: "0.75rem" }}>Time</TableCell>
                                      </TableRow>
                                    </TableHead>
                                    <TableBody>
                                      {trades.slice(0, 10).map(trade => (
                                        <TableRow key={trade.id}>
                                          <TableCell>
                                            <Typography variant="caption" sx={{ fontWeight: 600 }}>
                                              {trade.symbol}
                                            </Typography>
                                          </TableCell>
                                          <TableCell>
                                            <Chip
                                              label={trade.action}
                                              size="small"
                                              sx={{
                                                height: 18,
                                                fontSize: "0.65rem",
                                                bgcolor: trade.action === "BUY" ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.15)",
                                                color: trade.action === "BUY" ? "#22c55e" : "#ef4444"
                                              }}
                                            />
                                          </TableCell>
                                          <TableCell align="right">
                                            <Typography variant="caption">{trade.quantity}</Typography>
                                          </TableCell>
                                          <TableCell align="right">
                                            <Typography variant="caption" sx={{ fontFamily: "'JetBrains Mono', monospace" }}>
                                              ${trade.entry_price?.toFixed(2) || "-"}
                                            </Typography>
                                          </TableCell>
                                          <TableCell align="right">
                                            <Typography variant="caption" sx={{ fontFamily: "'JetBrains Mono', monospace" }}>
                                              ${trade.exit_price?.toFixed(2) || "-"}
                                            </Typography>
                                          </TableCell>
                                          <TableCell align="right">
                                            <Typography
                                              variant="caption"
                                              sx={{
                                                fontFamily: "'JetBrains Mono', monospace",
                                                color: (trade.pnl || 0) >= 0 ? "success.main" : "error.main",
                                                fontWeight: 600
                                              }}
                                            >
                                              {trade.pnl !== null ? formatPnl(trade.pnl) : "-"}
                                            </Typography>
                                          </TableCell>
                                          <TableCell align="right">
                                            <Typography variant="caption" color="text.secondary">
                                              {formatDateTime(trade.exit_time || trade.entry_time)}
                                            </Typography>
                                          </TableCell>
                                        </TableRow>
                                      ))}
                                    </TableBody>
                                  </Table>
                                </TableContainer>
                              )}

                              {/* Period Comparison */}
                              <Box sx={{ mt: 2, pt: 2, borderTop: "1px solid rgba(255,255,255,0.1)" }}>
                                <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: "block" }}>
                                  P&L by Period
                                </Typography>
                                <Stack direction="row" spacing={1} flexWrap="wrap">
                                  {(["daily", "three_day", "weekly", "monthly", "all_time"] as TimePeriod[]).map(period => {
                                    const pStats = getStatsForPeriod(strategy, period);
                                    return (
                                      <Tooltip key={period} title={`${pStats.trades} trades, ${formatPercent(pStats.win_rate)} win rate`}>
                                        <Chip
                                          label={
                                            <Stack direction="row" spacing={0.5} alignItems="center">
                                              <span>{periodLabels[period]}:</span>
                                              <span style={{
                                                fontWeight: 600,
                                                color: pStats.total_pnl >= 0 ? "#22c55e" : "#ef4444"
                                              }}>
                                                {formatPnl(pStats.total_pnl)}
                                              </span>
                                            </Stack>
                                          }
                                          size="small"
                                          variant={period === selectedPeriod ? "filled" : "outlined"}
                                          sx={{ height: 24, fontSize: "0.7rem" }}
                                        />
                                      </Tooltip>
                                    );
                                  })}
                                </Stack>
                              </Box>
                            </Box>
                          </Collapse>
                        </TableCell>
                      </TableRow>
                    </>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </CardContent>
    </Card>
  );
};

export default StrategyPerformancePanel;
