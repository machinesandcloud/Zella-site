import { useState } from "react";
import {
  Button,
  Card,
  CardContent,
  Chip,
  Grid,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography
} from "@mui/material";
import { triggerKillSwitch } from "../../services/api";

type Mode = "ASSISTED" | "SEMI_AUTO" | "FULL_AUTO" | "GOD_MODE";

const AutopilotControl = () => {
  const [mode, setMode] = useState<Mode>("FULL_AUTO");
  const [status, setStatus] = useState("ACTIVE");
  const [metrics] = useState({ symbols: 1247, strategies: 3, trades: 12, pnl: 842 });

  const handleKill = async () => {
    const confirmed = window.confirm("This will stop all trading immediately. Continue?");
    if (!confirmed) return;
    await triggerKillSwitch();
  };

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
          <Stack spacing={1}>
            <Typography variant="h6">AI Autopilot Control Center</Typography>
            <Typography variant="body2" color="text.secondary">
              AI status & supervisory controls
            </Typography>
          </Stack>
          <Chip label={status} color={status === "ACTIVE" ? "success" : "default"} />
        </Stack>

        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={6} md={3}>
            <Typography variant="overline">Symbols</Typography>
            <Typography variant="h6">{metrics.symbols}</Typography>
          </Grid>
          <Grid item xs={6} md={3}>
            <Typography variant="overline">Strategies</Typography>
            <Typography variant="h6">{metrics.strategies}</Typography>
          </Grid>
          <Grid item xs={6} md={3}>
            <Typography variant="overline">Trades Today</Typography>
            <Typography variant="h6">{metrics.trades}</Typography>
          </Grid>
          <Grid item xs={6} md={3}>
            <Typography variant="overline">AI PnL</Typography>
            <Typography variant="h6">+${metrics.pnl}</Typography>
          </Grid>
        </Grid>

        <Stack spacing={2} sx={{ mb: 3 }}>
          <Typography variant="subtitle2">Autopilot Mode</Typography>
          <ToggleButtonGroup
            value={mode}
            exclusive
            onChange={(_, value) => value && setMode(value)}
          >
            <ToggleButton value="ASSISTED">Assisted</ToggleButton>
            <ToggleButton value="SEMI_AUTO">Semi-Auto</ToggleButton>
            <ToggleButton value="FULL_AUTO">Full Auto</ToggleButton>
            <ToggleButton value="GOD_MODE">God Mode</ToggleButton>
          </ToggleButtonGroup>
        </Stack>

        <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
          <Button
            variant="contained"
            onClick={() => setStatus(status === "ACTIVE" ? "PAUSED" : "ACTIVE")}
          >
            {status === "ACTIVE" ? "Pause AI" : "Resume AI"}
          </Button>
          <Button variant="outlined">Configure</Button>
          <Button variant="contained" color="error" onClick={handleKill}>
            Emergency Stop
          </Button>
        </Stack>
      </CardContent>
    </Card>
  );
};

export default AutopilotControl;
