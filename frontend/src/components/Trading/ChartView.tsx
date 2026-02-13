import { useEffect, useMemo, useRef, useState } from "react";
import {
  Card,
  CardContent,
  FormControlLabel,
  MenuItem,
  Select,
  SelectChangeEvent,
  Stack,
  Switch,
  Typography
} from "@mui/material";
import { createChart, ColorType, UTCTimestamp } from "lightweight-charts";
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
  const [timeframe, setTimeframe] = useState("1m");
  const [showEMA, setShowEMA] = useState(true);
  const [showSMA, setShowSMA] = useState(false);
  const [showVWAP, setShowVWAP] = useState(false);
  const [showBB, setShowBB] = useState(false);

  const tfSeconds = useMemo(() => {
    const map: Record<string, number> = {
      "1m": 60,
      "5m": 300,
      "15m": 900,
      "1h": 3600,
      "4h": 14400,
      "1d": 86400
    };
    return map[timeframe] || 60;
  }, [timeframe]);

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

    const priceSeries = chart.addLineSeries({ color: "#1f7a8c" });
    const emaSeries = chart.addLineSeries({ color: "#f97316", lineWidth: 2 });
    const smaSeries = chart.addLineSeries({ color: "#22c55e", lineWidth: 2 });
    const vwapSeries = chart.addLineSeries({ color: "#6366f1", lineWidth: 2 });
    const bbUpperSeries = chart.addLineSeries({ color: "#ef4444", lineWidth: 1 });
    const bbLowerSeries = chart.addLineSeries({ color: "#ef4444", lineWidth: 1 });

    const dataPoints: { time: UTCTimestamp; value: number; volume: number }[] = [];
    const emaPeriod = 20;
    const smaPeriod = 20;
    const bbPeriod = 20;
    const bbStd = 2;
    let emaValue: number | null = null;
    let currentBucket: number | null = null;
    let lastTime: UTCTimestamp | null = null;

    const symbol = "AAPL";
    const ws = connectWebSocket(`/ws/market-data?symbol=${symbol}`, (msg) => {
      const data = msg as MarketDataMessage;
      if (data.channel !== "market-data" || data.symbol !== symbol) return;
      const ts = Math.floor(new Date(data.timestamp).getTime() / 1000);
      const bucket = Math.floor(ts / tfSeconds) * tfSeconds;
      const time = bucket as UTCTimestamp;

      if (currentBucket === null || bucket !== currentBucket) {
        currentBucket = bucket;
        dataPoints.push({ time, value: data.price, volume: data.volume });
        if (dataPoints.length > 200) dataPoints.shift();
        lastTime = time;
      } else if (lastTime !== null) {
        const last = dataPoints[dataPoints.length - 1];
        last.value = data.price;
        last.volume += data.volume;
      }

      const points = dataPoints.map((p) => ({ time: p.time, value: p.value }));
      priceSeries.setData(points);

      if (showEMA) {
        if (emaValue === null) {
          emaValue = data.price;
        } else {
          const emaMultiplier = 2 / (emaPeriod + 1);
          emaValue = data.price * emaMultiplier + emaValue * (1 - emaMultiplier);
        }
        emaSeries.update({ time, value: Number(emaValue.toFixed(2)) });
      }

      if (showSMA && dataPoints.length >= smaPeriod) {
        const slice = dataPoints.slice(-smaPeriod);
        const sma = slice.reduce((acc, p) => acc + p.value, 0) / smaPeriod;
        smaSeries.update({ time, value: Number(sma.toFixed(2)) });
      }

      if (showVWAP) {
        const total = dataPoints.reduce((acc, p) => acc + p.value * p.volume, 0);
        const vol = dataPoints.reduce((acc, p) => acc + p.volume, 0);
        if (vol > 0) {
          const vwap = total / vol;
          vwapSeries.update({ time, value: Number(vwap.toFixed(2)) });
        }
      }

      if (showBB && dataPoints.length >= bbPeriod) {
        const slice = dataPoints.slice(-bbPeriod);
        const mean = slice.reduce((acc, p) => acc + p.value, 0) / bbPeriod;
        const variance =
          slice.reduce((acc, p) => acc + (p.value - mean) ** 2, 0) / bbPeriod;
        const std = Math.sqrt(variance);
        const upper = mean + bbStd * std;
        const lower = mean - bbStd * std;
        bbUpperSeries.update({ time, value: Number(upper.toFixed(2)) });
        bbLowerSeries.update({ time, value: Number(lower.toFixed(2)) });
      }
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
  }, [tfSeconds, showEMA, showSMA, showVWAP, showBB]);

  const handleTimeframe = (event: SelectChangeEvent) => {
    setTimeframe(event.target.value);
  };

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2, flexWrap: "wrap" }}>
          <Typography variant="h6">Price Chart</Typography>
          <Select size="small" value={timeframe} onChange={handleTimeframe}>
            <MenuItem value="1m">1m</MenuItem>
            <MenuItem value="5m">5m</MenuItem>
            <MenuItem value="15m">15m</MenuItem>
            <MenuItem value="1h">1H</MenuItem>
            <MenuItem value="4h">4H</MenuItem>
            <MenuItem value="1d">1D</MenuItem>
          </Select>
          <FormControlLabel
            control={<Switch checked={showEMA} onChange={() => setShowEMA(!showEMA)} />}
            label="EMA"
          />
          <FormControlLabel
            control={<Switch checked={showSMA} onChange={() => setShowSMA(!showSMA)} />}
            label="SMA"
          />
          <FormControlLabel
            control={<Switch checked={showVWAP} onChange={() => setShowVWAP(!showVWAP)} />}
            label="VWAP"
          />
          <FormControlLabel
            control={<Switch checked={showBB} onChange={() => setShowBB(!showBB)} />}
            label="BB"
          />
        </Stack>
        <div ref={chartRef} />
      </CardContent>
    </Card>
  );
};

export default ChartView;
