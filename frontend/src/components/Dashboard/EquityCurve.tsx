import { useEffect, useRef, useState } from "react";
import { Card, CardContent, Typography } from "@mui/material";
import { ColorType, UTCTimestamp, createChart } from "lightweight-charts";
import { fetchAccountSnapshots } from "../../services/api";

type Snapshot = {
  account_value: number;
  snapshot_time: string;
};

const EquityCurve = () => {
  const chartRef = useRef<HTMLDivElement | null>(null);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);

  useEffect(() => {
    fetchAccountSnapshots()
      .then((data) => setSnapshots(data || []))
      .catch(() => setSnapshots([]));
  }, []);

  useEffect(() => {
    if (!chartRef.current) return;

    const chart = createChart(chartRef.current, {
      width: chartRef.current.clientWidth,
      height: 220,
      layout: {
        background: { type: ColorType.Solid, color: "#ffffff" },
        textColor: "#1f2937"
      },
      grid: {
        vertLines: { color: "#e2e8f0" },
        horzLines: { color: "#e2e8f0" }
      }
    });

    const series = chart.addLineSeries({ color: "#2563eb", lineWidth: 2 });
    const data = snapshots
      .slice()
      .reverse()
      .map((snap) => ({
        time: Math.floor(new Date(snap.snapshot_time).getTime() / 1000) as UTCTimestamp,
        value: Number(snap.account_value || 0)
      }));
    series.setData(data);

    const handleResize = () => {
      chart.applyOptions({ width: chartRef.current?.clientWidth || 0 });
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [snapshots]);

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Equity Curve
        </Typography>
        <div ref={chartRef} />
      </CardContent>
    </Card>
  );
};

export default EquityCurve;
