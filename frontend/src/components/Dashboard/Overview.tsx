import { useEffect, useState } from "react";
import { Box, Card, CardContent, Grid, Stack, Typography } from "@mui/material";
import { fetchAlpacaAccount } from "../../services/api";
import { connectWebSocket, WebSocketConnection } from "../../services/websocket";

const Overview = () => {
  const [summary, setSummary] = useState<Record<string, string>>({});
  const [timestamp, setTimestamp] = useState<string>("");

  useEffect(() => {
    fetchAlpacaAccount()
      .then((data) => {
        setSummary(data || {});
        setTimestamp(new Date().toISOString());
      })
      .catch(() => {
        setSummary({});
      });
  }, []);

  useEffect(() => {
    let ws: WebSocketConnection | null = null;
    try {
      ws = connectWebSocket("/ws/account-updates", (msg) => {
        setTimestamp(msg.timestamp);
      });
    } catch (error) {
      console.warn("WebSocket connection failed:", error);
    }
    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, []);

  const tiles = [
    { label: "Account Value", value: summary.NetLiquidation || "--" },
    { label: "Cash Available", value: summary.CashBalance || "--" },
    { label: "Buying Power", value: summary.BuyingPower || "--" },
    { label: "PnL Today", value: summary.RealizedPnL || "--" },
    { label: "PnL Total", value: summary.UnrealizedPnL || "--" }
  ];

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 2 }}>
        Account Summary
      </Typography>
      <Grid container spacing={2}>
        {tiles.map((tile) => (
          <Grid key={tile.label} item xs={12} sm={6} md={tile.label === "PnL Total" ? 6 : 3}>
            <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
              <CardContent>
                <Typography variant="overline" color="text.secondary">
                  {tile.label}
                </Typography>
                <Typography variant="h6">{tile.value}</Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Stack direction="row" spacing={2} sx={{ mt: 3 }}>
        <Card elevation={0} sx={{ border: "1px solid var(--border)", flex: 1 }}>
          <CardContent>
            <Typography variant="overline" color="text.secondary">
              System Status
            </Typography>
            <Typography variant="body1">Alpaca: {summary ? "Connected" : "Disconnected"}</Typography>
            <Typography variant="body2" color="text.secondary">
              Active strategies: 0
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Last update: {timestamp || "--"}
            </Typography>
          </CardContent>
        </Card>
        <Card elevation={0} sx={{ border: "1px solid var(--border)", flex: 1 }}>
          <CardContent>
            <Typography variant="overline" color="text.secondary">
              Trading Mode
            </Typography>
            <Typography variant="body1" sx={{ color: "var(--success)", fontWeight: 600 }}>
              PAPER
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Live trading requires manual enable
            </Typography>
          </CardContent>
        </Card>
      </Stack>
    </Box>
  );
};

export default Overview;
