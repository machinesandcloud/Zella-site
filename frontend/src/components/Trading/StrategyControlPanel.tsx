import { useEffect, useState } from "react";
import {
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  Stack,
  TextField,
  Typography
} from "@mui/material";
import {
  fetchStrategies,
  fetchStrategyConfig,
  fetchStrategyLogs,
  fetchStrategyPerformance,
  startStrategy,
  stopStrategy,
  updateStrategyConfig
} from "../../services/api";

type StrategyMeta = {
  id: string;
  status: "RUNNING" | "STOPPED";
  pnl?: number;
  win_rate?: number;
  trades?: number;
};

const StrategyControlPanel = () => {
  const [strategies, setStrategies] = useState<StrategyMeta[]>([]);
  const [selected, setSelected] = useState<StrategyMeta | null>(null);
  const [configStrategy, setConfigStrategy] = useState<string | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [configOpen, setConfigOpen] = useState(false);
  const [configJson, setConfigJson] = useState("{\n  \"parameters\": {},\n  \"risk\": {}\n}");

  const load = async () => {
    const data = await fetchStrategies();
    const available: string[] = data?.available || [];
    const active: string[] = data?.active || [];

    const mapped = await Promise.all(
      available.map(async (id) => {
        const perf = await fetchStrategyPerformance(id).catch(() => ({}));
        return {
          id,
          status: active.includes(id) ? "RUNNING" : "STOPPED",
          pnl: perf?.pnl ?? 0,
          win_rate: perf?.win_rate ?? 0,
          trades: perf?.trades ?? 0
        } as StrategyMeta;
      })
    );

    setStrategies(mapped);
  };

  useEffect(() => {
    load();
  }, []);

  const handleStart = async (strategyId: string) => {
    let payload = { parameters: {}, risk: {} } as Record<string, unknown>;
    try {
      payload = JSON.parse(configJson);
    } catch {
      payload = { parameters: {}, risk: {} };
    }
    await startStrategy(strategyId, payload);
    await load();
  };

  const handleStop = async (strategyId: string) => {
    await stopStrategy(strategyId);
    await load();
  };

  const openLogs = async (strategy: StrategyMeta) => {
    const data = await fetchStrategyLogs(strategy.id).catch(() => ({ logs: [] }));
    setSelected(strategy);
    setLogs(data?.logs || []);
  };

  const openConfig = async (strategyId: string) => {
    const data = await fetchStrategyConfig(strategyId).catch(() => ({ parameters: {}, risk: {} }));
    setConfigJson(JSON.stringify(data || { parameters: {}, risk: {} }, null, 2));
    setConfigStrategy(strategyId);
    setConfigOpen(true);
  };

  const saveConfig = async () => {
    if (!configStrategy) return;
    let payload = { parameters: {}, risk: {} } as Record<string, unknown>;
    try {
      payload = JSON.parse(configJson);
    } catch {
      payload = { parameters: {}, risk: {} };
    }
    await updateStrategyConfig(configStrategy, payload);
    setConfigOpen(false);
  };

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
          <Typography variant="h6">Strategy Control Panel</Typography>
          <Button size="small" variant="outlined" onClick={load}>
            Refresh
          </Button>
        </Stack>

        <Grid container spacing={2}>
          {strategies.map((strategy) => (
            <Grid item xs={12} md={6} key={strategy.id}>
              <Stack
                spacing={1}
                sx={{ border: "1px solid #eef2f7", borderRadius: 2, p: 2 }}
              >
                <Stack direction="row" justifyContent="space-between" alignItems="center">
                  <Typography variant="subtitle1">{strategy.id}</Typography>
                  <Chip
                    label={strategy.status}
                    size="small"
                    color={strategy.status === "RUNNING" ? "success" : "default"}
                  />
                </Stack>
                <Typography variant="body2" color="text.secondary">
                  Trades: {strategy.trades ?? 0} · Win rate: {strategy.win_rate ?? 0}% · PnL: {strategy.pnl ?? 0}
                </Typography>
                <Stack direction="row" spacing={1}>
                  <Button
                    size="small"
                    variant="contained"
                    onClick={() => handleStart(strategy.id)}
                    disabled={strategy.status === "RUNNING"}
                  >
                    Start
                  </Button>
                  <Button
                    size="small"
                    variant="outlined"
                    onClick={() => handleStop(strategy.id)}
                    disabled={strategy.status !== "RUNNING"}
                  >
                    Stop
                  </Button>
                  <Button size="small" onClick={() => openConfig(strategy.id)}>
                    Configure
                  </Button>
                  <Button size="small" onClick={() => openLogs(strategy)}>
                    Logs
                  </Button>
                </Stack>
              </Stack>
            </Grid>
          ))}
        </Grid>
      </CardContent>

      <Dialog open={configOpen} onClose={() => setConfigOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Strategy Configuration</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            multiline
            minRows={8}
            value={configJson}
            onChange={(e) => setConfigJson(e.target.value)}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfigOpen(false)}>Close</Button>
          <Button variant="contained" onClick={saveConfig}>
            Save
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(selected)} onClose={() => setSelected(null)} fullWidth maxWidth="sm">
        <DialogTitle>Strategy Logs {selected ? `- ${selected.id}` : ""}</DialogTitle>
        <DialogContent>
          <Stack spacing={1} sx={{ mt: 1 }}>
            {logs.length === 0 && (
              <Typography variant="body2" color="text.secondary">
                No logs yet.
              </Typography>
            )}
            {logs.map((log, idx) => (
              <Typography key={`${selected?.id}-${idx}`} variant="body2">
                {log}
              </Typography>
            ))}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelected(null)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Card>
  );
};

export default StrategyControlPanel;
