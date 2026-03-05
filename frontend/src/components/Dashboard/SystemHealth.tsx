import { useEffect, useState } from "react";
import { Card, CardContent, Chip, Grid, Typography } from "@mui/material";
import { fetchAlpacaStatus } from "../../services/api";

type Status = {
  connected: boolean;
  mode: string;
};

const SystemHealth = () => {
  const [status, setStatus] = useState<Status | null>(null);

  useEffect(() => {
    const cached = localStorage.getItem("zella_alpaca_status");
    if (cached) {
      try {
        setStatus(JSON.parse(cached));
      } catch {
        // ignore cache parse errors
      }
    }

    const load = async () => {
      try {
        const data = await fetchAlpacaStatus();
        setStatus(data);
        localStorage.setItem("zella_alpaca_status", JSON.stringify(data));
      } catch {
        setStatus(null);
      }
    };

    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          System Health
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <Typography variant="overline">Alpaca Status</Typography>
            <Chip
              label={status?.connected ? "Connected" : "Disconnected"}
              color={status?.connected ? "success" : "default"}
              size="small"
            />
          </Grid>
          <Grid item xs={12} md={4}>
            <Typography variant="overline">Trading Mode</Typography>
            <Typography variant="h6">{status?.mode || "PAPER"}</Typography>
          </Grid>
          <Grid item xs={12} md={4}>
            <Typography variant="overline">Data Feed</Typography>
            <Chip label="Streaming" color="success" size="small" />
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
};

export default SystemHealth;
