import { useEffect, useMemo, useRef, useState } from "react";
import {
  Button,
  Card,
  CardContent,
  Chip,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Switch,
  TextField,
  Typography
} from "@mui/material";
import {
  acknowledgeAlert,
  fetchAlertSettings,
  fetchAlerts,
  updateAlertSettings
} from "../../services/api";

type AlertItem = {
  id: string;
  severity: string;
  message: string;
  created_at: string;
  acknowledged: boolean;
};

type AlertSettings = {
  in_app: boolean;
  email: boolean;
  sms: boolean;
  webhook: boolean;
  sound_enabled: boolean;
};

const NotificationCenter = () => {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [settings, setSettings] = useState<AlertSettings | null>(null);
  const [severityFilter, setSeverityFilter] = useState("ALL");
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [search, setSearch] = useState("");
  const prevAlertCount = useRef(0);

  const load = () => {
    fetchAlerts()
      .then((data) => setAlerts(data || []))
      .catch(() => setAlerts([]));
  };

  const loadSettings = () => {
    fetchAlertSettings()
      .then((data) => setSettings(data))
      .catch(() => setSettings(null));
  };

  useEffect(() => {
    load();
    loadSettings();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!settings?.sound_enabled) {
      prevAlertCount.current = alerts.length;
      return;
    }
    if (alerts.length > prevAlertCount.current) {
      const audioContextClass = window.AudioContext;
      if (audioContextClass) {
        const context = new audioContextClass();
        const oscillator = context.createOscillator();
        const gain = context.createGain();
        oscillator.type = "sine";
        oscillator.frequency.value = 880;
        gain.gain.value = 0.05;
        oscillator.connect(gain);
        gain.connect(context.destination);
        oscillator.start();
        setTimeout(() => {
          oscillator.stop();
          context.close();
        }, 120);
      }
    }
    prevAlertCount.current = alerts.length;
  }, [alerts, settings?.sound_enabled]);

  const ack = async (id: string) => {
    await acknowledgeAlert(id);
    load();
  };

  const updateSettings = async (next: Partial<AlertSettings>) => {
    if (!settings) return;
    const updated = await updateAlertSettings(next);
    setSettings(updated);
  };

  const filteredAlerts = useMemo(() => {
    return alerts.filter((alert) => {
      if (severityFilter !== "ALL" && alert.severity !== severityFilter) return false;
      if (unreadOnly && alert.acknowledged) return false;
      if (search && !alert.message.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    });
  }, [alerts, severityFilter, unreadOnly, search]);

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
          <Typography variant="h6">Notifications</Typography>
          <Button size="small" variant="outlined" onClick={load}>
            Refresh
          </Button>
        </Stack>

        <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ mb: 2 }}>
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel>Severity</InputLabel>
            <Select
              value={severityFilter}
              label="Severity"
              onChange={(e) => setSeverityFilter(e.target.value)}
            >
              <MenuItem value="ALL">All</MenuItem>
              <MenuItem value="INFO">Info</MenuItem>
              <MenuItem value="WARNING">Warning</MenuItem>
              <MenuItem value="CRITICAL">Critical</MenuItem>
            </Select>
          </FormControl>
          <TextField
            size="small"
            label="Search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="body2">Unread only</Typography>
            <Switch checked={unreadOnly} onChange={() => setUnreadOnly(!unreadOnly)} />
          </Stack>
        </Stack>

        <Stack spacing={1} sx={{ mb: 3 }}>
          {filteredAlerts.length === 0 && (
            <Typography variant="body2" color="text.secondary">
              No alerts.
            </Typography>
          )}
          {filteredAlerts.map((alert) => (
            <Stack
              key={alert.id}
              direction="row"
              alignItems="center"
              justifyContent="space-between"
              sx={{ borderBottom: "1px solid #eef2f7", pb: 1 }}
            >
              <Typography variant="body2">
                [{alert.severity}] {alert.message}
              </Typography>
              <Chip
                label={alert.acknowledged ? "Ack" : "Acknowledge"}
                size="small"
                color={alert.acknowledged ? "default" : "primary"}
                onClick={() => !alert.acknowledged && ack(alert.id)}
              />
            </Stack>
          ))}
        </Stack>

        <Typography variant="subtitle2" sx={{ mb: 1 }}>
          Alert Preferences
        </Typography>
        <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="body2">In-app</Typography>
            <Switch
              checked={settings?.in_app ?? true}
              onChange={() => updateSettings({ in_app: !(settings?.in_app ?? true) })}
            />
          </Stack>
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="body2">Email</Typography>
            <Switch
              checked={settings?.email ?? false}
              onChange={() => updateSettings({ email: !(settings?.email ?? false) })}
            />
          </Stack>
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="body2">SMS</Typography>
            <Switch
              checked={settings?.sms ?? false}
              onChange={() => updateSettings({ sms: !(settings?.sms ?? false) })}
            />
          </Stack>
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="body2">Webhook</Typography>
            <Switch
              checked={settings?.webhook ?? false}
              onChange={() => updateSettings({ webhook: !(settings?.webhook ?? false) })}
            />
          </Stack>
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="body2">Sound</Typography>
            <Switch
              checked={settings?.sound_enabled ?? true}
              onChange={() => updateSettings({ sound_enabled: !(settings?.sound_enabled ?? true) })}
            />
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
};

export default NotificationCenter;
