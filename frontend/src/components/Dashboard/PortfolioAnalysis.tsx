import { useEffect, useState, useMemo, useRef } from "react";
import {
  Card,
  CardContent,
  Grid,
  Stack,
  Typography,
  Box,
  Chip,
  LinearProgress,
  Tooltip
} from "@mui/material";
import {
  PieChart,
  TrendingUp,
  TrendingDown,
  AccountBalance,
  ShowChart,
  Assessment
} from "@mui/icons-material";
import { ColorType, createChart, UTCTimestamp } from "lightweight-charts";
import { fetchAccountSummary, fetchPositions, fetchTrades } from "../../services/api";

type Position = {
  symbol: string;
  qty?: number;
  position?: number;
  avg_entry_price?: number;
  avg_cost?: number;
  market_value?: number;
  unrealized_pl?: number;
  unrealized_plpc?: number;
  current_price?: number;
  market_price?: number;
};

type Trade = {
  pnl?: number | null;
  entry_time?: string | null;
  exit_time?: string | null;
  symbol?: string;
  side?: string;
};

const PortfolioAnalysis = () => {
  const [positions, setPositions] = useState<Position[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [accountValue, setAccountValue] = useState(0);
  const [loading, setLoading] = useState(true);
  const pnlChartRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchPositions()
        .then((data) => {
          // Handle both array and {positions: [...]} formats
          const posArray = Array.isArray(data) ? data : (data?.positions || []);
          setPositions(posArray);
        })
        .catch(() => setPositions([])),
      fetchAccountSummary()
        .then((data) => setAccountValue(Number(data?.equity || data?.NetLiquidation || 0)))
        .catch(() => setAccountValue(0)),
      fetchTrades()
        .then((data) => {
          const tradesArray = Array.isArray(data) ? data : (data?.trades || []);
          setTrades(tradesArray);
        })
        .catch(() => setTrades([]))
    ]).finally(() => setLoading(false));
  }, []);

  // Calculate portfolio metrics
  const metrics = useMemo(() => {
    const totalExposure = positions.reduce(
      (acc, pos) => acc + Math.abs(Number(pos.market_value || (pos.qty || pos.position || 0) * (pos.current_price || pos.avg_entry_price || pos.avg_cost || 0))),
      0
    );

    const totalUnrealizedPL = positions.reduce(
      (acc, pos) => acc + Number(pos.unrealized_pl || 0),
      0
    );

    const longPositions = positions.filter(p => (p.qty || p.position || 0) > 0);
    const shortPositions = positions.filter(p => (p.qty || p.position || 0) < 0);

    const longExposure = longPositions.reduce(
      (acc, pos) => acc + Math.abs(Number(pos.market_value || 0)),
      0
    );

    const shortExposure = shortPositions.reduce(
      (acc, pos) => acc + Math.abs(Number(pos.market_value || 0)),
      0
    );

    return {
      totalExposure,
      totalUnrealizedPL,
      longExposure,
      shortExposure,
      longCount: longPositions.length,
      shortCount: shortPositions.length,
      exposurePercent: accountValue ? (totalExposure / accountValue) * 100 : 0,
      cashPercent: accountValue ? ((accountValue - totalExposure) / accountValue) * 100 : 100
    };
  }, [positions, accountValue]);

  // Calculate P&L by day for the chart
  const dailyPnL = useMemo(() => {
    const pnlByDay = new Map<string, number>();
    trades.forEach((trade) => {
      if (!trade.exit_time || trade.pnl === null || trade.pnl === undefined) return;
      const date = new Date(trade.exit_time).toISOString().split('T')[0];
      pnlByDay.set(date, (pnlByDay.get(date) || 0) + Number(trade.pnl));
    });

    return Array.from(pnlByDay.entries())
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([date, pnl]) => ({
        time: Math.floor(new Date(date).getTime() / 1000) as UTCTimestamp,
        value: pnl,
        color: pnl >= 0 ? '#22c55e' : '#ef4444'
      }));
  }, [trades]);

  // Trade statistics
  const tradeStats = useMemo(() => {
    const closedTrades = trades.filter(t => t.pnl !== null && t.pnl !== undefined);
    const wins = closedTrades.filter(t => Number(t.pnl) > 0);
    const losses = closedTrades.filter(t => Number(t.pnl) < 0);

    const totalPnL = closedTrades.reduce((sum, t) => sum + Number(t.pnl || 0), 0);
    const avgWin = wins.length ? wins.reduce((sum, t) => sum + Number(t.pnl || 0), 0) / wins.length : 0;
    const avgLoss = losses.length ? Math.abs(losses.reduce((sum, t) => sum + Number(t.pnl || 0), 0) / losses.length) : 0;

    return {
      totalTrades: closedTrades.length,
      wins: wins.length,
      losses: losses.length,
      winRate: closedTrades.length ? (wins.length / closedTrades.length) * 100 : 0,
      totalPnL,
      avgWin,
      avgLoss,
      profitFactor: avgLoss > 0 ? avgWin / avgLoss : 0,
      expectancy: closedTrades.length ? totalPnL / closedTrades.length : 0
    };
  }, [trades]);

  // Render P&L histogram chart
  useEffect(() => {
    if (!pnlChartRef.current || dailyPnL.length === 0) return;

    const chart = createChart(pnlChartRef.current, {
      width: pnlChartRef.current.clientWidth,
      height: 180,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#94a3b8'
      },
      grid: {
        vertLines: { color: 'rgba(255,255,255,0.04)' },
        horzLines: { color: 'rgba(255,255,255,0.04)' }
      },
      rightPriceScale: {
        borderColor: 'rgba(255,255,255,0.1)'
      },
      timeScale: {
        borderColor: 'rgba(255,255,255,0.1)'
      }
    });

    const series = chart.addHistogramSeries({
      priceFormat: { type: 'price', precision: 2, minMove: 0.01 }
    });
    series.setData(dailyPnL);
    chart.timeScale().fitContent();

    const handleResize = () => {
      chart.applyOptions({ width: pnlChartRef.current?.clientWidth || 0 });
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [dailyPnL]);

  // Position allocation data
  const allocationData = useMemo(() => {
    if (positions.length === 0) return [];

    return positions
      .map(pos => ({
        symbol: pos.symbol,
        value: Math.abs(Number(pos.market_value || (pos.qty || pos.position || 0) * (pos.current_price || pos.avg_entry_price || 0))),
        unrealizedPL: Number(pos.unrealized_pl || 0),
        percent: 0
      }))
      .sort((a, b) => b.value - a.value)
      .map(item => ({
        ...item,
        percent: metrics.totalExposure ? (item.value / metrics.totalExposure) * 100 : 0
      }));
  }, [positions, metrics.totalExposure]);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  };

  if (loading) {
    return (
      <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>Portfolio Analysis</Typography>
          <LinearProgress />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        {/* Header */}
        <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 3 }}>
          <Assessment sx={{ fontSize: 28, color: "primary.main" }} />
          <Box>
            <Typography variant="h6" fontWeight="bold">Portfolio Analysis</Typography>
            <Typography variant="body2" color="text.secondary">
              Position allocation and trading performance
            </Typography>
          </Box>
        </Stack>

        {/* Key Metrics */}
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={6} md={3}>
            <Box sx={{ p: 2, borderRadius: 2, bgcolor: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
              <Stack direction="row" alignItems="center" spacing={1}>
                <AccountBalance sx={{ fontSize: 18, color: 'primary.main' }} />
                <Typography variant="overline" color="text.secondary">Account Value</Typography>
              </Stack>
              <Typography variant="h6" fontWeight="bold">{formatCurrency(accountValue)}</Typography>
            </Box>
          </Grid>
          <Grid item xs={6} md={3}>
            <Box sx={{ p: 2, borderRadius: 2, bgcolor: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
              <Stack direction="row" alignItems="center" spacing={1}>
                <ShowChart sx={{ fontSize: 18, color: 'warning.main' }} />
                <Typography variant="overline" color="text.secondary">Total Exposure</Typography>
              </Stack>
              <Typography variant="h6" fontWeight="bold">{formatCurrency(metrics.totalExposure)}</Typography>
              <Typography variant="caption" color="text.secondary">
                {metrics.exposurePercent.toFixed(1)}% of account
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={6} md={3}>
            <Box sx={{ p: 2, borderRadius: 2, bgcolor: metrics.totalUnrealizedPL >= 0 ? 'rgba(34,197,94,0.08)' : 'rgba(239,68,68,0.08)', border: `1px solid ${metrics.totalUnrealizedPL >= 0 ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'}` }}>
              <Stack direction="row" alignItems="center" spacing={1}>
                {metrics.totalUnrealizedPL >= 0 ?
                  <TrendingUp sx={{ fontSize: 18, color: 'success.main' }} /> :
                  <TrendingDown sx={{ fontSize: 18, color: 'error.main' }} />
                }
                <Typography variant="overline" color="text.secondary">Unrealized P&L</Typography>
              </Stack>
              <Typography variant="h6" fontWeight="bold" color={metrics.totalUnrealizedPL >= 0 ? 'success.main' : 'error.main'}>
                {metrics.totalUnrealizedPL >= 0 ? '+' : ''}{formatCurrency(metrics.totalUnrealizedPL)}
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={6} md={3}>
            <Box sx={{ p: 2, borderRadius: 2, bgcolor: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
              <Stack direction="row" alignItems="center" spacing={1}>
                <PieChart sx={{ fontSize: 18, color: 'info.main' }} />
                <Typography variant="overline" color="text.secondary">Positions</Typography>
              </Stack>
              <Typography variant="h6" fontWeight="bold">{positions.length}</Typography>
              <Stack direction="row" spacing={1}>
                <Chip label={`${metrics.longCount} Long`} size="small" color="success" variant="outlined" sx={{ height: 20, fontSize: '0.65rem' }} />
                <Chip label={`${metrics.shortCount} Short`} size="small" color="error" variant="outlined" sx={{ height: 20, fontSize: '0.65rem' }} />
              </Stack>
            </Box>
          </Grid>
        </Grid>

        {/* Trade Statistics */}
        {tradeStats.totalTrades > 0 && (
          <Box sx={{ mb: 3, p: 2, borderRadius: 2, bgcolor: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
            <Typography variant="subtitle2" fontWeight="bold" sx={{ mb: 2 }}>Trading Statistics</Typography>
            <Grid container spacing={2}>
              <Grid item xs={4} md={2}>
                <Typography variant="caption" color="text.secondary">Win Rate</Typography>
                <Typography variant="h6" fontWeight="bold" color={tradeStats.winRate >= 50 ? 'success.main' : 'error.main'}>
                  {tradeStats.winRate.toFixed(1)}%
                </Typography>
              </Grid>
              <Grid item xs={4} md={2}>
                <Typography variant="caption" color="text.secondary">Total Trades</Typography>
                <Typography variant="h6" fontWeight="bold">{tradeStats.totalTrades}</Typography>
              </Grid>
              <Grid item xs={4} md={2}>
                <Typography variant="caption" color="text.secondary">Wins / Losses</Typography>
                <Typography variant="h6" fontWeight="bold">
                  <span style={{ color: '#22c55e' }}>{tradeStats.wins}</span>
                  {' / '}
                  <span style={{ color: '#ef4444' }}>{tradeStats.losses}</span>
                </Typography>
              </Grid>
              <Grid item xs={4} md={2}>
                <Typography variant="caption" color="text.secondary">Profit Factor</Typography>
                <Typography variant="h6" fontWeight="bold" color={tradeStats.profitFactor >= 1 ? 'success.main' : 'error.main'}>
                  {tradeStats.profitFactor.toFixed(2)}
                </Typography>
              </Grid>
              <Grid item xs={4} md={2}>
                <Typography variant="caption" color="text.secondary">Expectancy</Typography>
                <Typography variant="h6" fontWeight="bold" color={tradeStats.expectancy >= 0 ? 'success.main' : 'error.main'}>
                  {formatCurrency(tradeStats.expectancy)}
                </Typography>
              </Grid>
              <Grid item xs={4} md={2}>
                <Typography variant="caption" color="text.secondary">Total P&L</Typography>
                <Typography variant="h6" fontWeight="bold" color={tradeStats.totalPnL >= 0 ? 'success.main' : 'error.main'}>
                  {tradeStats.totalPnL >= 0 ? '+' : ''}{formatCurrency(tradeStats.totalPnL)}
                </Typography>
              </Grid>
            </Grid>
          </Box>
        )}

        {/* Charts Section */}
        <Grid container spacing={3}>
          {/* Daily P&L Chart */}
          <Grid item xs={12} md={7}>
            <Box sx={{ p: 2, borderRadius: 2, bgcolor: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
              <Typography variant="subtitle2" fontWeight="bold" sx={{ mb: 2 }}>Daily P&L</Typography>
              {dailyPnL.length > 0 ? (
                <div ref={pnlChartRef} />
              ) : (
                <Box sx={{ height: 180, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Typography variant="body2" color="text.secondary">No trade history yet</Typography>
                </Box>
              )}
            </Box>
          </Grid>

          {/* Position Allocation */}
          <Grid item xs={12} md={5}>
            <Box sx={{ p: 2, borderRadius: 2, bgcolor: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
              <Typography variant="subtitle2" fontWeight="bold" sx={{ mb: 2 }}>Position Allocation</Typography>
              {allocationData.length > 0 ? (
                <Stack spacing={1.5}>
                  {allocationData.slice(0, 8).map((item, index) => (
                    <Box key={item.symbol}>
                      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 0.5 }}>
                        <Stack direction="row" spacing={1} alignItems="center">
                          <Typography variant="body2" fontWeight="bold">{item.symbol}</Typography>
                          <Chip
                            label={`${item.percent.toFixed(1)}%`}
                            size="small"
                            sx={{ height: 18, fontSize: '0.65rem' }}
                          />
                        </Stack>
                        <Tooltip title={`P&L: ${formatCurrency(item.unrealizedPL)}`}>
                          <Typography
                            variant="caption"
                            color={item.unrealizedPL >= 0 ? 'success.main' : 'error.main'}
                          >
                            {item.unrealizedPL >= 0 ? '+' : ''}{formatCurrency(item.unrealizedPL)}
                          </Typography>
                        </Tooltip>
                      </Stack>
                      <LinearProgress
                        variant="determinate"
                        value={item.percent}
                        sx={{
                          height: 6,
                          borderRadius: 3,
                          bgcolor: 'rgba(255,255,255,0.05)',
                          '& .MuiLinearProgress-bar': {
                            borderRadius: 3,
                            bgcolor: `hsl(${(index * 40) % 360}, 70%, 50%)`
                          }
                        }}
                      />
                    </Box>
                  ))}
                  {allocationData.length > 8 && (
                    <Typography variant="caption" color="text.secondary">
                      +{allocationData.length - 8} more positions
                    </Typography>
                  )}

                  {/* Cash allocation */}
                  <Box sx={{ mt: 1, pt: 1, borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                    <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 0.5 }}>
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Typography variant="body2" fontWeight="bold" color="text.secondary">Cash</Typography>
                        <Chip
                          label={`${metrics.cashPercent.toFixed(1)}%`}
                          size="small"
                          sx={{ height: 18, fontSize: '0.65rem' }}
                        />
                      </Stack>
                      <Typography variant="caption" color="text.secondary">
                        {formatCurrency(accountValue - metrics.totalExposure)}
                      </Typography>
                    </Stack>
                    <LinearProgress
                      variant="determinate"
                      value={metrics.cashPercent}
                      sx={{
                        height: 6,
                        borderRadius: 3,
                        bgcolor: 'rgba(255,255,255,0.05)',
                        '& .MuiLinearProgress-bar': {
                          borderRadius: 3,
                          bgcolor: '#64748b'
                        }
                      }}
                    />
                  </Box>
                </Stack>
              ) : (
                <Box sx={{ height: 180, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Typography variant="body2" color="text.secondary">No open positions</Typography>
                </Box>
              )}
            </Box>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
};

export default PortfolioAnalysis;
