import { useEffect, useState } from "react";
import { Card, CardContent, Grid, Typography } from "@mui/material";
import { connectWebSocket } from "../../services/websocket";

type BookLevel = { price: number; size: number };
type OrderBookMessage = {
  channel: string;
  symbol: string;
  mid: number;
  spread: number;
  bids: BookLevel[];
  asks: BookLevel[];
  timestamp: string;
};

const OrderBook = () => {
  const [book, setBook] = useState<OrderBookMessage | null>(null);

  useEffect(() => {
    const ws = connectWebSocket("/ws/order-book?symbol=AAPL", (msg) => {
      const data = msg as OrderBookMessage;
      if (data.channel === "order-book") {
        setBook(data);
      }
    });
    return () => ws.close();
  }, []);

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 1 }}>
          Order Book (Level 2)
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {book ? `Mid: ${book.mid} | Spread: ${book.spread}` : "Loading..."}
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={6}>
            <Typography variant="overline">Bids</Typography>
            {book?.bids?.slice(0, 8).map((bid, idx) => (
              <Typography key={`bid-${idx}`} variant="body2">
                {bid.price} × {bid.size}
              </Typography>
            ))}
          </Grid>
          <Grid item xs={6}>
            <Typography variant="overline">Asks</Typography>
            {book?.asks?.slice(0, 8).map((ask, idx) => (
              <Typography key={`ask-${idx}`} variant="body2">
                {ask.price} × {ask.size}
              </Typography>
            ))}
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
};

export default OrderBook;
