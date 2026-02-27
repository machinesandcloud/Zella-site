import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  Chip,
  List,
  ListItem,
  ListItemText,
  Stack,
  Typography
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
};

const TradeHistory = () => {
  const [trades, setTrades] = useState<TradeRow[]>([]);

  useEffect(() => {
    fetchRecentTrades()
      .then((data) => setTrades(data || []))
      .catch(() => setTrades([]));
  }, []);

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Recent Trades
        </Typography>
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
      </CardContent>
    </Card>
  );
};

export default TradeHistory;
