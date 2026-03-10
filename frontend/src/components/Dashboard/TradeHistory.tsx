import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  Chip,
  Stack,
  Typography,
  ToggleButton,
  ToggleButtonGroup,
  Box,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TableContainer,
  Paper,
  Alert
} from "@mui/material";
import { fetchRecentTrades } from "../../services/api";

type TradeRow = {
  symbol: string;
  action: string;
  quantity: number;
  pnl: number;
  pnl_percent?: number;
  status?: string;
  entry_time?: string;
  exit_time?: string;
  entry_price?: number;
  exit_price?: number;
  strategy_name?: string;
  confidence?: number;
  setup_grade?: string;
};

const toNumber = (value: unknown, fallback = 0): number => {
  if (value === null || value === undefined) return fallback;
  const num = typeof value === "number" ? value : Number(value);
  return Number.isFinite(num) ? num : fallback;
};

const formatCurrency = (value: number): string => {
  const sign = value >= 0 ? "+" : "";
  return `${sign}$${Math.abs(value).toFixed(2)}`;
};

const formatDateTime = (dateStr?: string): string => {
  if (!dateStr) return "-";
  return new Date(dateStr).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
};

const TradeHistory = () => {
  const [trades, setTrades] = useState<TradeRow[]>([]);
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const cacheKey = `zella_trades_recent_${days}`;
    const cached = localStorage.getItem(cacheKey);
    if (cached) {
      try {
        setTrades(JSON.parse(cached));
        setLoading(false);
      } catch {
        // ignore cache parse errors
      }
    }

    const load = async () => {
      try {
        const data = await fetchRecentTrades(days, 100);
        setTrades(data || []);
        localStorage.setItem(cacheKey, JSON.stringify(data || []));
      } catch {
        setTrades([]);
      } finally {
        setLoading(false);
      }
    };

    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, [days]);

  const closedTrades = trades.filter((trade) => {
    const status = (trade.status || "").toLowerCase();
    if (status === "open") return false;
    return status === "closed" || Boolean(trade.exit_time);
  });
  const openTrades = trades.length - closedTrades.length;
  const totalPnl = closedTrades.reduce((sum, t) => sum + toNumber(t.pnl, 0), 0);
  const wins = closedTrades.filter((t) => toNumber(t.pnl, 0) > 0).length;
  const losses = closedTrades.filter((t) => toNumber(t.pnl, 0) < 0).length;
  const winRate = closedTrades.length ? Math.round((wins / closedTrades.length) * 100) : 0;

  return (
    <Card elevation={0} sx={{ border: "1px solid rgba(255,255,255,0.1)", borderRadius: 3 }}>
      <CardContent sx={{ p: 3 }}>
        {/* Header */}
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>Trade Log</Typography>
          <ToggleButtonGroup
            size="small"
            value={days}
            exclusive
            onChange={(_, value) => value && setDays(value)}
          >
            <ToggleButton value={1}>Today</ToggleButton>
            <ToggleButton value={7}>7 Days</ToggleButton>
            <ToggleButton value={30}>30 Days</ToggleButton>
          </ToggleButtonGroup>
        </Stack>

        {/* Summary Stats */}
        <Stack direction="row" spacing={2} sx={{ mb: 3 }}>
          <Box sx={{ p: 2, borderRadius: 2, bgcolor: "rgba(255,255,255,0.03)", flex: 1, textAlign: "center" }}>
            <Typography variant="caption" color="text.secondary">Closed P&L</Typography>
            <Typography
              variant="h6"
              sx={{
                fontWeight: 700,
                color: totalPnl >= 0 ? "success.main" : "error.main",
                fontFamily: "'JetBrains Mono', monospace"
              }}
            >
              {formatCurrency(totalPnl)}
            </Typography>
          </Box>
          <Box sx={{ p: 2, borderRadius: 2, bgcolor: "rgba(255,255,255,0.03)", flex: 1, textAlign: "center" }}>
            <Typography variant="caption" color="text.secondary">Trades (Closed / Open)</Typography>
            <Typography variant="h6" sx={{ fontWeight: 700 }}>
              {closedTrades.length} / {openTrades}
            </Typography>
          </Box>
          <Box sx={{ p: 2, borderRadius: 2, bgcolor: "rgba(255,255,255,0.03)", flex: 1, textAlign: "center" }}>
            <Typography variant="caption" color="text.secondary">Win Rate</Typography>
            <Typography
              variant="h6"
              sx={{ fontWeight: 700, color: winRate >= 50 ? "success.main" : "warning.main" }}
            >
              {winRate}%
            </Typography>
          </Box>
          <Box sx={{ p: 2, borderRadius: 2, bgcolor: "rgba(255,255,255,0.03)", flex: 1, textAlign: "center" }}>
            <Typography variant="caption" color="text.secondary">W / L</Typography>
            <Typography variant="h6" sx={{ fontWeight: 700 }}>
              <span style={{ color: "#22c55e" }}>{wins}</span>
              {" / "}
              <span style={{ color: "#ef4444" }}>{losses}</span>
            </Typography>
          </Box>
        </Stack>

        {/* Trades Table */}
        {loading ? (
          <Box sx={{ textAlign: "center", py: 4 }}>
            <Typography color="text.secondary">Loading trades...</Typography>
          </Box>
        ) : trades.length === 0 ? (
          <Alert severity="info">
            No trades recorded in this period. Trades will appear here once the bot executes them.
          </Alert>
        ) : (
          <TableContainer
            component={Paper}
            sx={{
              bgcolor: "rgba(255,255,255,0.02)",
              border: "1px solid rgba(255,255,255,0.1)",
              maxHeight: 400
            }}
          >
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600, bgcolor: "rgba(0,0,0,0.3)" }}>Symbol</TableCell>
                  <TableCell sx={{ fontWeight: 600, bgcolor: "rgba(0,0,0,0.3)" }}>Action</TableCell>
                  <TableCell sx={{ fontWeight: 600, bgcolor: "rgba(0,0,0,0.3)" }} align="right">Qty</TableCell>
                  <TableCell sx={{ fontWeight: 600, bgcolor: "rgba(0,0,0,0.3)" }} align="right">Entry</TableCell>
                  <TableCell sx={{ fontWeight: 600, bgcolor: "rgba(0,0,0,0.3)" }} align="right">Exit</TableCell>
                  <TableCell sx={{ fontWeight: 600, bgcolor: "rgba(0,0,0,0.3)" }} align="right">P&L</TableCell>
                  <TableCell sx={{ fontWeight: 600, bgcolor: "rgba(0,0,0,0.3)" }}>Strategy</TableCell>
                  <TableCell sx={{ fontWeight: 600, bgcolor: "rgba(0,0,0,0.3)" }}>Time</TableCell>
                  <TableCell sx={{ fontWeight: 600, bgcolor: "rgba(0,0,0,0.3)" }}>Status</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {trades.map((trade, idx) => {
                  const pnl = toNumber(trade.pnl, 0);
                  const pnlPercent = toNumber(trade.pnl_percent, 0);
                  const isProfitable = pnl >= 0;

                  return (
                    <TableRow
                      key={`${trade.symbol}-${idx}`}
                      sx={{ "&:hover": { bgcolor: "rgba(255,255,255,0.05)" } }}
                    >
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {trade.symbol}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={trade.action}
                          size="small"
                          sx={{
                            height: 20,
                            fontSize: "0.7rem",
                            bgcolor: trade.action === "BUY" ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.15)",
                            color: trade.action === "BUY" ? "#22c55e" : "#ef4444"
                          }}
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2">{trade.quantity}</Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2" sx={{ fontFamily: "'JetBrains Mono', monospace" }}>
                          ${toNumber(trade.entry_price, 0).toFixed(2)}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2" sx={{ fontFamily: "'JetBrains Mono', monospace" }}>
                          {trade.exit_price ? `$${toNumber(trade.exit_price, 0).toFixed(2)}` : "-"}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography
                          variant="body2"
                          sx={{
                            fontWeight: 600,
                            fontFamily: "'JetBrains Mono', monospace",
                            color: isProfitable ? "success.main" : "error.main"
                          }}
                        >
                          {formatCurrency(pnl)}
                          {pnlPercent !== 0 && (
                            <Typography
                              component="span"
                              variant="caption"
                              sx={{ ml: 0.5, color: "text.secondary" }}
                            >
                              ({pnlPercent.toFixed(1)}%)
                            </Typography>
                          )}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        {trade.strategy_name ? (
                          <Chip
                            label={trade.strategy_name}
                            size="small"
                            variant="outlined"
                            sx={{ height: 20, fontSize: "0.65rem" }}
                          />
                        ) : (
                          <Typography variant="caption" color="text.secondary">-</Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption" color="text.secondary">
                          {formatDateTime(trade.exit_time || trade.entry_time)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={trade.status || "closed"}
                          size="small"
                          sx={{
                            height: 20,
                            fontSize: "0.65rem",
                            bgcolor: trade.status === "open" ? "rgba(251,191,36,0.15)" : "rgba(255,255,255,0.05)",
                            color: trade.status === "open" ? "#fbbf24" : "text.secondary"
                          }}
                        />
                      </TableCell>
                    </TableRow>
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

export default TradeHistory;
