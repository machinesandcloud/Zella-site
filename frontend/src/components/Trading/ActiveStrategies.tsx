import { Card, CardContent, Stack, Typography, Button } from "@mui/material";

const ActiveStrategies = () => {
  const strategies = [
    { name: "ema_cross", status: "running", performance: "+2.1%" },
    { name: "vwap_bounce", status: "stopped", performance: "-0.4%" }
  ];

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Active Strategies
        </Typography>
        <Stack spacing={2}>
          {strategies.map((strategy) => (
            <Stack key={strategy.name} direction="row" spacing={2} alignItems="center">
              <Typography sx={{ minWidth: 120 }}>{strategy.name}</Typography>
              <Typography color="text.secondary">{strategy.performance}</Typography>
              <Button size="small" variant="outlined">
                {strategy.status === "running" ? "Stop" : "Start"}
              </Button>
              <Button size="small">Configure</Button>
            </Stack>
          ))}
        </Stack>
      </CardContent>
    </Card>
  );
};

export default ActiveStrategies;
