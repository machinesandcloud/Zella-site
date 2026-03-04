import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  Chip,
  List,
  ListItem,
  ListItemText,
  Stack,
  Typography,
  ToggleButton,
  ToggleButtonGroup,
  Divider,
  Box
} from "@mui/material";
import { fetchRecentTrades, fetchLearningSummary } from "../../services/api";

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
  strategies?: string;
  entry_reason?: string;
};

const TradeHistory = () => {
  const [trades, setTrades] = useState<TradeRow[]>([]);
  const [days, setDays] = useState(7);
  const [learning, setLearning] = useState<any>(null);

  useEffect(() => {
    fetchRecentTrades(days, 100)
      .then((data) => setTrades(data || []))
      .catch(() => setTrades([]));
  }, [days]);

  useEffect(() => {
    fetchLearningSummary()
      .then((data) => setLearning(data))
      .catch(() => setLearning(null));
  }, []);

  const totalPnl = trades.reduce((sum, t) => sum + (t.pnl || 0), 0);
  const wins = trades.filter((t) => (t.pnl || 0) > 0).length;
  const losses = trades.filter((t) => (t.pnl || 0) < 0).length;
  const winRate = trades.length ? Math.round((wins / trades.length) * 100) : 0;

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
          <Typography variant="h6">Recent Trades</Typography>
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

        <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }}>
          <Typography variant="caption" color="text.secondary">
            Trades: {trades.length}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Win rate: {winRate}%
          </Typography>
          <Typography
            variant="caption"
            color={totalPnl >= 0 ? "success.main" : "error.main"}
          >
            P/L: {totalPnl >= 0 ? "+" : ""}{totalPnl.toFixed(2)}
          </Typography>
        </Stack>

        <Divider sx={{ mb: 2 }} />
        {learning?.summary && (
          <Box sx={{ mb: 2, p: 2, borderRadius: 2, border: "1px solid rgba(255,255,255,0.06)" }}>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>Learning Summary</Typography>
            <Stack direction="row" spacing={2} flexWrap="wrap">
              <Typography variant="caption" color="text.secondary">
                Trades learned: {learning.summary.total_trades_analyzed ?? 0}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Learning cycles: {learning.summary.learning_cycles_completed ?? 0}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Recommended confidence: {learning.summary.recommended_confidence ?? 0}
              </Typography>
            </Stack>
            {learning.recent_insights?.length > 0 && (
              <Stack spacing={0.5} sx={{ mt: 1 }}>
                {learning.recent_insights.map((insight: string, idx: number) => (
                  <Typography key={idx} variant="caption" color="text.secondary">
                    {insight}
                  </Typography>
                ))}
              </Stack>
            )}
          </Box>
        )}
        {trades.length === 0 && (
          <Typography variant="body2" color="text.secondary">
            No trades yet.
          </Typography>
        )}
        <List dense>
          {trades.map((trade, idx) => (
            <ListItem key={`${trade.symbol}-${idx}`} divider>
              <ListItemText
                primary={
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Typography variant="body2" fontWeight={600}>{trade.symbol}</Typography>
                    <Chip
                      label={trade.action}
                      size="small"
                      color={trade.action === "BUY" ? "success" : "error"}
                      sx={{ height: 18, fontSize: "0.65rem" }}
                    />
                    <Typography variant="caption" color="text.secondary">
                      {trade.quantity} shares
                    </Typography>
                    {trade.strategy_name && (
                      <Chip label={trade.strategy_name} size="small" variant="outlined" sx={{ height: 18, fontSize: "0.6rem" }} />
                    )}
                  </Stack>
                }
                secondary={
                  <Stack direction="row" spacing={2} sx={{ mt: 0.5 }}>
                    <Typography variant="caption" color="text.secondary">
                      Entry: {trade.entry_price ? `$${trade.entry_price.toFixed(2)}` : "--"}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Exit: {trade.exit_price ? `$${trade.exit_price.toFixed(2)}` : "--"}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {trade.entry_time ? new Date(trade.entry_time).toLocaleString() : "--"}
                    </Typography>
                    {trade.setup_grade && (
                      <Typography variant="caption" color="text.secondary">
                        Grade: {trade.setup_grade}
                      </Typography>
                    )}
                    {typeof trade.confidence === "number" && (
                      <Typography variant="caption" color="text.secondary">
                        Conf: {Math.round(trade.confidence * 100)}%
                      </Typography>
                    )}
                  </Stack>
                }
              />
              <Stack direction="row" spacing={1} alignItems="center">
                <Typography
                  variant="body2"
                  fontWeight={600}
                  color={(trade.pnl ?? 0) >= 0 ? "success.main" : "error.main"}
                >
                  {(trade.pnl ?? 0) >= 0 ? "+" : ""}{(trade.pnl ?? 0).toFixed(2)}
                  {trade.pnl_percent && ` (${trade.pnl_percent.toFixed(1)}%)`}
                </Typography>
                <Chip
                  label={trade.status || "closed"}
                  size="small"
                  color={trade.status === "open" ? "warning" : "default"}
                />
              </Stack>
            </ListItem>
          ))}
        </List>
        {trades.length > 0 && trades[0].entry_reason && (
          <Typography variant="caption" color="text.secondary">
            Example reason: {trades[0].entry_reason}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

export default TradeHistory;
