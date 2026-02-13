import { useEffect, useMemo, useState } from "react";
import { Card, CardContent, Grid, Typography } from "@mui/material";
import { fetchTrades } from "../../services/api";

type Trade = {
  pnl?: number | null;
  exit_time?: string | null;
};

const CalendarHeatmap = () => {
  const [trades, setTrades] = useState<Trade[]>([]);

  useEffect(() => {
    fetchTrades()
      .then((data) => setTrades(data || []))
      .catch(() => setTrades([]));
  }, []);

  const days = useMemo(() => {
    const byDate = new Map<string, number>();
    trades.forEach((trade) => {
      if (!trade.exit_time) return;
      const key = new Date(trade.exit_time).toDateString();
      byDate.set(key, (byDate.get(key) || 0) + Number(trade.pnl || 0));
    });
    return Array.from({ length: 14 }).map((_, idx) => {
      const date = new Date(Date.now() - (13 - idx) * 86400000);
      const key = date.toDateString();
      return { date, pnl: byDate.get(key) || 0 };
    });
  }, [trades]);

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
                      ? `rgba(34, 197, 94, ${Math.min(0.8, Math.abs(day.pnl) / 200)})`
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
