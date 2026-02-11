import { useEffect, useRef } from "react";
import { Card, CardContent, Typography } from "@mui/material";
import { createChart, ColorType } from "lightweight-charts";
import { connectWebSocket } from "../../services/websocket";

type MarketDataMessage = {
  channel: string;
  symbol: string;
  price: number;
  volume: number;
  timestamp: string;
};

const ChartView = () => {
  const chartRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    const chart = createChart(chartRef.current, {
      width: chartRef.current.clientWidth,
      height: 280,
      layout: {
        background: { type: ColorType.Solid, color: "#ffffff" },
        textColor: "#1f2937"
      },
      grid: {
        vertLines: { color: "#e2e8f0" },
        horzLines: { color: "#e2e8f0" }
      }
    });

    const line = chart.addLineSeries({ color: "#1f7a8c" });
    const ema = chart.addLineSeries({ color: "#f97316", lineWidth: 2 });
    const emaPeriod = 20;
    const emaMultiplier = 2 / (emaPeriod + 1);
    let emaValue: number | null = null;
    const symbol = "AAPL";
    const ws = connectWebSocket(`/ws/market-data?symbol=${symbol}`, (msg) => {
      const data = msg as MarketDataMessage;
      if (data.channel !== "market-data" || data.symbol !== symbol) return;
      const time = Math.floor(new Date(data.timestamp).getTime() / 1000);
      line.update({ time, value: data.price });
      if (emaValue === null) {
        emaValue = data.price;
      } else {
        emaValue = data.price * emaMultiplier + emaValue * (1 - emaMultiplier);
      }
      ema.update({ time, value: Number(emaValue.toFixed(2)) });
    });

    const handleResize = () => {
      chart.applyOptions({ width: chartRef.current?.clientWidth || 0 });
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      ws.close();
      chart.remove();
    };
  }, []);

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Price Chart
        </Typography>
        <div ref={chartRef} />
      </CardContent>
    </Card>
  );
};

export default ChartView;
