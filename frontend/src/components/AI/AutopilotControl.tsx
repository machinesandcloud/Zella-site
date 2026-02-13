import { useMemo, useState } from "react";
import {
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  Grid,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography
} from "@mui/material";
import { triggerKillSwitch } from "../../services/api";

type Mode = "ASSISTED" | "SEMI_AUTO" | "FULL_AUTO" | "GOD_MODE";

type Decision = {
  id: string;
  time: string;
  type: "TRADE" | "SIGNAL" | "RISK";
  action: string;
  reasoning: string;
  status: "EXECUTED" | "SKIPPED" | "ADJUSTED";
};

const AutopilotControl = () => {
  const [mode, setMode] = useState<Mode>("FULL_AUTO");
  const [status, setStatus] = useState("ACTIVE");
  const [riskPosture, setRiskPosture] = useState<"DEFENSIVE" | "BALANCED" | "AGGRESSIVE">(
    "BALANCED"
  );
  const [metrics] = useState({ symbols: 1247, strategies: 3, trades: 12, pnl: 842 });

  const decisions = useMemo<Decision[]>(
    () => [
      {
        id: "d1",
        time: "14:34",
        type: "TRADE",
        action: "Bought 50 AAPL @ 148.50",
        reasoning: "EMA crossover + volume surge; R:R 2.6",
        status: "EXECUTED"
      },
      {
        id: "d2",
        time: "14:28",
        type: "SIGNAL",
        action: "Skipped TSLA short",
        reasoning: "Against market trend; low confidence",
        status: "SKIPPED"
      },
      {
        id: "d3",
        time: "14:12",
        type: "RISK",
        action: "Tightened stops by 15%",
        reasoning: "Volatility spike + daily PnL near target",
        status: "ADJUSTED"
      }
    ],
    []
  );

  const handleKill = async () => {
    const confirmed = window.confirm("This will stop all trading immediately. Continue?");
    if (!confirmed) return;
    await triggerKillSwitch();
    window.dispatchEvent(
      new CustomEvent("app:toast", {
        detail: { message: "Kill switch triggered. Trading halted.", severity: "error" }
      })
    );
  };

  const notify = (message: string, severity: "success" | "info" | "warning" | "error" = "info") => {
    window.dispatchEvent(new CustomEvent("app:toast", { detail: { message, severity } }));
  };

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
          <Stack spacing={1}>
            <Typography variant="h6">AI Autopilot Control Center</Typography>
            <Typography variant="body2" color="text.secondary">
              AI status, risk posture, and decision transparency
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Autopilot executes in PAPER mode only. Review results before enabling any live trading.
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

        <Stack spacing={1} sx={{ mb: 3 }}>
          <Typography variant="subtitle2">Risk Posture</Typography>
          <ToggleButtonGroup
            value={riskPosture}
            exclusive
            onChange={(_, value) => value && setRiskPosture(value)}
          >
            <ToggleButton value="DEFENSIVE">Defensive</ToggleButton>
            <ToggleButton value="BALANCED">Balanced</ToggleButton>
            <ToggleButton value="AGGRESSIVE">Aggressive</ToggleButton>
          </ToggleButtonGroup>
        </Stack>

        <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ mb: 3 }}>
          <Button
            variant="contained"
            onClick={() => {
              const next = status === "ACTIVE" ? "PAUSED" : "ACTIVE";
              setStatus(next);
              notify(next === "ACTIVE" ? "Autopilot resumed." : "Autopilot paused.", "success");
            }}
          >
            {status === "ACTIVE" ? "Pause AI" : "Resume AI"}
          </Button>
          <Button
            variant="outlined"
            onClick={() => {
              window.dispatchEvent(new CustomEvent("app:navigate", { detail: { tab: 3 } }));
              notify("Opening AI configuration in Settings.", "info");
            }}
          >
            Configure
          </Button>
          <Button variant="contained" color="error" onClick={handleKill}>
            Emergency Stop
          </Button>
        </Stack>

        <Divider sx={{ mb: 2 }} />

        <Typography variant="subtitle2" sx={{ mb: 2 }}>
          Decision Log
        </Typography>
        <Stack spacing={2}>
          {decisions.map((decision) => (
            <Stack
              key={decision.id}
              sx={{
                p: 2,
                borderRadius: 3,
                border: "1px solid rgba(255,255,255,0.06)",
                background: "rgba(12, 16, 26, 0.7)"
              }}
            >
              <Stack direction="row" justifyContent="space-between" alignItems="center">
                <Typography variant="body2" color="text.secondary">
                  {decision.time} · {decision.type}
                </Typography>
                <Chip label={decision.status} size="small" />
              </Stack>
              <Typography variant="subtitle1" sx={{ mt: 1 }}>
                {decision.action}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {decision.reasoning}
              </Typography>
            </Stack>
          ))}
        </Stack>
      </CardContent>
    </Card>
  );
};

export default AutopilotControl;
