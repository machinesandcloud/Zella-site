import { useEffect, useState } from "react";
import {
  Box,
  Card,
  Button,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
  Chip,
  Stack,
  Tooltip
} from "@mui/material";
import { closePosition, fetchPositions, getAutonomousStatus } from "../../services/api";

const formatCurrency = (value: number | undefined): string => {
  if (value === undefined || value === null) return "--";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2
  }).format(value);
};

const ActivePositions = () => {
  const [positions, setPositions] = useState<any[]>([]);
  const [exitRules, setExitRules] = useState<any | null>(null);
  const [positionExitState, setPositionExitState] = useState<Record<string, any>>({});
  const [timings, setTimings] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  const loadPositions = async () => {
    try {
      const data = await fetchPositions();
      // API returns array directly from alpaca_client.get_positions()
      const posArray = Array.isArray(data) ? data : (data?.positions || []);
      setPositions(posArray);
      localStorage.setItem("zella_positions", JSON.stringify(posArray));

      try {
        const status = await getAutonomousStatus();
        setExitRules(status?.exit_rules || null);
        setPositionExitState(status?.position_exit_state || {});
        setTimings(status?.timings || null);
        localStorage.setItem("zella_exit_rules", JSON.stringify(status?.exit_rules || {}));
        localStorage.setItem("zella_position_exit_state", JSON.stringify(status?.position_exit_state || {}));
        localStorage.setItem("zella_engine_timings", JSON.stringify(status?.timings || {}));
      } catch {
        // ignore status fetch errors
      }
    } catch {
      setPositions([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const cached = localStorage.getItem("zella_positions");
    if (cached) {
      try {
        setPositions(JSON.parse(cached));
        setLoading(false);
      } catch {
        // ignore cache parse errors
      }
    }
    const cachedRules = localStorage.getItem("zella_exit_rules");
    if (cachedRules) {
      try {
        setExitRules(JSON.parse(cachedRules));
      } catch {
        // ignore cache parse errors
      }
    }
    const cachedExitState = localStorage.getItem("zella_position_exit_state");
    if (cachedExitState) {
      try {
        setPositionExitState(JSON.parse(cachedExitState));
      } catch {
        // ignore cache parse errors
      }
    }
    const cachedTimings = localStorage.getItem("zella_engine_timings");
    if (cachedTimings) {
      try {
        setTimings(JSON.parse(cachedTimings));
      } catch {
        // ignore cache parse errors
      }
    }

    loadPositions();
    const interval = setInterval(loadPositions, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const notify = (message: string, severity: "success" | "info" | "warning" | "error" = "info") => {
    window.dispatchEvent(new CustomEvent("app:toast", { detail: { message, severity } }));
  };

  const handleClose = async (symbol: string) => {
    try {
      await closePosition(symbol);
      notify(`Close order sent for ${symbol}.`, "success");
      await loadPositions();
    } catch {
      notify(`Failed to close ${symbol}.`, "error");
    }
  };

  return (
    <Card elevation={0} sx={{ border: "1px solid rgba(255,255,255,0.1)", borderRadius: 3 }}>
      <CardContent sx={{ p: 3 }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Active Positions
          </Typography>
          <Stack direction="row" spacing={1} alignItems="center">
            <Chip
              label={`${positions.length} position${positions.length !== 1 ? "s" : ""}`}
              size="small"
              color={positions.length > 0 ? "primary" : "default"}
            />
            {timings?.position_monitor_interval_seconds && (
              <Chip
                label={`Exit check: ${timings.position_monitor_interval_seconds}s`}
                size="small"
                variant="outlined"
              />
            )}
            {timings?.scan_interval_seconds && (
              <Chip
                label={`Scan: ${timings.scan_interval_seconds}s`}
                size="small"
                variant="outlined"
              />
            )}
            {exitRules && (
              <Tooltip
                title={`Exits: time-stop ${exitRules.time_stop_minutes}m (<${exitRules.time_stop_min_pnl}%), max-hold ${exitRules.max_hold_minutes}m, EMA${exitRules.momentum_exit_ema_period}, trail ${exitRules.trailing_lookback_bars} bars`}
                arrow
              >
                <Chip label="Exit rules" size="small" variant="outlined" />
              </Tooltip>
            )}
          </Stack>
        </Box>

        {loading ? (
          <Typography color="text.secondary">Loading positions...</Typography>
        ) : positions.length === 0 ? (
          <Box sx={{
            p: 4,
            textAlign: "center",
            border: "1px dashed rgba(255,255,255,0.1)",
            borderRadius: 2
          }}>
            <Typography color="text.secondary">No active positions</Typography>
            <Typography variant="caption" color="text.secondary">
              The bot will open positions when opportunities are found
            </Typography>
          </Box>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 600 }}>Symbol</TableCell>
                <TableCell sx={{ fontWeight: 600 }} align="right">Qty</TableCell>
                <TableCell sx={{ fontWeight: 600 }} align="right">Entry</TableCell>
                <TableCell sx={{ fontWeight: 600 }} align="right">Current</TableCell>
                <TableCell sx={{ fontWeight: 600 }} align="right">P&L</TableCell>
                <TableCell sx={{ fontWeight: 600 }} align="right">Value</TableCell>
                <TableCell sx={{ fontWeight: 600 }} align="left">Exit Rules</TableCell>
                <TableCell sx={{ fontWeight: 600 }} align="center">Action</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {positions.map((pos, idx) => {
                // Use correct field names from alpaca_client.get_positions()
                const pnl = parseFloat(pos.unrealizedPnL) || 0;
                const pnlPercent = parseFloat(pos.unrealizedPnLPercent) || 0;
                const isProfitable = pnl >= 0;
                const exitState = positionExitState[pos.symbol] || {};
                const stopPrice = exitState.current_stop;
                const breakeven = exitState.breakeven_activated;
                const trailing = exitState.trailing_activated;
                const scaleLevels = Array.isArray(exitState.scale_levels) ? exitState.scale_levels : [];
                const scaleSummary = scaleLevels
                  .map((level: any) => `${level.level}:${level.executed ? "✓" : "•"}`)
                  .join(" ");

                return (
                  <TableRow key={`${pos.symbol}-${idx}`}>
                    <TableCell>
                      <Typography sx={{ fontWeight: 600 }}>{pos.symbol}</Typography>
                    </TableCell>
                    <TableCell align="right">
                      {pos.quantity || pos.qty || "--"}
                    </TableCell>
                    <TableCell align="right">
                      {formatCurrency(pos.avgPrice || pos.avg_entry_price)}
                    </TableCell>
                    <TableCell align="right">
                      {formatCurrency(pos.currentPrice || pos.current_price)}
                    </TableCell>
                    <TableCell align="right">
                      <Box sx={{ color: isProfitable ? "#4caf50" : "#f44336" }}>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {isProfitable ? "+" : ""}{formatCurrency(pnl)}
                        </Typography>
                        <Typography variant="caption">
                          ({isProfitable ? "+" : ""}{pnlPercent.toFixed(2)}%)
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell align="right">
                      {formatCurrency(pos.marketValue || pos.market_value)}
                    </TableCell>
                    <TableCell align="left">
                      <Stack direction="row" spacing={1} flexWrap="wrap">
                        {stopPrice && (
                          <Chip label={`Stop $${Number(stopPrice).toFixed(2)}`} size="small" variant="outlined" />
                        )}
                        <Chip
                          label={breakeven ? "BE ✅" : "BE ❌"}
                          size="small"
                          color={breakeven ? "success" : "default"}
                          variant="outlined"
                        />
                        <Chip
                          label={trailing ? "Trail ✅" : "Trail ❌"}
                          size="small"
                          color={trailing ? "success" : "default"}
                          variant="outlined"
                        />
                        {scaleSummary && (
                          <Tooltip title={`Scale levels (1R/2R/3R): ${scaleSummary}`} arrow>
                            <Chip label="Scale" size="small" variant="outlined" />
                          </Tooltip>
                        )}
                      </Stack>
                    </TableCell>
                    <TableCell align="center">
                      <Button
                        size="small"
                        variant="outlined"
                        color="error"
                        onClick={() => handleClose(pos.symbol)}
                        sx={{ textTransform: "none", minWidth: 60 }}
                      >
                        Close
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
};

export default ActivePositions;
