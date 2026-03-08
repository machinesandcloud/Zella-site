import { useEffect, useState } from "react";
import { Alert, Button, Card, CardContent, CircularProgress, Grid, TextField, Typography, Stack } from "@mui/material";
import api from "../../services/api";

const RiskSettings = () => {
  const [values, setValues] = useState({
    max_position_size_percent: 10,
    max_daily_loss: 500,
    max_concurrent_positions: 5,
    risk_per_trade_percent: 2
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    const loadSettings = async () => {
      try {
        const { data } = await api.get("/api/settings/risk");
        setValues({
          max_position_size_percent: data.max_position_size_percent ?? 10,
          max_daily_loss: data.max_daily_loss ?? 500,
          max_concurrent_positions: data.max_concurrent_positions ?? 5,
          risk_per_trade_percent: data.risk_per_trade_percent ?? 2
        });
      } catch {
        // Use defaults if API fails
      } finally {
        setLoading(false);
      }
    };
    loadSettings();
  }, []);

  const update = (key: string, value: number) => {
    setValues((prev) => ({ ...prev, [key]: value }));
    setMessage(null);
  };

  const save = async () => {
    setSaving(true);
    setMessage(null);
    try {
      await api.put("/api/settings/risk", values);
      setMessage({ type: "success", text: "Risk settings saved successfully" });
    } catch (err: any) {
      setMessage({ type: "error", text: err?.response?.data?.detail || "Failed to save settings" });
    } finally {
      setSaving(false);
    }
  };

  const killSwitch = async () => {
    const confirmed = window.confirm(
      "KILL SWITCH\n\nThis will immediately:\n- Trigger emergency stop\n- Cancel all open orders\n- Halt all trading\n\nContinue?"
    );
    if (!confirmed) return;

    try {
      await api.post("/api/trading/kill-switch");
      setMessage({ type: "success", text: "Kill switch triggered - all trading halted" });
    } catch (err: any) {
      setMessage({ type: "error", text: err?.response?.data?.detail || "Failed to trigger kill switch" });
    }
  };

  if (loading) {
    return (
      <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
        <CardContent sx={{ textAlign: "center", py: 4 }}>
          <CircularProgress size={24} />
          <Typography sx={{ mt: 1 }}>Loading settings...</Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Risk Management
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Keep risk per trade consistent. Many traders reduce percentage risk as account size
          grows. Define stops before entry to quantify risk.
        </Typography>

        {message && (
          <Alert severity={message.type} sx={{ mb: 2 }} onClose={() => setMessage(null)}>
            {message.text}
          </Alert>
        )}

        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Max Position Size (%)"
              type="number"
              value={values.max_position_size_percent}
              onChange={(e) => update("max_position_size_percent", Number(e.target.value))}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Max Daily Loss ($)"
              type="number"
              value={values.max_daily_loss}
              onChange={(e) => update("max_daily_loss", Number(e.target.value))}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Max Concurrent Positions"
              type="number"
              value={values.max_concurrent_positions}
              onChange={(e) => update("max_concurrent_positions", Number(e.target.value))}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Risk per Trade (%)"
              type="number"
              value={values.risk_per_trade_percent}
              onChange={(e) => update("risk_per_trade_percent", Number(e.target.value))}
            />
          </Grid>
          <Grid item xs={12}>
            <Stack direction="row" spacing={2}>
              <Button variant="contained" onClick={save} disabled={saving}>
                {saving ? <CircularProgress size={20} /> : "Save"}
              </Button>
              <Button variant="outlined" color="error" onClick={killSwitch}>
                Kill Switch
              </Button>
            </Stack>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
};

export default RiskSettings;
