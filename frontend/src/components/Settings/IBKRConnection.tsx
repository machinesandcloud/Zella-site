import { useEffect, useState } from "react";
import {
  Button,
  Card,
  CardContent,
  FormControlLabel,
  Stack,
  Switch,
  TextField,
  Typography
} from "@mui/material";
import api, { fetchIbkrWebapiStatus } from "../../services/api";

const IBKRConnection = () => {
  const [host, setHost] = useState("127.0.0.1");
  const [port, setPort] = useState(7497);
  const [clientId, setClientId] = useState(1);
  const [paper, setPaper] = useState(true);
  const [webapi, setWebapi] = useState<{ enabled: boolean; connected?: boolean; base_url?: string }>({ enabled: false });

  useEffect(() => {
    fetchIbkrWebapiStatus()
      .then((data) => setWebapi(data))
      .catch(() => setWebapi({ enabled: false }));
  }, []);

  const connect = async () => {
    if (!paper) {
      const confirmed = window.confirm("You are switching to LIVE trading. Continue?");
      if (!confirmed) return;
    }
    await api.post("/api/ibkr/connect", {
      host,
      port,
      client_id: clientId,
      is_paper_trading: paper
    });
  };

  const disconnect = async () => {
    await api.post("/api/ibkr/disconnect");
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
            <Button variant="contained" onClick={connect} disabled={webapi.enabled}>
              Connect
            </Button>
            <Button variant="outlined" onClick={disconnect} disabled={webapi.enabled}>
              Disconnect
            </Button>
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
};

export default IBKRConnection;
