import { useEffect, useState } from "react";
import { Alert, Button, Card, CardContent, LinearProgress, Stack, Typography } from "@mui/material";
import { fetchAlpacaAccount, fetchAlpacaPositions, fetchAlpacaStatus } from "../../services/api";

type AlpacaStatus = {
  enabled: boolean;
  connected?: boolean;
  mode?: string;
};

type AlpacaAccount = {
  NetLiquidation?: number;
  BuyingPower?: number;
  CashBalance?: number;
  RealizedPnL?: number;
  UnrealizedPnL?: number;
};

const AlpacaConnection = () => {
  const [status, setStatus] = useState<AlpacaStatus | null>(null);
  const [account, setAccount] = useState<AlpacaAccount | null>(null);
  const [positionsCount, setPositionsCount] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadAll = async () => {
    setError(null);
    setLoading(true);
    try {
      const statusData = await fetchAlpacaStatus();
      setStatus(statusData);
      if (statusData?.connected) {
        const [accountData, positionsData] = await Promise.all([
          fetchAlpacaAccount(),
          fetchAlpacaPositions()
        ]);
        setAccount(accountData);
        setPositionsCount(Array.isArray(positionsData?.positions) ? positionsData.positions.length : 0);
      } else {
        setAccount(null);
        setPositionsCount(null);
      }
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || "Unable to load Alpaca status.";
      setError(detail);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    const refresh = async () => {
      if (cancelled) return;
      await loadAll();
    };
    refresh();
    const timer = window.setInterval(refresh, 30000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Alpaca Connection
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Alpaca API is used for trading and market data. Authentication is via API keys only.
        </Typography>
        {loading && <LinearProgress sx={{ mb: 2 }} />}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        {status && (
          <Alert severity={status.connected ? "success" : "warning"} sx={{ mb: 2 }}>
            {status.connected ? `Connected (${status.mode || "PAPER"})` : "Not connected"}
          </Alert>
        )}
        {account && (
          <Stack spacing={1.2} sx={{ mb: 2 }}>
            <Typography variant="body2">Net Liquidation: ${account.NetLiquidation?.toLocaleString()}</Typography>
            <Typography variant="body2">Buying Power: ${account.BuyingPower?.toLocaleString()}</Typography>
            <Typography variant="body2">Cash Balance: ${account.CashBalance?.toLocaleString()}</Typography>
            <Typography variant="body2">Positions: {positionsCount ?? 0}</Typography>
          </Stack>
        )}
        <Button variant="outlined" onClick={loadAll} disabled={loading}>
          Refresh Status
        </Button>
      </CardContent>
    </Card>
  );
};

export default AlpacaConnection;
