import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Card,
  CardContent,
  FormControlLabel,
  LinearProgress,
  Stack,
  Switch,
  TextField,
  Typography
} from "@mui/material";
import api, { fetchIbkrStatus, fetchIbkrWebapiStatus } from "../../services/api";

const IBKRConnection = () => {
  const [host, setHost] = useState("127.0.0.1");
  const [port, setPort] = useState(7497);
  const [clientId, setClientId] = useState(1);
  const [paper, setPaper] = useState(true);
  const [webapi, setWebapi] = useState<{ enabled: boolean; connected?: boolean; base_url?: string }>({ enabled: false });
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [statusSeverity, setStatusSeverity] = useState<"success" | "error" | "info">("info");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchIbkrWebapiStatus()
      .then((data) => setWebapi(data))
      .catch(() => setWebapi({ enabled: false }));
  }, []);

  const connect = async () => {
    setStatusMessage(null);
    if (!paper) {
      const confirmed = window.confirm("You are switching to LIVE trading. Continue?");
      if (!confirmed) return;
    }
    try {
      setLoading(true);
      await api.post("/api/ibkr/connect", {
        host,
        port,
        client_id: clientId,
        is_paper_trading: paper
      });
      const status = await fetchIbkrStatus();
      setStatusSeverity(status?.connected ? "success" : "info");
      setStatusMessage(status?.connected ? "Connected to IBKR." : "Connection requested. Check IBKR Gateway.");
    } catch (error: any) {
      const detail =
        error?.response?.data?.detail ||
        error?.message ||
        "Unable to connect. Check backend URL and IBKR Gateway.";
      setStatusSeverity("error");
      setStatusMessage(detail);
    } finally {
      setLoading(false);
    }
  };

  const disconnect = async () => {
    setStatusMessage(null);
    try {
      setLoading(true);
      await api.post("/api/ibkr/disconnect");
      setStatusSeverity("info");
      setStatusMessage("Disconnected.");
    } catch (error: any) {
      const detail =
        error?.response?.data?.detail ||
        error?.message ||
        "Unable to disconnect.";
      setStatusSeverity("error");
      setStatusMessage(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          IBKR Connection
        </Typography>
        {webapi.enabled && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Web API enabled ({webapi.base_url}). Authenticate via IBKR Client Portal Gateway UI.
            Status: {webapi.connected ? "Authenticated" : "Not authenticated"}.
          </Typography>
        )}
        {loading && <LinearProgress sx={{ mb: 2 }} />}
        {statusMessage && (
          <Alert severity={statusSeverity} sx={{ mb: 2 }}>
            {statusMessage}
          </Alert>
        )}
        <Stack spacing={2}>
          <TextField label="Host" value={host} onChange={(e) => setHost(e.target.value)} />
          <TextField
            label="Port"
            type="number"
            value={port}
            onChange={(e) => setPort(Number(e.target.value))}
          />
          <TextField
            label="Client ID"
            type="number"
            value={clientId}
            onChange={(e) => setClientId(Number(e.target.value))}
          />
          <FormControlLabel
            control={<Switch checked={paper} onChange={(e) => setPaper(e.target.checked)} />}
            label="Paper Trading"
          />
          <Stack direction="row" spacing={2}>
            <Button variant="contained" onClick={connect} disabled={webapi.enabled || loading}>
              Connect
            </Button>
            <Button variant="outlined" onClick={disconnect} disabled={webapi.enabled || loading}>
              Disconnect
            </Button>
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
};

export default IBKRConnection;
