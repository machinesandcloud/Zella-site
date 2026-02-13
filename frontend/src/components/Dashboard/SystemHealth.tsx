import { useEffect, useState } from "react";
import { Card, CardContent, Chip, Grid, Typography } from "@mui/material";
import { fetchIbkrStatus } from "../../services/api";

type Status = {
  connected: boolean;
  mode: string;
};

const SystemHealth = () => {
  const [status, setStatus] = useState<Status | null>(null);

  useEffect(() => {
    fetchIbkrStatus()
      .then((data) => setStatus(data))
      .catch(() => setStatus(null));
  }, []);

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          System Health
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <Typography variant="overline">IBKR Status</Typography>
            <Chip
              label={status?.connected ? "Connected" : "Disconnected"}
              color={status?.connected ? "success" : "default"}
              size="small"
            />
          </Grid>
          <Grid item xs={12} md={4}>
            <Typography variant="overline">Trading Mode</Typography>
            <Typography variant="h6">{status?.mode || "--"}</Typography>
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
