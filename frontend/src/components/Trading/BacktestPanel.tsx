import { useEffect, useRef, useState } from "react";
import {
  Button,
  Card,
  CardContent,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography
} from "@mui/material";
import { ColorType, UTCTimestamp, createChart } from "lightweight-charts";
import { runBacktest } from "../../services/api";

type BacktestResult = {
  summary: {
    strategy: string;
    symbol: string;
    total_trades: number;
    win_rate: number;
    profit_factor: number;
    total_return: number;
    ending_equity: number;
  };
  equity_curve: Array<{ date: string; equity: number }>;
  trades: Array<{ symbol: string; entryDate: string; exitDate: string; pnl: number; side: string }>;
};

const BacktestPanel = () => {
  const chartRef = useRef<HTMLDivElement | null>(null);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [form, setForm] = useState({
    strategy: "ema_cross",
    symbol: "AAPL",
    start_date: "2024-01-01",
    end_date: "2024-02-15",
    initial_capital: "10000"
  });

  useEffect(() => {
    if (!chartRef.current || !result) return;

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

    const series = chart.addLineSeries({ color: "#0ea5e9", lineWidth: 2 });
    series.setData(
      result.equity_curve.map((point) => ({
        time: Math.floor(new Date(point.date).getTime() / 1000) as UTCTimestamp,
        value: point.equity
      }))
    );

    const handleResize = () => {
      chart.applyOptions({ width: chartRef.current?.clientWidth || 0 });
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [result]);

  const handleRun = async () => {
    const data = await runBacktest({
      ...form,
      initial_capital: Number(form.initial_capital)
    });
    setResult(data);
  };

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
          <Typography variant="h6">Strategy Backtester</Typography>
          <Button variant="contained" onClick={handleRun}>
            Run Backtest
          </Button>
        </Stack>
        <Grid container spacing={2}>
          <Grid item xs={12} md={3}>
            <FormControl fullWidth>
              <InputLabel>Strategy</InputLabel>
              <Select
                value={form.strategy}
                label="Strategy"
                onChange={(e) => setForm((prev) => ({ ...prev, strategy: e.target.value }))}
              >
                <MenuItem value="ema_cross">EMA Cross</MenuItem>
                <MenuItem value="vwap_bounce">VWAP Bounce</MenuItem>
                <MenuItem value="breakout">Breakout</MenuItem>
                <MenuItem value="mean_reversion">Mean Reversion</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={2}>
            <TextField
              fullWidth
              label="Symbol"
              value={form.symbol}
              onChange={(e) => setForm((prev) => ({ ...prev, symbol: e.target.value.toUpperCase() }))}
            />
          </Grid>
          <Grid item xs={12} md={3}>
            <TextField
              fullWidth
              label="Start Date"
              type="date"
              InputLabelProps={{ shrink: true }}
              value={form.start_date}
              onChange={(e) => setForm((prev) => ({ ...prev, start_date: e.target.value }))}
            />
          </Grid>
          <Grid item xs={12} md={3}>
            <TextField
              fullWidth
              label="End Date"
              type="date"
              InputLabelProps={{ shrink: true }}
              value={form.end_date}
              onChange={(e) => setForm((prev) => ({ ...prev, end_date: e.target.value }))}
            />
          </Grid>
          <Grid item xs={12} md={1}>
            <TextField
              fullWidth
              label="Capital"
              value={form.initial_capital}
              onChange={(e) => setForm((prev) => ({ ...prev, initial_capital: e.target.value }))}
            />
          </Grid>
        </Grid>

        <Stack spacing={2} sx={{ mt: 3 }}>
          <div ref={chartRef} />
          {result && (
            <Grid container spacing={2}>
              <Grid item xs={6} md={3}>
                <Typography variant="overline">Total Trades</Typography>
                <Typography variant="h6">{result.summary.total_trades}</Typography>
              </Grid>
              <Grid item xs={6} md={3}>
                <Typography variant="overline">Win Rate</Typography>
                <Typography variant="h6">{result.summary.win_rate}%</Typography>
              </Grid>
              <Grid item xs={6} md={3}>
                <Typography variant="overline">Profit Factor</Typography>
                <Typography variant="h6">{result.summary.profit_factor}</Typography>
              </Grid>
              <Grid item xs={6} md={3}>
                <Typography variant="overline">Total Return</Typography>
                <Typography variant="h6">{result.summary.total_return}%</Typography>
              </Grid>
            </Grid>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
};

export default BacktestPanel;
