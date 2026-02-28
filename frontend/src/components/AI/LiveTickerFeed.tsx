import { useEffect, useState, useRef, useCallback } from "react";
import {
  Card,
  CardContent,
  Typography,
  Box,
  Stack,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  TextField,
  Tooltip,
  LinearProgress,
  Alert,
  Divider,
  Badge
} from "@mui/material";
import {
  TrendingUp,
  TrendingDown,
  TrendingFlat,
  Wifi,
  WifiOff,
  Add,
  Close,
  Speed,
  ShowChart
} from "@mui/icons-material";

interface TickerData {
  symbol: string;
  price: number;
  bid: number;
  ask: number;
  spread: number;
  change: number;
  change_pct: number;
  direction: "up" | "down" | "flat";
  bid_size: number;
  ask_size: number;
  // New fields
  open: number;
  prev_close: number;
  high: number;
  low: number;
  vwap: number;
  day_change: number;
  day_change_pct: number;
  volume: number;
}

interface WebSocketMessage {
  channel: string;
  type: string;
  data?: TickerData[];
  symbols?: string[];
  timestamp: string;
  data_source?: string;
  symbols_requested?: number;
  symbols_with_data?: number;
}

const LiveTickerFeed = () => {
  const [tickers, setTickers] = useState<TickerData[]>([]);
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [subscribedSymbols, setSubscribedSymbols] = useState<string[]>([]);
  const [newSymbol, setNewSymbol] = useState("");
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);
  const [updateCount, setUpdateCount] = useState(0);
  const [dataSource, setDataSource] = useState<string>("real");
  const [symbolsRequested, setSymbolsRequested] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const getWebSocketUrl = useCallback(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    // Use production backend if on Netlify, otherwise use env var or localhost
    const isProduction = window.location.hostname.includes("netlify.app");
    const envHost = import.meta.env.VITE_API_URL?.replace(/^https?:\/\//, "");
    const host = isProduction ? "zella-site.onrender.com" : (envHost || "localhost:8000");
    const symbols = subscribedSymbols.length > 0 ? subscribedSymbols.join(",") : "";
    return `${protocol}//${host}/ws/live-ticker${symbols ? `?symbols=${symbols}` : ""}`;
  }, [subscribedSymbols]);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setConnecting(true);
    setError(null);

    try {
      const ws = new WebSocket(getWebSocketUrl());

      ws.onopen = () => {
        setConnected(true);
        setConnecting(false);
        setError(null);
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);

          if (message.type === "subscribed") {
            setSubscribedSymbols(message.symbols || []);
          } else if (message.type === "update" && message.data) {
            setTickers(message.data);
            setLastUpdate(message.timestamp);
            setUpdateCount((prev) => prev + 1);
            setDataSource(message.data_source || "real");
            setSymbolsRequested(message.symbols_requested || 0);
          }
        } catch (e) {
          console.error("Error parsing WebSocket message:", e);
        }
      };

      ws.onerror = () => {
        setError("WebSocket connection error");
        setConnected(false);
        setConnecting(false);
      };

      ws.onclose = () => {
        setConnected(false);
        setConnecting(false);

        // Auto-reconnect after 2 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, 2000);
      };

      wsRef.current = ws;
    } catch (e) {
      setError("Failed to connect to WebSocket");
      setConnecting(false);
    }
  }, [getWebSocketUrl]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnected(false);
    setTickers([]);
  }, []);

  const addSymbol = () => {
    const symbol = newSymbol.trim().toUpperCase();
    if (symbol && !subscribedSymbols.includes(symbol)) {
      const updated = [...subscribedSymbols, symbol];
      setSubscribedSymbols(updated);
      setNewSymbol("");
      // Reconnect with new symbols
      disconnect();
      setTimeout(() => connect(), 100);
    }
  };

  const removeSymbol = (symbol: string) => {
    const updated = subscribedSymbols.filter((s) => s !== symbol);
    setSubscribedSymbols(updated);
    // Reconnect with updated symbols
    disconnect();
    setTimeout(() => connect(), 100);
  };

  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, []);

  const getDirectionIcon = (direction: string) => {
    switch (direction) {
      case "up":
        return <TrendingUp sx={{ fontSize: 16, color: "success.main" }} />;
      case "down":
        return <TrendingDown sx={{ fontSize: 16, color: "error.main" }} />;
      default:
        return <TrendingFlat sx={{ fontSize: 16, color: "text.secondary" }} />;
    }
  };

  const formatPrice = (price: number) => {
    return price.toLocaleString("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  };

  const formatVolume = (volume: number) => {
    if (volume >= 1000000) return `${(volume / 1000000).toFixed(1)}M`;
    if (volume >= 1000) return `${(volume / 1000).toFixed(1)}K`;
    return volume.toString();
  };

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        {/* Header */}
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 2 }}>
          <Stack direction="row" alignItems="center" spacing={2}>
            <ShowChart sx={{ fontSize: 28, color: "primary.main" }} />
            <Box>
              <Stack direction="row" alignItems="center" spacing={1}>
                <Typography variant="h6" fontWeight="bold">
                  Live Ticker Feed
                </Typography>
                <Badge
                  badgeContent={connected ? "LIVE" : "OFF"}
                  color={connected ? "success" : "error"}
                  sx={{
                    "& .MuiBadge-badge": {
                      fontSize: "0.6rem",
                      height: 16,
                      minWidth: 32,
                    },
                  }}
                />
              </Stack>
              <Typography variant="body2" color="text.secondary">
                Real-time stock prices streaming at 100ms
              </Typography>
            </Box>
          </Stack>

          <Stack direction="row" spacing={1} alignItems="center">
            {connected ? (
              <Chip
                icon={<Wifi />}
                label={`${updateCount} updates`}
                color="success"
                size="small"
                sx={{ animation: "pulse 2s infinite" }}
              />
            ) : connecting ? (
              <Chip
                icon={<Speed />}
                label="Connecting..."
                color="warning"
                size="small"
              />
            ) : (
              <Chip
                icon={<WifiOff />}
                label="Disconnected"
                color="error"
                size="small"
                onClick={connect}
                sx={{ cursor: "pointer" }}
              />
            )}
          </Stack>
        </Stack>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Symbol Input */}
        <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
          <TextField
            size="small"
            placeholder="Add symbol (e.g., AAPL)"
            value={newSymbol}
            onChange={(e) => setNewSymbol(e.target.value.toUpperCase())}
            onKeyPress={(e) => e.key === "Enter" && addSymbol()}
            sx={{ width: 180 }}
          />
          <IconButton size="small" onClick={addSymbol} color="primary">
            <Add />
          </IconButton>
        </Stack>

        {/* Subscribed Symbols */}
        {subscribedSymbols.length > 0 && (
          <Stack direction="row" spacing={0.5} flexWrap="wrap" gap={0.5} sx={{ mb: 2 }}>
            {subscribedSymbols.map((symbol) => (
              <Chip
                key={symbol}
                label={symbol}
                size="small"
                onDelete={() => removeSymbol(symbol)}
                deleteIcon={<Close sx={{ fontSize: 14 }} />}
                sx={{ height: 24 }}
              />
            ))}
          </Stack>
        )}

        <Divider sx={{ mb: 2 }} />

        {/* Ticker Table */}
        {connecting && <LinearProgress sx={{ mb: 2 }} />}

        {tickers.length > 0 ? (
          <TableContainer
            component={Paper}
            elevation={0}
            sx={{ bgcolor: "transparent", maxHeight: 400 }}
          >
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: "bold", bgcolor: "background.paper" }}>Symbol</TableCell>
                  <TableCell align="right" sx={{ fontWeight: "bold", bgcolor: "background.paper" }}>Price</TableCell>
                  <TableCell align="right" sx={{ fontWeight: "bold", bgcolor: "background.paper" }}>Day Chg</TableCell>
                  <TableCell align="right" sx={{ fontWeight: "bold", bgcolor: "background.paper" }}>Open</TableCell>
                  <TableCell align="right" sx={{ fontWeight: "bold", bgcolor: "background.paper" }}>Prev Close</TableCell>
                  <TableCell align="right" sx={{ fontWeight: "bold", bgcolor: "background.paper" }}>Bid</TableCell>
                  <TableCell align="right" sx={{ fontWeight: "bold", bgcolor: "background.paper" }}>Ask</TableCell>
                  <TableCell align="right" sx={{ fontWeight: "bold", bgcolor: "background.paper" }}>Volume</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {tickers.map((ticker) => (
                  <TableRow
                    key={ticker.symbol}
                    sx={{
                      transition: "background-color 0.2s",
                      bgcolor:
                        ticker.direction === "up"
                          ? "rgba(46, 125, 50, 0.08)"
                          : ticker.direction === "down"
                          ? "rgba(211, 47, 47, 0.08)"
                          : "transparent",
                      "&:hover": { bgcolor: "rgba(255,255,255,0.05)" },
                    }}
                  >
                    <TableCell>
                      <Stack direction="row" alignItems="center" spacing={1}>
                        {getDirectionIcon(ticker.direction)}
                        <Typography variant="body2" fontWeight="bold">
                          {ticker.symbol}
                        </Typography>
                      </Stack>
                    </TableCell>
                    <TableCell align="right">
                      <Typography
                        variant="body2"
                        fontWeight="bold"
                        sx={{
                          color:
                            ticker.direction === "up"
                              ? "success.main"
                              : ticker.direction === "down"
                              ? "error.main"
                              : "text.primary",
                        }}
                      >
                        {formatPrice(ticker.price)}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Stack direction="row" alignItems="center" justifyContent="flex-end" spacing={0.5}>
                        <Typography
                          variant="caption"
                          sx={{
                            color:
                              ticker.day_change >= 0 ? "success.main" : "error.main",
                          }}
                        >
                          {ticker.day_change >= 0 ? "+" : ""}
                          {formatPrice(ticker.day_change)}
                        </Typography>
                        <Chip
                          label={`${ticker.day_change_pct >= 0 ? "+" : ""}${ticker.day_change_pct.toFixed(2)}%`}
                          size="small"
                          sx={{
                            height: 18,
                            fontSize: "0.65rem",
                            bgcolor:
                              ticker.day_change_pct >= 0
                                ? "rgba(46, 125, 50, 0.2)"
                                : "rgba(211, 47, 47, 0.2)",
                            color:
                              ticker.day_change_pct >= 0
                                ? "success.main"
                                : "error.main",
                          }}
                        />
                      </Stack>
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="caption" color="text.primary">
                        {formatPrice(ticker.open)}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="caption" color="text.secondary">
                        {formatPrice(ticker.prev_close)}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="caption" color="success.main">
                        {formatPrice(ticker.bid)}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="caption" color="error.main">
                        {formatPrice(ticker.ask)}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Tooltip title={`VWAP: ${formatPrice(ticker.vwap)} | High: ${formatPrice(ticker.high)} | Low: ${formatPrice(ticker.low)}`}>
                        <Typography variant="caption" color="text.secondary">
                          {formatVolume(ticker.volume)}
                        </Typography>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        ) : connected ? (
          <Box sx={{ textAlign: "center", py: 4 }}>
            {dataSource === "unavailable" ? (
              <>
                <Box sx={{ mb: 2, p: 2, borderRadius: 2, bgcolor: "rgba(255, 152, 0, 0.1)", border: "1px solid rgba(255, 152, 0, 0.3)" }}>
                  <Typography variant="body2" color="warning.main" fontWeight="bold">
                    Market Closed or Data Unavailable
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
                    Real-time prices are only available during market hours (9:30 AM - 4:00 PM ET).
                    {symbolsRequested > 0 && ` Requested ${symbolsRequested} symbols.`}
                  </Typography>
                </Box>
              </>
            ) : (
              <Typography variant="body2" color="text.secondary">
                Connecting to market data feed...
              </Typography>
            )}
          </Box>
        ) : (
          <Box sx={{ textAlign: "center", py: 4 }}>
            <WifiOff sx={{ fontSize: 48, color: "text.secondary", mb: 1 }} />
            <Typography variant="body2" color="text.secondary">
              Not connected. Click to connect.
            </Typography>
          </Box>
        )}

        {/* Footer */}
        <Box sx={{ mt: 2, pt: 1, borderTop: "1px solid rgba(255,255,255,0.06)" }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Typography variant="caption" color="text.secondary">
              {tickers.length} symbols streaming
            </Typography>
            {lastUpdate && (
              <Typography variant="caption" color="text.secondary">
                Last update: {new Date(lastUpdate).toLocaleTimeString()}
              </Typography>
            )}
          </Stack>
        </Box>
      </CardContent>
    </Card>
  );
};

export default LiveTickerFeed;
