import { Card, CardContent, Grid, Typography } from "@mui/material";

const PerformanceMetrics = () => {
  const metrics = [
    { label: "Total Trades", value: 24 },
    { label: "Win Rate", value: "54%" },
    { label: "Largest Win", value: "$420" },
    { label: "Largest Loss", value: "$-180" },
    { label: "Avg Win/Loss", value: "1.6" }
  ];

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Today&apos;s Performance
        </Typography>
        <Grid container spacing={2}>
          {metrics.map((metric) => (
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
