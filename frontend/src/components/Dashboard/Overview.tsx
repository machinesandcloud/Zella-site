import { useEffect, useState } from "react";
import { Box, Card, CardContent, Grid, Typography, Chip, Stack } from "@mui/material";
import { fetchAlpacaAccount, fetchAlpacaStatus } from "../../services/api";

const formatCurrency = (value: number | string | undefined): string => {
  if (value === undefined || value === null || value === "") return "$0.00";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "$0.00";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2
  }).format(num);
};

const Overview = () => {
  const [summary, setSummary] = useState<Record<string, any>>({});
  const [alpacaStatus, setAlpacaStatus] = useState<{connected?: boolean; mode?: string} | null>(null);
  const [lastUpdate, setLastUpdate] = useState<string>("");

  useEffect(() => {
    const loadData = () => {
      fetchAlpacaAccount()
        .then((data) => {
          setSummary(data || {});
          setLastUpdate(new Date().toLocaleTimeString());
        })
        .catch(() => setSummary({}));

      fetchAlpacaStatus()
        .then((data) => setAlpacaStatus(data))
        .catch(() => setAlpacaStatus(null));
    };

    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  const dailyPnL = parseFloat(summary.UnrealizedPnL) || 0;
  const accountValue = parseFloat(summary.NetLiquidation) || 0;
  const dailyPnLPercent = accountValue > 0 ? ((dailyPnL / accountValue) * 100).toFixed(2) : "0.00";

  return (
    <Card elevation={0} sx={{ border: "1px solid rgba(255,255,255,0.1)", borderRadius: 3 }}>
      <CardContent sx={{ p: 3 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>Account Summary</Typography>
          <Stack direction="row" spacing={1}>
            <Chip
              label={alpacaStatus?.connected ? "Connected" : "Disconnected"}
              color={alpacaStatus?.connected ? "success" : "error"}
              size="small"
            />
          </Stack>
        </Stack>

        <Grid container spacing={2}>
          {/* Account Value - Large display */}
          <Grid item xs={12}>
            <Box sx={{
              p: 2.5,
              borderRadius: 2,
              background: "linear-gradient(135deg, rgba(63, 208, 201, 0.15), rgba(63, 208, 201, 0.05))",
              border: "1px solid rgba(63, 208, 201, 0.3)"
            }}>
              <Typography variant="overline" color="text.secondary">
                Total Account Value
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 700, color: "#3fd0c9", mt: 0.5 }}>
                {formatCurrency(summary.NetLiquidation)}
              </Typography>
            </Box>
          </Grid>

          {/* Cash & Buying Power */}
          <Grid item xs={6}>
            <Box sx={{ p: 2, borderRadius: 2, border: "1px solid rgba(255,255,255,0.1)", minHeight: 80 }}>
              <Typography variant="overline" color="text.secondary" sx={{ fontSize: "0.65rem" }}>
                Cash Available
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 600, mt: 0.5 }}>
                {formatCurrency(summary.CashBalance)}
              </Typography>
            </Box>
          </Grid>

          <Grid item xs={6}>
            <Box sx={{ p: 2, borderRadius: 2, border: "1px solid rgba(255,255,255,0.1)", minHeight: 80 }}>
              <Typography variant="overline" color="text.secondary" sx={{ fontSize: "0.65rem" }}>
                Buying Power
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 600, mt: 0.5 }}>
                {formatCurrency(summary.BuyingPower)}
              </Typography>
            </Box>
          </Grid>

          {/* Daily P&L */}
          <Grid item xs={12}>
            <Box sx={{
              p: 2,
              borderRadius: 2,
              border: `1px solid ${dailyPnL >= 0 ? "rgba(76, 175, 80, 0.4)" : "rgba(244, 67, 54, 0.4)"}`,
              background: dailyPnL >= 0 ? "rgba(76, 175, 80, 0.1)" : "rgba(244, 67, 54, 0.1)"
            }}>
              <Typography variant="overline" color="text.secondary" sx={{ fontSize: "0.65rem" }}>
                Today's P&L
              </Typography>
              <Stack direction="row" alignItems="baseline" spacing={1} sx={{ mt: 0.5 }}>
                <Typography variant="h5" sx={{ fontWeight: 700, color: dailyPnL >= 0 ? "#4caf50" : "#f44336" }}>
                  {dailyPnL >= 0 ? "+" : ""}{formatCurrency(dailyPnL)}
                </Typography>
                <Typography variant="body2" sx={{ color: dailyPnL >= 0 ? "#4caf50" : "#f44336" }}>
                  ({dailyPnL >= 0 ? "+" : ""}{dailyPnLPercent}%)
                </Typography>
              </Stack>
            </Box>
          </Grid>
        </Grid>

        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 2, textAlign: "right" }}>
          Last updated: {lastUpdate || "--"}
        </Typography>
      </CardContent>
    </Card>
  );
};

export default Overview;
