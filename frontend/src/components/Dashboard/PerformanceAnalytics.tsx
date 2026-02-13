import { useEffect, useMemo, useRef, useState } from "react";
import { Card, CardContent, Grid, Stack, Typography } from "@mui/material";
import { ColorType, UTCTimestamp, createChart } from "lightweight-charts";
import { fetchAccountSnapshots, fetchSetupStats, fetchTrades } from "../../services/api";

type Snapshot = {
  account_value: number;
  snapshot_time: string;
};

type Trade = {
  pnl?: number | null;
  entry_time?: string | null;
  setup_tag?: string | null;
};

type SetupStat = {
  setup: string;
  trades: number;
  wins: number;
  losses: number;
  win_rate: number;
  avg_pnl: number;
  total_pnl: number;
};

const PerformanceAnalytics = () => {
  const equityRef = useRef<HTMLDivElement | null>(null);
  const drawdownRef = useRef<HTMLDivElement | null>(null);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [setupStats, setSetupStats] = useState<SetupStat[]>([]);

  useEffect(() => {
    fetchAccountSnapshots()
      .then((data) => setSnapshots(data || []))
      .catch(() => setSnapshots([]));
    fetchTrades()
      .then((data) => setTrades(data || []))
      .catch(() => setTrades([]));
    fetchSetupStats()
      .then((data) => setSetupStats(data?.setups || []))
      .catch(() => setSetupStats([]));
  }, []);

  const dayOfWeekStats = useMemo(() => {
    const map = new Map<string, { count: number; pnl: number }>();
    trades.forEach((trade) => {
      if (!trade.entry_time) return;
      const date = new Date(trade.entry_time);
      const label = date.toLocaleDateString(undefined, { weekday: "short" });
      const entry = map.get(label) || { count: 0, pnl: 0 };
      entry.count += 1;
      entry.pnl += Number(trade.pnl || 0);
      map.set(label, entry);
    });
    return Array.from(map.entries()).map(([label, value]) => ({
      label,
      avg: value.count ? value.pnl / value.count : 0
    }));
  }, [trades]);

  const hourStats = useMemo(() => {
    const map = new Map<number, { count: number; pnl: number }>();
    trades.forEach((trade) => {
      if (!trade.entry_time) return;
      const date = new Date(trade.entry_time);
      const hour = date.getHours();
      const entry = map.get(hour) || { count: 0, pnl: 0 };
      entry.count += 1;
      entry.pnl += Number(trade.pnl || 0);
      map.set(hour, entry);
    });
    return Array.from(map.entries())
      .sort((a, b) => a[0] - b[0])
      .map(([hour, value]) => ({
        label: `${hour}:00`,
        avg: value.count ? value.pnl / value.count : 0
      }));
  }, [trades]);

  const equityData = useMemo(() => {
    return snapshots
      .slice()
      .reverse()
      .map((snap) => ({
        time: Math.floor(new Date(snap.snapshot_time).getTime() / 1000) as UTCTimestamp,
        value: Number(snap.account_value || 0)
      }));
  }, [snapshots]);

  const drawdownData = useMemo(() => {
    let peak = 0;
    return equityData.map((point) => {
      peak = Math.max(peak, point.value);
      const dd = peak ? ((point.value - peak) / peak) * 100 : 0;
      return { time: point.time, value: Number(dd.toFixed(2)) };
    });
  }, [equityData]);

  useEffect(() => {
    if (!equityRef.current) return;
    const chart = createChart(equityRef.current, {
      width: equityRef.current.clientWidth,
      height: 200,
      layout: {
        background: { type: ColorType.Solid, color: "#ffffff" },
        textColor: "#1f2937"
      },
      grid: { vertLines: { color: "#e2e8f0" }, horzLines: { color: "#e2e8f0" } }
    });
    const series = chart.addLineSeries({ color: "#16a34a", lineWidth: 2 });
    series.setData(equityData);

    const handleResize = () => {
      chart.applyOptions({ width: equityRef.current?.clientWidth || 0 });
    };
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [equityData]);

  useEffect(() => {
    if (!drawdownRef.current) return;
    const chart = createChart(drawdownRef.current, {
      width: drawdownRef.current.clientWidth,
      height: 200,
      layout: {
        background: { type: ColorType.Solid, color: "#ffffff" },
        textColor: "#1f2937"
      },
      grid: { vertLines: { color: "#e2e8f0" }, horzLines: { color: "#e2e8f0" } }
    });
    const series = chart.addLineSeries({ color: "#ef4444", lineWidth: 2 });
    series.setData(drawdownData);

    const handleResize = () => {
      chart.applyOptions({ width: drawdownRef.current?.clientWidth || 0 });
    };
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [drawdownData]);

  const histogram = useMemo(() => {
    const pnls = trades.map((trade) => Number(trade.pnl || 0));
    if (pnls.length === 0) return [] as Array<{ label: string; count: number }>;
    const min = Math.min(...pnls);
    const max = Math.max(...pnls);
    const buckets = 6;
    const step = (max - min) / buckets || 1;
    const result = Array.from({ length: buckets }, (_, idx) => ({
      label: `${(min + idx * step).toFixed(0)}-${(min + (idx + 1) * step).toFixed(0)}`,
      count: 0
    }));
    pnls.forEach((pnl) => {
      const index = Math.min(buckets - 1, Math.floor((pnl - min) / step));
      result[index].count += 1;
    });
    return result;
  }, [trades]);

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Performance Analytics
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <Typography variant="overline">Equity Curve</Typography>
            <div ref={equityRef} />
          </Grid>
          <Grid item xs={12} md={6}>
            <Typography variant="overline">Drawdown</Typography>
            <div ref={drawdownRef} />
          </Grid>
          <Grid item xs={12}>
            <Typography variant="overline">Win/Loss Distribution</Typography>
            <Stack direction="row" spacing={1} alignItems="flex-end" sx={{ mt: 1 }}>
              {histogram.map((bucket) => (
                <Stack key={bucket.label} alignItems="center" spacing={1}>
                  <div
                    style={{
                      width: 24,
                      height: bucket.count * 10 + 10,
                      background: "#94a3b8",
                      borderRadius: 4
                    }}
                  />
                  <Typography variant="caption">{bucket.label}</Typography>
                </Stack>
              ))}
            </Stack>
          </Grid>
          <Grid item xs={12} md={6}>
            <Typography variant="overline">Avg PnL by Day</Typography>
            <Stack direction="row" spacing={1} alignItems="flex-end" sx={{ mt: 1 }}>
              {dayOfWeekStats.map((bucket) => (
                <Stack key={bucket.label} alignItems="center" spacing={1}>
                  <div
                    style={{
                      width: 26,
                      height: Math.max(10, Math.min(120, Math.abs(bucket.avg) * 2 + 10)),
                      background: bucket.avg >= 0 ? "#22c55e" : "#ef4444",
                      borderRadius: 4
                    }}
                  />
                  <Typography variant="caption">{bucket.label}</Typography>
                </Stack>
              ))}
            </Stack>
          </Grid>
          <Grid item xs={12} md={6}>
            <Typography variant="overline">Avg PnL by Hour</Typography>
            <Stack direction="row" spacing={1} alignItems="flex-end" sx={{ mt: 1 }}>
              {hourStats.map((bucket) => (
                <Stack key={bucket.label} alignItems="center" spacing={1}>
                  <div
                    style={{
                      width: 18,
                      height: Math.max(10, Math.min(120, Math.abs(bucket.avg) * 2 + 10)),
                      background: bucket.avg >= 0 ? "#22c55e" : "#ef4444",
                      borderRadius: 4
                    }}
                  />
                  <Typography variant="caption">{bucket.label}</Typography>
                </Stack>
              ))}
            </Stack>
          </Grid>
          <Grid item xs={12}>
            <Typography variant="overline">Setup Performance (Playbook)</Typography>
            <Stack spacing={1} sx={{ mt: 1 }}>
              {setupStats.length === 0 && (
                <Typography variant="body2" color="text.secondary">
                  No setup stats yet. Tag trades in the journal to see results.
                </Typography>
              )}
              {setupStats.map((setup) => (
                <Stack
                  key={setup.setup}
                  direction="row"
                  spacing={2}
                  alignItems="center"
                  justifyContent="space-between"
                  sx={{
                    p: 1.5,
                    borderRadius: 2,
                    border: "1px solid rgba(255,255,255,0.08)",
                    background: "rgba(10, 14, 22, 0.6)"
                  }}
                >
                  <Typography variant="subtitle2">{setup.setup}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    Trades: {setup.trades} · Win rate: {setup.win_rate}% · Avg PnL: {setup.avg_pnl}
                  </Typography>
                  <Typography variant="subtitle2">
                    Total PnL: {setup.total_pnl}
                  </Typography>
                </Stack>
              ))}
            </Stack>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
};

export default PerformanceAnalytics;
