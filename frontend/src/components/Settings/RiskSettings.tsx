import { useState } from "react";
import { Button, Card, CardContent, Grid, TextField, Typography } from "@mui/material";
import api from "../../services/api";

const RiskSettings = () => {
  const [values, setValues] = useState({
    max_position_size_percent: 10,
    max_daily_loss: 500,
    max_concurrent_positions: 5,
    risk_per_trade_percent: 2
  });

  const update = (key: string, value: number) => {
    setValues((prev) => ({ ...prev, [key]: value }));
  };

  const save = async () => {
    await api.put("/api/settings/risk", values);
  };

  const killSwitch = async () => {
    await api.post("/api/trading/kill-switch");
  };

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Risk Management
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Max Position Size (%)"
              type="number"
              value={values.max_position_size_percent}
              onChange={(e) => update("max_position_size_percent", Number(e.target.value))}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Max Daily Loss ($)"
              type="number"
              value={values.max_daily_loss}
              onChange={(e) => update("max_daily_loss", Number(e.target.value))}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Max Concurrent Positions"
              type="number"
              value={values.max_concurrent_positions}
              onChange={(e) => update("max_concurrent_positions", Number(e.target.value))}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Risk per Trade (%)"
              type="number"
              value={values.risk_per_trade_percent}
              onChange={(e) => update("risk_per_trade_percent", Number(e.target.value))}
            />
          </Grid>
          <Grid item xs={12} md={3}>
            <Button variant="contained" onClick={save}>
              Save
            </Button>
          </Grid>
          <Grid item xs={12} md={3}>
            <Button variant="outlined" color="error" onClick={killSwitch}>
              Kill Switch
            </Button>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
};

export default RiskSettings;
