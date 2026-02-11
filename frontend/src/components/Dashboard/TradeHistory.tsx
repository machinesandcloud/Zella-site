import { Card, CardContent, List, ListItem, ListItemText, Typography } from "@mui/material";

const TradeHistory = () => {
  const trades = [
    { symbol: "AAPL", action: "BUY", pnl: 120.5 },
    { symbol: "TSLA", action: "SELL", pnl: -45.1 }
  ];

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Recent Trades
        </Typography>
        <List dense>
          {trades.map((trade, idx) => (
            <ListItem key={`${trade.symbol}-${idx}`}>
              <ListItemText
                primary={`${trade.symbol} ${trade.action}`}
                secondary={`PnL: ${trade.pnl}`}
              />
            </ListItem>
          ))}
        </List>
      </CardContent>
    </Card>
  );
};

export default TradeHistory;
