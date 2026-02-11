import { useEffect, useState } from "react";
import {
  Button,
  Card,
  CardContent,
  FormControlLabel,
  Stack,
  Switch,
  Typography
} from "@mui/material";
import api from "../../services/api";

const StrategyConfig = () => {
  const [strategies, setStrategies] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get("/api/strategies")
      .then((res) => {
        const available = res.data.available || [];
        const active = new Set(res.data.active || []);
        const next: Record<string, boolean> = {};
        available.forEach((name: string) => {
          next[name] = active.has(name);
        });
        setStrategies(next);
      })
      .catch(() => {
        setStrategies({
          ema_cross: true,
          vwap_bounce: true,
          rsi_exhaustion: true,
          orb_strategy: false
        });
      })
      .finally(() => setLoading(false));
  }, []);

  const toggle = (key: string) => {
    setStrategies((prev) => ({ ...prev, [key]: !prev[key as keyof typeof prev] }));
  };

  const save = async () => {
    const entries = Object.entries(strategies);
    await Promise.all(
      entries.map(([key, enabled]) =>
        enabled
          ? api.post(`/api/strategies/${key}/start`, { parameters: {}, risk: {} })
          : api.post(`/api/strategies/${key}/stop`)
      )
    );
  };

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Strategy Configuration
        </Typography>
        <Stack spacing={1}>
          {loading && <Typography color="text.secondary">Loading strategies...</Typography>}
          {!loading &&
            Object.entries(strategies).map(([key, enabled]) => (
            <FormControlLabel
              key={key}
              control={<Switch checked={enabled} onChange={() => toggle(key)} />}
              label={key}
            />
          ))}
        </Stack>
        <Button variant="contained" sx={{ mt: 2 }} onClick={save}>
          Save Configuration
        </Button>
      </CardContent>
    </Card>
  );
};

export default StrategyConfig;
