import { useEffect, useRef, useState } from "react";
import {
  Button,
  Card,
  CardContent,
  CircularProgress,
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
import { fetchBacktestStrategies, runBacktest } from "../../services/api";

type StrategyOption = { name: string; display_name: string };

type BacktestResult = {
  summary: {
    strategy: string;
    symbol: string;
    total_trades: number;
    win_rate: number;
    profit_factor: number;
    total_return: number;
    total_return_pct: number;
    ending_equity: number;
    sharpe_ratio: number;
    sortino_ratio: number;
    max_drawdown: number;
    max_drawdown_pct: number;
    calmar_ratio: number;
  };
  equity_curve: Array<{ date: string; equity: number }>;
  trades: Array<{
    symbol: string;
    entryDate: string;
    exitDate: string;
    entryPrice: number;
    exitPrice: number;
    pnl: number;
    pnl_percent: number;
    side: string;
    exit_reason: string;
  }>;
};

const MetricBox = ({ label, value, color }: { label: string; value: string; color?: string }) => (
  <Grid item xs={6} md={3}>
    <Typography variant="overline" color="text.secondary">{label}</Typography>
    <Typography variant="h6" color={color}>{value}</Typography>
  </Grid>
);

const BacktestPanel = () => {
  const chartRef = useRef<HTMLDivElement | null>(null);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [strategies, setStrategies] = useState<StrategyOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    strategy: "ema_cross",
    symbol: "AAPL",
    start_date: "2024-01-01",
    end_date: "2024-03-31",
    initial_capital: "10000"
  });

  useEffect(() => {
    fetchBacktestStrategies()
      .then(setStrategies)
      .catch(() => {
        // Fallback to common strategies if API unavailable
        setStrategies([
          { name: "ema_cross", display_name: "EMA Cross" },
          { name: "vwap_bounce", display_name: "Vwap Bounce" },
          { name: "breakout", display_name: "Breakout" },
          { name: "momentum", display_name: "Momentum" },
          { name: "orb", display_name: "Orb" },
          { name: "trend_follow", display_name: "Trend Follow" },
        ]);
      });
  }, []);

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
    setLoading(true);
    setError(null);
    try {
      const data = await runBacktest({
        ...form,
        initial_capital: Number(form.initial_capital)
      });
      setResult(data);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Backtest failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = () => {
    if (!result) return;
    const header = "symbol,side,entryDate,exitDate,entryPrice,exitPrice,pnl,pnl_pct,exit_reason";
    const rows = result.trades.map(
      (t) => `${t.symbol},${t.side},${t.entryDate},${t.exitDate},${t.entryPrice},${t.exitPrice ?? ""},${t.pnl},${t.pnl_percent},${t.exit_reason}`
    );
    const csv = [header, ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `backtest_${form.strategy}_${form.symbol}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const s = result?.summary;
  const returnColor = s && s.total_return_pct >= 0 ? "success.main" : "error.main";

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
          <Typography variant="h6">Strategy Backtester</Typography>
          <Stack direction="row" spacing={1}>
            <Button variant="contained" onClick={handleRun} disabled={loading}>
              {loading ? <CircularProgress size={18} color="inherit" /> : "Run Backtest"}
            </Button>
            <Button variant="outlined" onClick={handleExport} disabled={!result}>
              Export CSV
            </Button>
          </Stack>
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
                {strategies.map((s) => (
                  <MenuItem key={s.name} value={s.name}>{s.display_name}</MenuItem>
                ))}
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
          <Grid item xs={12} md={2}>
            <TextField
              fullWidth
              label="Start Date"
              type="date"
              InputLabelProps={{ shrink: true }}
              value={form.start_date}
              onChange={(e) => setForm((prev) => ({ ...prev, start_date: e.target.value }))}
            />
          </Grid>
          <Grid item xs={12} md={2}>
            <TextField
              fullWidth
              label="End Date"
              type="date"
              InputLabelProps={{ shrink: true }}
              value={form.end_date}
              onChange={(e) => setForm((prev) => ({ ...prev, end_date: e.target.value }))}
            />
          </Grid>
          <Grid item xs={12} md={2}>
            <TextField
              fullWidth
              label="Capital ($)"
              value={form.initial_capital}
              onChange={(e) => setForm((prev) => ({ ...prev, initial_capital: e.target.value }))}
            />
          </Grid>
        </Grid>

        {error && (
          <Typography color="error" sx={{ mt: 2 }}>{error}</Typography>
        )}

        <Stack spacing={2} sx={{ mt: 3 }}>
          <div ref={chartRef} />

          {s && (
            <>
              {/* Row 1: P&L overview */}
              <Grid container spacing={2}>
                <MetricBox
                  label="Total Return"
                  value={`${s.total_return_pct >= 0 ? "+" : ""}${s.total_return_pct.toFixed(1)}%`}
                  color={returnColor}
                />
                <MetricBox label="Ending Equity" value={`$${s.ending_equity.toLocaleString()}`} />
                <MetricBox label="Total Trades" value={String(s.total_trades)} />
                <MetricBox label="Win Rate" value={`${s.win_rate.toFixed(1)}%`} />
              </Grid>

              {/* Row 2: Risk metrics */}
              <Grid container spacing={2}>
                <MetricBox label="Sharpe Ratio" value={s.sharpe_ratio.toFixed(2)} />
                <MetricBox label="Max Drawdown" value={`${s.max_drawdown_pct.toFixed(1)}%`} />
                <MetricBox label="Profit Factor" value={s.profit_factor.toFixed(2)} />
                <MetricBox label="Calmar Ratio" value={s.calmar_ratio.toFixed(2)} />
              </Grid>
            </>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
};

export default BacktestPanel;
