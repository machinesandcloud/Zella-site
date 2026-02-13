import { useEffect, useMemo, useRef, useState } from "react";
import {
  Card,
  CardContent,
  FormControl,
  FormControlLabel,
  MenuItem,
  Select,
  SelectChangeEvent,
  Stack,
  Switch,
  Typography
} from "@mui/material";
import { ColorType, UTCTimestamp, createChart } from "lightweight-charts";
import { connectWebSocket } from "../../services/websocket";

type MarketDataMessage = {
  channel: string;
  symbol: string;
  price: number;
  volume: number;
  timestamp: string;
};

type CandlePoint = {
  time: UTCTimestamp;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

const ChartView = () => {
  const chartRef = useRef<HTMLDivElement | null>(null);
  const chartApiRef = useRef<ReturnType<typeof createChart> | null>(null);
  const candleSeriesRef = useRef<ReturnType<ReturnType<typeof createChart>["addCandlestickSeries"]> | null>(null);
  const volumeSeriesRef = useRef<ReturnType<ReturnType<typeof createChart>["addHistogramSeries"]> | null>(null);
  const emaSeriesRef = useRef<ReturnType<ReturnType<typeof createChart>["addLineSeries"]> | null>(null);
  const smaSeriesRef = useRef<ReturnType<ReturnType<typeof createChart>["addLineSeries"]> | null>(null);
  const vwapSeriesRef = useRef<ReturnType<ReturnType<typeof createChart>["addLineSeries"]> | null>(null);
  const bbUpperSeriesRef = useRef<ReturnType<ReturnType<typeof createChart>["addLineSeries"]> | null>(null);
  const bbLowerSeriesRef = useRef<ReturnType<ReturnType<typeof createChart>["addLineSeries"]> | null>(null);

  const dataPointsRef = useRef<CandlePoint[]>([]);
  const currentBucketRef = useRef<number | null>(null);
  const emaValueRef = useRef<number | null>(null);

  const [symbol, setSymbol] = useState("AAPL");
  const [timeframe, setTimeframe] = useState("1m");
  const [showEMA, setShowEMA] = useState(true);
  const [showSMA, setShowSMA] = useState(false);
  const [showVWAP, setShowVWAP] = useState(false);
  const [showBB, setShowBB] = useState(false);
  const showEMARef = useRef(showEMA);
  const showSMARef = useRef(showSMA);
  const showVWAPRef = useRef(showVWAP);
  const showBBRef = useRef(showBB);

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

    if (chartApiRef.current) {
      chartApiRef.current.remove();
      chartApiRef.current = null;
    }

    const chart = createChart(chartRef.current, {
      width: chartRef.current.clientWidth,
      height: 340,
      layout: {
        background: { type: ColorType.Solid, color: "#ffffff" },
        textColor: "#1f2937"
      },
      grid: {
        vertLines: { color: "#e2e8f0" },
        horzLines: { color: "#e2e8f0" }
      }
    });

    chartApiRef.current = chart;
    candleSeriesRef.current = chart.addCandlestickSeries({
      upColor: "#22c55e",
      downColor: "#ef4444",
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
      borderVisible: false
    });

    volumeSeriesRef.current = chart.addHistogramSeries({
      priceScaleId: "",
      priceFormat: { type: "volume" },
      color: "#94a3b8"
    });

    chart.priceScale("").applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 }
    });

    emaSeriesRef.current = chart.addLineSeries({ color: "#f97316", lineWidth: 2 });
    smaSeriesRef.current = chart.addLineSeries({ color: "#22c55e", lineWidth: 2 });
    vwapSeriesRef.current = chart.addLineSeries({ color: "#6366f1", lineWidth: 2 });
    bbUpperSeriesRef.current = chart.addLineSeries({ color: "#ef4444", lineWidth: 1 });
    bbLowerSeriesRef.current = chart.addLineSeries({ color: "#ef4444", lineWidth: 1 });

    dataPointsRef.current = [];
    currentBucketRef.current = null;
    emaValueRef.current = null;

    const emaPeriod = 20;
    const smaPeriod = 20;
    const bbPeriod = 20;
    const bbStd = 2;

    const ws = connectWebSocket(`/ws/market-data?symbol=${symbol}`, (msg) => {
      const data = msg as MarketDataMessage;
      if (data.channel !== "market-data" || data.symbol !== symbol) return;

      const ts = Math.floor(new Date(data.timestamp).getTime() / 1000);
      const bucket = Math.floor(ts / tfSeconds) * tfSeconds;
      const time = bucket as UTCTimestamp;

      let candle = dataPointsRef.current[dataPointsRef.current.length - 1];
      if (currentBucketRef.current === null || bucket !== currentBucketRef.current) {
        currentBucketRef.current = bucket;
        candle = {
          time,
          open: data.price,
          high: data.price,
          low: data.price,
          close: data.price,
          volume: data.volume
        };
        dataPointsRef.current.push(candle);
        if (dataPointsRef.current.length > 200) dataPointsRef.current.shift();
      } else if (candle) {
        candle.close = data.price;
        candle.high = Math.max(candle.high, data.price);
        candle.low = Math.min(candle.low, data.price);
        candle.volume += data.volume;
      }

      const candleData = dataPointsRef.current.map((p) => ({
        time: p.time,
        open: p.open,
        high: p.high,
        low: p.low,
        close: p.close
      }));

      candleSeriesRef.current?.setData(candleData);

      const volumeData = dataPointsRef.current.map((p) => ({
        time: p.time,
        value: p.volume,
        color: p.close >= p.open ? "#22c55e" : "#ef4444"
      }));
      volumeSeriesRef.current?.setData(volumeData);

      if (showEMARef.current) {
        if (emaValueRef.current === null) {
          emaValueRef.current = data.price;
        } else {
          const emaMultiplier = 2 / (emaPeriod + 1);
          emaValueRef.current =
            data.price * emaMultiplier + emaValueRef.current * (1 - emaMultiplier);
        }
        emaSeriesRef.current?.update({
          time,
          value: Number(emaValueRef.current.toFixed(2))
        });
      }

      if (showSMARef.current && dataPointsRef.current.length >= smaPeriod) {
        const slice = dataPointsRef.current.slice(-smaPeriod);
        const sma = slice.reduce((acc, p) => acc + p.close, 0) / smaPeriod;
        smaSeriesRef.current?.update({ time, value: Number(sma.toFixed(2)) });
      }

      if (showVWAPRef.current) {
        const total = dataPointsRef.current.reduce(
          (acc, p) => acc + p.close * p.volume,
          0
        );
        const vol = dataPointsRef.current.reduce((acc, p) => acc + p.volume, 0);
        if (vol > 0) {
          const vwap = total / vol;
          vwapSeriesRef.current?.update({ time, value: Number(vwap.toFixed(2)) });
        }
      }

      if (showBBRef.current && dataPointsRef.current.length >= bbPeriod) {
        const slice = dataPointsRef.current.slice(-bbPeriod);
        const mean = slice.reduce((acc, p) => acc + p.close, 0) / bbPeriod;
        const variance =
          slice.reduce((acc, p) => acc + (p.close - mean) ** 2, 0) / bbPeriod;
        const std = Math.sqrt(variance);
        const upper = mean + bbStd * std;
        const lower = mean - bbStd * std;
        bbUpperSeriesRef.current?.update({ time, value: Number(upper.toFixed(2)) });
        bbLowerSeriesRef.current?.update({ time, value: Number(lower.toFixed(2)) });
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
      chartApiRef.current = null;
    };
  }, [symbol, tfSeconds]);

  useEffect(() => {
    emaSeriesRef.current?.applyOptions({ visible: showEMA });
    smaSeriesRef.current?.applyOptions({ visible: showSMA });
    vwapSeriesRef.current?.applyOptions({ visible: showVWAP });
    bbUpperSeriesRef.current?.applyOptions({ visible: showBB });
    bbLowerSeriesRef.current?.applyOptions({ visible: showBB });
    showEMARef.current = showEMA;
    showSMARef.current = showSMA;
    showVWAPRef.current = showVWAP;
    showBBRef.current = showBB;
  }, [showEMA, showSMA, showVWAP, showBB]);

  const handleTimeframe = (event: SelectChangeEvent) => {
    setTimeframe(event.target.value);
  };

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2, flexWrap: "wrap" }}>
          <Typography variant="h6">Price Chart</Typography>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <Select value={symbol} onChange={(event) => setSymbol(event.target.value)}>
              <MenuItem value="AAPL">AAPL</MenuItem>
              <MenuItem value="MSFT">MSFT</MenuItem>
              <MenuItem value="TSLA">TSLA</MenuItem>
              <MenuItem value="NVDA">NVDA</MenuItem>
              <MenuItem value="AMD">AMD</MenuItem>
              <MenuItem value="AMZN">AMZN</MenuItem>
            </Select>
          </FormControl>
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
