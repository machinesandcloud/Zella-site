import { useEffect, useState } from "react";
import { Card, CardContent, Typography } from "@mui/material";
import { connectWebSocket } from "../../services/websocket";

type TimeSalesMessage = {
  channel: string;
  symbol: string;
  price: number;
  size: number;
  side: "BUY" | "SELL";
  timestamp: string;
};

const TimeSales = () => {
  const [trades, setTrades] = useState<TimeSalesMessage[]>([]);

  useEffect(() => {
    const ws = connectWebSocket("/ws/time-sales?symbol=AAPL", (msg) => {
      const data = msg as TimeSalesMessage;
      if (data.channel !== "time-sales") return;
      setTrades((prev) => [data, ...prev].slice(0, 12));
    });
    return () => ws.close();
  }, []);

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 1 }}>
          Time & Sales
        </Typography>
        {trades.map((trade, idx) => (
          <Typography
            key={`${trade.timestamp}-${idx}`}
            variant="body2"
            sx={{ color: trade.side === "BUY" ? "var(--success)" : "var(--danger)" }}
          >
            {trade.timestamp.slice(11, 19)} · {trade.side} {trade.size} @ {trade.price}
          </Typography>
        ))}
      </CardContent>
    </Card>
  );
};

export default TimeSales;
