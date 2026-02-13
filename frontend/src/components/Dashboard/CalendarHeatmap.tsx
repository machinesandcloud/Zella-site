import { Card, CardContent, Grid, Typography } from "@mui/material";

const CalendarHeatmap = () => {
  const days = Array.from({ length: 14 }).map((_, idx) => ({
    date: new Date(Date.now() - (13 - idx) * 86400000),
    pnl: Math.round((Math.random() - 0.4) * 200)
  }));

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          PnL Calendar
        </Typography>
        <Grid container spacing={1}>
          {days.map((day) => (
            <Grid item xs={3} sm={2} md={1} key={day.date.toISOString()}>
              <div
                style={{
                  height: 48,
                  borderRadius: 6,
                  background:
                    day.pnl >= 0
                      ? `rgba(34, 197, 94, ${Math.min(0.8, day.pnl / 200)})`
                      : `rgba(239, 68, 68, ${Math.min(0.8, Math.abs(day.pnl) / 200)})`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 12,
                  color: "#0f172a"
                }}
              >
                {day.date.getDate()}
              </div>
            </Grid>
          ))}
        </Grid>
      </CardContent>
    </Card>
  );
};

export default CalendarHeatmap;
