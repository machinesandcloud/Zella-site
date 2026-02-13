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
  status?: string;
  entry_time?: string;
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
                primary={`${trade.symbol} ${trade.action} · ${trade.quantity}`}
                secondary={trade.entry_time ? new Date(trade.entry_time).toLocaleString() : "--"}
              />
              <Stack direction="row" spacing={1} alignItems="center">
                <Typography variant="body2">PnL: {trade.pnl ?? 0}</Typography>
                <Chip label={trade.status || "closed"} size="small" />
              </Stack>
            </ListItem>
          ))}
        </List>
      </CardContent>
    </Card>
  );
};

export default TradeHistory;
