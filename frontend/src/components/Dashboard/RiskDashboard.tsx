import { useEffect, useState } from "react";
import { Card, CardContent, Grid, Typography } from "@mui/material";
import { fetchRiskSummary } from "../../services/api";

type RiskSummary = {
  accountMetrics: Record<string, number | string | object>;
  killSwitch: Record<string, number | string | boolean | null>;
};

const RiskDashboard = () => {
  const [summary, setSummary] = useState<RiskSummary | null>(null);

  useEffect(() => {
    fetchRiskSummary()
      .then((data) => setSummary(data))
      .catch(() => setSummary(null));
  }, []);

  const metrics = summary?.accountMetrics || {};

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Risk Dashboard
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6} md={3}>
            <Typography variant="overline">Daily PnL</Typography>
            <Typography variant="h6">{metrics.dailyPnL ?? "--"}</Typography>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Typography variant="overline">Loss Limit</Typography>
            <Typography variant="h6">{metrics.dailyLossLimit ?? "--"}</Typography>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Typography variant="overline">Positions</Typography>
            <Typography variant="h6">
              {metrics.currentPositions ?? "--"} / {metrics.maxPositions ?? "--"}
            </Typography>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Typography variant="overline">Gross Exposure</Typography>
            <Typography variant="h6">{metrics.grossExposure ?? "--"}</Typography>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
};

export default RiskDashboard;
