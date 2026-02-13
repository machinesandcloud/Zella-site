import { useEffect, useMemo, useState } from "react";
import {
  Button,
  Card,
  CardContent,
  Grid,
  Stack,
  TextField,
  Typography
} from "@mui/material";
import { connectWebSocket } from "../../services/websocket";

type Quote = {
  price: number;
  volume: number;
  open?: number;
};

type MarketDataMessage = {
  channel: string;
  symbol: string;
  price: number;
  volume: number;
  timestamp: string;
};

const DEFAULT_SYMBOLS = ["AAPL", "MSFT", "TSLA", "NVDA"];

const Watchlist = () => {
  const [symbols, setSymbols] = useState<string[]>(() => {
    const stored = localStorage.getItem("zella_watchlist");
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed) && parsed.length) {
          return parsed;
        }
      } catch {
        return DEFAULT_SYMBOLS;
      }
    }
    return DEFAULT_SYMBOLS;
  });
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const [input, setInput] = useState("");

  useEffect(() => {
    const sockets = symbols.map((symbol) =>
      connectWebSocket(`/ws/market-data?symbol=${symbol}`, (msg) => {
        const data = msg as MarketDataMessage;
        if (data.channel !== "market-data" || data.symbol !== symbol) return;
        setQuotes((prev) => {
          const existing = prev[symbol];
          return {
            ...prev,
            [symbol]: {
              price: data.price,
              volume: data.volume,
              open: existing?.open ?? data.price
            }
          };
        });
      })
    );

    return () => {
      sockets.forEach((socket) => socket.close());
    };
  }, [symbols]);

  useEffect(() => {
    localStorage.setItem("zella_watchlist", JSON.stringify(symbols));
  }, [symbols]);

  const addSymbol = () => {
    const next = input.trim().toUpperCase();
    if (!next || symbols.includes(next)) return;
    setSymbols((prev) => [...prev, next]);
    setInput("");
  };

  const removeSymbol = (symbol: string) => {
    setSymbols((prev) => prev.filter((item) => item !== symbol));
    setQuotes((prev) => {
      const next = { ...prev };
      delete next[symbol];
      return next;
    });
  };

  const rows = useMemo(
    () =>
      symbols.map((symbol) => {
        const quote = quotes[symbol];
        const open = quote?.open ?? quote?.price ?? 0;
        const price = quote?.price ?? 0;
        const change = open ? price - open : 0;
        const changePct = open ? (change / open) * 100 : 0;
        return {
          symbol,
          price: price ? price.toFixed(2) : "--",
          change: price ? change.toFixed(2) : "--",
          changePct: price ? `${changePct.toFixed(2)}%` : "--",
          volume: quote?.volume ?? "--"
        };
      }),
    [symbols, quotes]
  );

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Watchlist
        </Typography>
        <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
          <TextField
            size="small"
            label="Add Symbol"
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
          <Button size="small" variant="outlined" onClick={addSymbol}>
            Add
          </Button>
        </Stack>

        <Grid container spacing={1}>
          {rows.map((row) => (
            <Grid item xs={12} key={row.symbol}>
              <Stack
                direction="row"
                spacing={2}
                alignItems="center"
                justifyContent="space-between"
                sx={{ borderBottom: "1px solid #eef2f7", pb: 1 }}
              >
                <Stack direction="row" spacing={2} alignItems="center">
                  <Typography sx={{ minWidth: 60 }}>{row.symbol}</Typography>
                  <Typography variant="body2">${row.price}</Typography>
                  <Typography
                    variant="body2"
                    sx={{ color: Number(row.change) >= 0 ? "var(--success)" : "var(--danger)" }}
                  >
                    {row.change} ({row.changePct})
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Vol {row.volume}
                  </Typography>
                </Stack>
                <Button size="small" onClick={() => removeSymbol(row.symbol)}>
                  Remove
                </Button>
              </Stack>
            </Grid>
          ))}
        </Grid>
      </CardContent>
    </Card>
  );
};

export default Watchlist;
