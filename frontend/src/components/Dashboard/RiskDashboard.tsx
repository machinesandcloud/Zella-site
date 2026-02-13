import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  CardContent,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  LinearProgress,
  Stack,
  Typography
} from "@mui/material";
import { fetchRiskSummary, triggerKillSwitch } from "../../services/api";

type RiskSummary = {
  accountMetrics: {
    totalAccountValue?: number;
    cashBalance?: number;
    buyingPower?: number;
    dailyPnL?: number;
    dailyLossLimit?: number;
    distanceToLimit?: number;
    limitPercent?: number;
    currentPositions?: number;
    maxPositions?: number;
    tradesToday?: number;
    maxTradesPerDay?: number;
    consecutiveLosses?: number;
    maxConsecutiveLosses?: number;
    grossExposure?: number;
    netExposure?: number;
    largestPosition?: { symbol?: string | null; percentOfAccount?: number };
  };
  killSwitch: {
    enabled?: boolean;
    reason?: string | null;
    triggeredAt?: string | null;
  };
};

const RiskDashboard = () => {
  const [summary, setSummary] = useState<RiskSummary | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    fetchRiskSummary()
      .then((data) => setSummary(data))
      .catch(() => setSummary(null));
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 8000);
    return () => clearInterval(interval);
  }, []);

  const metrics = summary?.accountMetrics || {};

  const limitPercent = useMemo(() => Math.min(100, Number(metrics.limitPercent || 0)), [metrics]);
  const riskColor = limitPercent >= 80 ? "error" : limitPercent >= 50 ? "warning" : "success";

  const handleKillSwitch = async () => {
    setError(null);
    try {
      await triggerKillSwitch();
      setConfirmOpen(false);
      load();
    } catch (err) {
      setError("Failed to trigger kill switch.");
    }
  };

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
          <Typography variant="h6">Risk Dashboard</Typography>
          <Button variant="outlined" size="small" onClick={load}>
            Refresh
          </Button>
        </Stack>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <Typography variant="overline">Daily Loss Limit Usage</Typography>
            <Typography variant="h6">
              {metrics.dailyPnL ?? 0} / -{metrics.dailyLossLimit ?? 0}
            </Typography>
            <LinearProgress
              variant="determinate"
              value={limitPercent}
              color={riskColor}
              sx={{ height: 8, borderRadius: 4, mt: 1 }}
            />
            <Typography variant="caption" color="text.secondary">
              {metrics.distanceToLimit ?? 0} until limit
            </Typography>
          </Grid>

          <Grid item xs={12} md={6}>
            <Typography variant="overline">Position Limits</Typography>
            <Typography variant="h6">
              {metrics.currentPositions ?? 0} / {metrics.maxPositions ?? 0} positions
            </Typography>
            <LinearProgress
              variant="determinate"
              value={
                metrics.maxPositions
                  ? Math.min(100, (Number(metrics.currentPositions || 0) / metrics.maxPositions) * 100)
                  : 0
              }
              sx={{ height: 8, borderRadius: 4, mt: 1 }}
            />
            <Typography variant="caption" color="text.secondary">
              Gross exposure: {metrics.grossExposure ?? 0}
            </Typography>
          </Grid>

          <Grid item xs={12} md={6}>
            <Typography variant="overline">Guardrails</Typography>
            <Typography variant="h6">
              Trades {metrics.tradesToday ?? 0}/{metrics.maxTradesPerDay ?? 0} · Losses {metrics.consecutiveLosses ?? 0}/
              {metrics.maxConsecutiveLosses ?? 0}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Auto-trade halts if limits are exceeded.
            </Typography>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Typography variant="overline">Account Value</Typography>
            <Typography variant="h6">{metrics.totalAccountValue ?? "--"}</Typography>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Typography variant="overline">Buying Power</Typography>
            <Typography variant="h6">{metrics.buyingPower ?? "--"}</Typography>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Typography variant="overline">Net Exposure</Typography>
            <Typography variant="h6">{metrics.netExposure ?? "--"}</Typography>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Typography variant="overline">Largest Position</Typography>
            <Typography variant="h6">
              {metrics.largestPosition?.symbol || "--"} ({metrics.largestPosition?.percentOfAccount?.toFixed(1) || 0}%)
            </Typography>
          </Grid>
        </Grid>

        <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ mt: 3 }}>
          <Button variant="contained" color="error" onClick={() => setConfirmOpen(true)}>
            KILL SWITCH - STOP ALL TRADING
          </Button>
          {summary?.killSwitch?.enabled && (
            <Alert severity="warning">
              Kill switch active{summary.killSwitch.reason ? `: ${summary.killSwitch.reason}` : ""}
            </Alert>
          )}
        </Stack>

        <Dialog open={confirmOpen} onClose={() => setConfirmOpen(false)}>
          <DialogTitle>Confirm Kill Switch</DialogTitle>
          <DialogContent>
            <Typography>
              This will close all positions, cancel open orders, and disable trading. Continue?
            </Typography>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setConfirmOpen(false)}>Cancel</Button>
            <Button variant="contained" color="error" onClick={handleKillSwitch}>
              Activate
            </Button>
          </DialogActions>
        </Dialog>
      </CardContent>
    </Card>
  );
};

export default RiskDashboard;
