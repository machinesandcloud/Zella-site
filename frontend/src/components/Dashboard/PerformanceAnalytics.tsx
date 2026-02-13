import { useEffect, useMemo, useRef, useState } from "react";
import { Card, CardContent, Grid, Stack, Typography } from "@mui/material";
import { ColorType, UTCTimestamp, createChart } from "lightweight-charts";
import { fetchAccountSnapshots, fetchTrades } from "../../services/api";

type Snapshot = {
  account_value: number;
  snapshot_time: string;
};

type Trade = {
  pnl?: number | null;
};

const PerformanceAnalytics = () => {
  const equityRef = useRef<HTMLDivElement | null>(null);
  const drawdownRef = useRef<HTMLDivElement | null>(null);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);

  useEffect(() => {
    fetchAccountSnapshots()
      .then((data) => setSnapshots(data || []))
      .catch(() => setSnapshots([]));
    fetchTrades()
      .then((data) => setTrades(data || []))
      .catch(() => setTrades([]));
  }, []);

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
        </Grid>
      </CardContent>
    </Card>
  );
};

export default PerformanceAnalytics;
