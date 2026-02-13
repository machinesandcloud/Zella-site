import { useEffect, useState } from "react";
import { Card, CardContent, Grid, Typography } from "@mui/material";
import { fetchDashboardMetrics } from "../../services/api";

type Metrics = {
  total_trades: number;
  win_rate: number;
  largest_win: number;
  largest_loss: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number;
  total_pnl: number;
};

const PerformanceMetrics = () => {
  const [metrics, setMetrics] = useState<Metrics | null>(null);

  useEffect(() => {
    fetchDashboardMetrics()
      .then((data) => setMetrics(data))
      .catch(() => setMetrics(null));
  }, []);

  const rows = metrics
    ? [
        { label: "Total Trades", value: metrics.total_trades },
        { label: "Win Rate", value: `${metrics.win_rate}%` },
        { label: "Profit Factor", value: metrics.profit_factor },
        { label: "Total PnL", value: `$${metrics.total_pnl}` },
        { label: "Largest Win", value: `$${metrics.largest_win}` },
        { label: "Largest Loss", value: `$${metrics.largest_loss}` },
        { label: "Avg Win", value: `$${metrics.avg_win}` },
        { label: "Avg Loss", value: `$${metrics.avg_loss}` }
      ]
    : [
        { label: "Total Trades", value: "--" },
        { label: "Win Rate", value: "--" },
        { label: "Profit Factor", value: "--" },
        { label: "Total PnL", value: "--" },
        { label: "Largest Win", value: "--" },
        { label: "Largest Loss", value: "--" },
        { label: "Avg Win", value: "--" },
        { label: "Avg Loss", value: "--" }
      ];

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Performance Metrics
        </Typography>
        <Grid container spacing={2}>
          {rows.map((metric) => (
            <Grid item xs={6} md={3} key={metric.label}>
              <Typography variant="overline" color="text.secondary">
                {metric.label}
              </Typography>
              <Typography variant="h6">{metric.value}</Typography>
            </Grid>
          ))}
        </Grid>
      </CardContent>
    </Card>
  );
};

export default PerformanceMetrics;
