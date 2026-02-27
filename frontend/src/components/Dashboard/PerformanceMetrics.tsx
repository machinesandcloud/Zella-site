import { useEffect, useState } from "react";
import { Box, Card, CardContent, Grid, Typography } from "@mui/material";
import { fetchDashboardMetrics, fetchTrades } from "../../services/api";

type Metrics = {
  total_trades: number;
  win_rate: number;
  largest_win: number;
  largest_loss: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number;
  total_pnl: number;
  wins: number;
  losses: number;
};

const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2
  }).format(value);
};

const PerformanceMetrics = () => {
  const [metrics, setMetrics] = useState<Metrics>({
    total_trades: 0,
    win_rate: 0,
    largest_win: 0,
    largest_loss: 0,
    avg_win: 0,
    avg_loss: 0,
    profit_factor: 0,
    total_pnl: 0,
    wins: 0,
    losses: 0
  });

  useEffect(() => {
    const loadMetrics = async () => {
      try {
        // Try dashboard metrics first
        const data = await fetchDashboardMetrics();
        if (data && typeof data.total_trades === "number") {
          setMetrics(data);
          return;
        }
      } catch {
        // Fallback: calculate from trades
      }

      // If dashboard metrics fail, try to calculate from trades
      try {
        const trades = await fetchTrades();
        if (trades && Array.isArray(trades) && trades.length > 0) {
          const wins = trades.filter((t: any) => (t.pnl || t.realized_pnl || 0) > 0);
          const losses = trades.filter((t: any) => (t.pnl || t.realized_pnl || 0) < 0);

          const winPnls = wins.map((t: any) => t.pnl || t.realized_pnl || 0);
          const lossPnls = losses.map((t: any) => Math.abs(t.pnl || t.realized_pnl || 0));

          const totalPnl = trades.reduce((sum: number, t: any) => sum + (t.pnl || t.realized_pnl || 0), 0);
          const avgWin = winPnls.length > 0 ? winPnls.reduce((a: number, b: number) => a + b, 0) / winPnls.length : 0;
          const avgLoss = lossPnls.length > 0 ? lossPnls.reduce((a: number, b: number) => a + b, 0) / lossPnls.length : 0;

          setMetrics({
            total_trades: trades.length,
            wins: wins.length,
            losses: losses.length,
            win_rate: trades.length > 0 ? (wins.length / trades.length) * 100 : 0,
            largest_win: winPnls.length > 0 ? Math.max(...winPnls) : 0,
            largest_loss: lossPnls.length > 0 ? Math.max(...lossPnls) : 0,
            avg_win: avgWin,
            avg_loss: avgLoss,
            profit_factor: avgLoss > 0 ? avgWin / avgLoss : 0,
            total_pnl: totalPnl
          });
        }
      } catch {
        // Keep default zeros
      }
    };

    loadMetrics();
    const interval = setInterval(loadMetrics, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  const MetricBox = ({ label, value, color }: { label: string; value: string | number; color?: string }) => (
    <Box sx={{
      p: 2,
      borderRadius: 2,
      border: "1px solid rgba(255,255,255,0.08)",
      background: "rgba(255,255,255,0.02)",
      minHeight: 80
    }}>
      <Typography variant="overline" color="text.secondary" sx={{ fontSize: "0.65rem" }}>
        {label}
      </Typography>
      <Typography variant="h6" sx={{ fontWeight: 600, color: color || "inherit", mt: 0.5 }}>
        {value}
      </Typography>
    </Box>
  );

  const noTrades = metrics.total_trades === 0;

  return (
    <Card elevation={0} sx={{ border: "1px solid rgba(255,255,255,0.1)", borderRadius: 3 }}>
      <CardContent sx={{ p: 3 }}>
        <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
          Performance Metrics
        </Typography>

        {noTrades ? (
          <Box sx={{
            p: 4,
            textAlign: "center",
            border: "1px dashed rgba(255,255,255,0.1)",
            borderRadius: 2
          }}>
            <Typography color="text.secondary">No trades recorded yet</Typography>
            <Typography variant="caption" color="text.secondary">
              Metrics will appear once the bot makes trades
            </Typography>
          </Box>
        ) : (
          <Grid container spacing={2}>
            <Grid item xs={6} sm={4} md={3}>
              <MetricBox label="Total Trades" value={metrics.total_trades} />
            </Grid>
            <Grid item xs={6} sm={4} md={3}>
              <MetricBox
                label="Win Rate"
                value={`${metrics.win_rate.toFixed(1)}%`}
                color={metrics.win_rate >= 50 ? "#4caf50" : "#f44336"}
              />
            </Grid>
            <Grid item xs={6} sm={4} md={3}>
              <MetricBox label="Wins / Losses" value={`${metrics.wins} / ${metrics.losses}`} />
            </Grid>
            <Grid item xs={6} sm={4} md={3}>
              <MetricBox
                label="Total P&L"
                value={formatCurrency(metrics.total_pnl)}
                color={metrics.total_pnl >= 0 ? "#4caf50" : "#f44336"}
              />
            </Grid>
            <Grid item xs={6} sm={4} md={3}>
              <MetricBox label="Avg Win" value={formatCurrency(metrics.avg_win)} color="#4caf50" />
            </Grid>
            <Grid item xs={6} sm={4} md={3}>
              <MetricBox label="Avg Loss" value={formatCurrency(metrics.avg_loss)} color="#f44336" />
            </Grid>
            <Grid item xs={6} sm={4} md={3}>
              <MetricBox label="Largest Win" value={formatCurrency(metrics.largest_win)} color="#4caf50" />
            </Grid>
            <Grid item xs={6} sm={4} md={3}>
              <MetricBox
                label="Profit Factor"
                value={metrics.profit_factor.toFixed(2)}
                color={metrics.profit_factor >= 1 ? "#4caf50" : "#f44336"}
              />
            </Grid>
          </Grid>
        )}
      </CardContent>
    </Card>
  );
};

export default PerformanceMetrics;
