import { Card, CardContent, Grid, Stack, Typography } from "@mui/material";

const DailyBriefing = () => {
  const items = [
    { label: "Risk posture", value: "Balanced" },
    { label: "Market regime", value: "Trend-follow" },
    { label: "Key watch", value: "NVDA, AAPL" },
    { label: "PnL target", value: "+$1,000" }
  ];

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Stack spacing={1} sx={{ mb: 2 }}>
          <Typography variant="h6">Daily Briefing</Typography>
          <Typography variant="body2" color="text.secondary">
            AI highlights for today’s session
          </Typography>
        </Stack>
        <Grid container spacing={2}>
          {items.map((item) => (
            <Grid item xs={12} md={3} key={item.label}>
              <Typography variant="overline">{item.label}</Typography>
              <Typography variant="h6">{item.value}</Typography>
            </Grid>
          ))}
        </Grid>
      </CardContent>
    </Card>
  );
};

export default DailyBriefing;
