import { useEffect, useState } from "react";
import {
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  Grid,
  Stack,
  Switch,
  FormControlLabel,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
  Box,
  LinearProgress,
  Alert,
  List,
  ListItem,
  ListItemText,
  IconButton,
  Collapse
} from "@mui/material";
import {
  Stop,
  Warning,
  CheckCircle,
  Psychology,
  Settings as SettingsIcon,
  ExpandMore,
  ExpandLess,
  Refresh
} from "@mui/icons-material";
import {
  startAutonomousEngine,
  stopAutonomousEngine,
  getAutonomousStatus,
  updateAutonomousConfig,
  getStrategyPerformance
} from "../../services/api";

type Mode = "ASSISTED" | "SEMI_AUTO" | "FULL_AUTO" | "GOD_MODE";
type RiskPosture = "DEFENSIVE" | "BALANCED" | "AGGRESSIVE";

interface AutonomousStatus {
  enabled: boolean;
  running: boolean;
  mode: Mode;
  risk_posture: RiskPosture;
  last_scan: string | null;
  active_positions: number;
  decisions: Decision[];
  strategy_performance: Record<string, { signals: number; trades: number }>;
  num_strategies: number;
  connected: boolean;
}

interface Decision {
  id: string;
  time: string;
  type: string;
  action: string;
  status: string;
  metadata?: any;
}

interface StrategyPerformance {
  strategies: string[];
  performance: Record<string, { signals: number; trades: number }>;
  total_strategies: number;
}

const AutopilotControl = () => {
  const [status, setStatus] = useState<AutonomousStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [strategyPerf, setStrategyPerf] = useState<StrategyPerformance | null>(null);
  const [expandedStrategies, setExpandedStrategies] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const loadStatus = async () => {
    setRefreshing(true);
    try {
      const data = await getAutonomousStatus();
      setStatus(data);
    } catch (error: any) {
      console.error("Error loading autonomous status:", error);
      // Set demo/offline status instead of failing
      if (error?.response?.status === 503 || error?.code === "ERR_NETWORK") {
        setStatus({
          enabled: false,
          running: false,
          mode: "FULL_AUTO",
          risk_posture: "BALANCED",
          last_scan: null,
          active_positions: 0,
          decisions: [],
          strategy_performance: {},
          num_strategies: 0,
          connected: false
        });
      } else {
        notify("Backend offline - showing demo mode", "warning");
      }
    } finally {
      setRefreshing(false);
      setLoading(false);
    }
  };

  const loadStrategyPerformance = async () => {
    try {
      const data = await getStrategyPerformance();
      setStrategyPerf(data);
    } catch (error) {
      console.error("Error loading strategy performance:", error);
    }
  };

  useEffect(() => {
    loadStatus();
    loadStrategyPerformance();

    // Auto-refresh every 5 seconds
    const interval = setInterval(() => {
      loadStatus();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const handleToggleEngine = async () => {
    if (!status) return;

    try {
      if (status.enabled && status.running) {
        await stopAutonomousEngine();
        notify("Autonomous engine stopped", "info");
      } else {
        await startAutonomousEngine();
        notify("Autonomous engine started", "success");
      }
      await loadStatus();
    } catch (error: any) {
      notify(error.message || "Failed to toggle engine", "error");
    }
  };

  const handleModeChange = async (newMode: Mode) => {
    if (!status) return;

    try {
      await updateAutonomousConfig({ mode: newMode });
      notify(`Mode changed to ${newMode}`, "success");
      await loadStatus();
    } catch (error) {
      notify("Failed to update mode", "error");
    }
  };

  const handleRiskChange = async (newRisk: RiskPosture) => {
    if (!status) return;

    try {
      await updateAutonomousConfig({ risk_posture: newRisk });
      notify(`Risk posture changed to ${newRisk}`, "success");
      await loadStatus();
    } catch (error) {
      notify("Failed to update risk posture", "error");
    }
  };

  const handleEmergencyStop = async () => {
    const confirmed = window.confirm(
      "⚠️ EMERGENCY STOP\n\nThis will immediately:\n• Stop all trading\n• Close autonomous engine\n• Halt all pending orders\n\nContinue?"
    );
    if (!confirmed) return;

    try {
      await stopAutonomousEngine();
      notify("🛑 EMERGENCY STOP ACTIVATED", "error");
      await loadStatus();
    } catch (error) {
      notify("Failed to execute emergency stop", "error");
    }
  };

  const notify = (message: string, severity: "success" | "info" | "warning" | "error" = "info") => {
    window.dispatchEvent(new CustomEvent("app:toast", { detail: { message, severity } }));
  };

  if (loading) {
    return (
      <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
        <CardContent>
          <Box sx={{ textAlign: "center", py: 4 }}>
            <LinearProgress />
            <Typography sx={{ mt: 2 }}>Loading Autonomous Engine...</Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  if (!status) {
    return (
      <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
        <CardContent>
          <Alert severity="info">
            Backend not connected. Start the backend server to enable autonomous trading features.
          </Alert>
        </CardContent>
      </Card>
    );
  }

  const isRunning = status.enabled && status.running;
  const connectionStatus = status.connected ? "connected" : "disconnected";

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>

        {/* Header */}
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
          <Stack spacing={0.5}>
            <Stack direction="row" alignItems="center" spacing={1}>
              <Psychology sx={{ fontSize: 32, color: isRunning ? "success.main" : "text.secondary" }} />
              <Typography variant="h5" fontWeight="bold">
                Autonomous Trading Engine
              </Typography>
              <IconButton size="small" onClick={() => loadStatus()} disabled={refreshing}>
                <Refresh className={refreshing ? "rotating" : ""} />
              </IconButton>
            </Stack>
            <Typography variant="body2" color="text.secondary">
              AI-powered fully autonomous trading using {status.num_strategies}+ strategies
            </Typography>
          </Stack>

          <Stack direction="row" spacing={1} alignItems="center">
            <Chip
              icon={status.connected ? <CheckCircle /> : <Warning />}
              label={connectionStatus.toUpperCase()}
              color={status.connected ? "success" : "error"}
              size="small"
            />
            <Chip
              label={isRunning ? "RUNNING" : "STOPPED"}
              color={isRunning ? "success" : "default"}
              size="small"
            />
          </Stack>
        </Stack>

        {/* Connection Warning */}
        {!status.connected && (
          <Alert severity="warning" sx={{ mb: 3 }}>
            Not connected to broker. Autonomous trading requires an active broker connection.
          </Alert>
        )}

        {/* Main Controls */}
        <Box sx={{
          p: 3,
          mb: 3,
          borderRadius: 2,
          background: isRunning
            ? "linear-gradient(135deg, rgba(46, 125, 50, 0.1) 0%, rgba(27, 94, 32, 0.05) 100%)"
            : "rgba(255, 255, 255, 0.02)",
          border: isRunning ? "2px solid" : "1px solid",
          borderColor: isRunning ? "success.main" : "divider"
        }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Stack spacing={1}>
              <Typography variant="h6">
                {isRunning ? "🤖 Autonomous Mode Active" : "⏸️ Autonomous Mode Paused"}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {isRunning
                  ? "AI is actively scanning markets and executing trades"
                  : "Toggle the switch to enable autonomous trading"}
              </Typography>
            </Stack>

            <FormControlLabel
              control={
                <Switch
                  checked={isRunning}
                  onChange={handleToggleEngine}
                  disabled={!status.connected}
                  size="medium"
                  color="success"
                />
              }
              label={isRunning ? "ENABLED" : "DISABLED"}
              labelPlacement="start"
              sx={{ m: 0 }}
            />
          </Stack>
        </Box>

        {/* Metrics */}
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={6} md={3}>
            <Box sx={{ p: 2, borderRadius: 2, bgcolor: "rgba(255, 255, 255, 0.02)" }}>
              <Typography variant="overline" color="text.secondary">Active Positions</Typography>
              <Typography variant="h5" fontWeight="bold">{status.active_positions}</Typography>
            </Box>
          </Grid>
          <Grid item xs={6} md={3}>
            <Box sx={{ p: 2, borderRadius: 2, bgcolor: "rgba(255, 255, 255, 0.02)" }}>
              <Typography variant="overline" color="text.secondary">Strategies Active</Typography>
              <Typography variant="h5" fontWeight="bold">{status.num_strategies}</Typography>
            </Box>
          </Grid>
          <Grid item xs={6} md={3}>
            <Box sx={{ p: 2, borderRadius: 2, bgcolor: "rgba(255, 255, 255, 0.02)" }}>
              <Typography variant="overline" color="text.secondary">Recent Decisions</Typography>
              <Typography variant="h5" fontWeight="bold">{status.decisions.length}</Typography>
            </Box>
          </Grid>
          <Grid item xs={6} md={3}>
            <Box sx={{ p: 2, borderRadius: 2, bgcolor: "rgba(255, 255, 255, 0.02)" }}>
              <Typography variant="overline" color="text.secondary">Last Scan</Typography>
              <Typography variant="body2" fontWeight="bold">
                {status.last_scan ? new Date(status.last_scan).toLocaleTimeString() : "Never"}
              </Typography>
            </Box>
          </Grid>
        </Grid>

        {/* Mode Selection */}
        <Stack spacing={2} sx={{ mb: 3 }}>
          <Typography variant="subtitle2" fontWeight="bold">Trading Mode</Typography>
          <ToggleButtonGroup
            value={status.mode}
            exclusive
            onChange={(_, value) => value && handleModeChange(value)}
            fullWidth
            size="small"
          >
            <ToggleButton value="ASSISTED">
              <Stack alignItems="center">
                <Typography variant="caption" fontWeight="bold">Assisted</Typography>
                <Typography variant="caption" fontSize="0.65rem">Manual approval</Typography>
              </Stack>
            </ToggleButton>
            <ToggleButton value="SEMI_AUTO">
              <Stack alignItems="center">
                <Typography variant="caption" fontWeight="bold">Semi-Auto</Typography>
                <Typography variant="caption" fontSize="0.65rem">Some automation</Typography>
              </Stack>
            </ToggleButton>
            <ToggleButton value="FULL_AUTO">
              <Stack alignItems="center">
                <Typography variant="caption" fontWeight="bold">Full Auto</Typography>
                <Typography variant="caption" fontSize="0.65rem">Fully autonomous</Typography>
              </Stack>
            </ToggleButton>
            <ToggleButton value="GOD_MODE">
              <Stack alignItems="center">
                <Typography variant="caption" fontWeight="bold">God Mode</Typography>
                <Typography variant="caption" fontSize="0.65rem">Maximum aggression</Typography>
              </Stack>
            </ToggleButton>
          </ToggleButtonGroup>
        </Stack>

        {/* Risk Posture */}
        <Stack spacing={2} sx={{ mb: 3 }}>
          <Typography variant="subtitle2" fontWeight="bold">Risk Posture</Typography>
          <ToggleButtonGroup
            value={status.risk_posture}
            exclusive
            onChange={(_, value) => value && handleRiskChange(value)}
            fullWidth
            size="small"
          >
            <ToggleButton value="DEFENSIVE">
              <Stack alignItems="center">
                <Typography variant="caption" fontWeight="bold">Defensive</Typography>
                <Typography variant="caption" fontSize="0.65rem">Min risk, 3% profit</Typography>
              </Stack>
            </ToggleButton>
            <ToggleButton value="BALANCED">
              <Stack alignItems="center">
                <Typography variant="caption" fontWeight="bold">Balanced</Typography>
                <Typography variant="caption" fontSize="0.65rem">Moderate risk, 5% profit</Typography>
              </Stack>
            </ToggleButton>
            <ToggleButton value="AGGRESSIVE">
              <Stack alignItems="center">
                <Typography variant="caption" fontWeight="bold">Aggressive</Typography>
                <Typography variant="caption" fontSize="0.65rem">Max risk, 8% profit</Typography>
              </Stack>
            </ToggleButton>
          </ToggleButtonGroup>
        </Stack>

        {/* Strategy Performance */}
        {strategyPerf && (
          <Box sx={{ mb: 3 }}>
            <Stack
              direction="row"
              justifyContent="space-between"
              alignItems="center"
              onClick={() => setExpandedStrategies(!expandedStrategies)}
              sx={{ cursor: "pointer", mb: 1 }}
            >
              <Typography variant="subtitle2" fontWeight="bold">
                Strategy Performance ({strategyPerf.total_strategies} strategies)
              </Typography>
              {expandedStrategies ? <ExpandLess /> : <ExpandMore />}
            </Stack>

            <Collapse in={expandedStrategies}>
              <Box sx={{
                maxHeight: 200,
                overflow: "auto",
                p: 2,
                borderRadius: 2,
                bgcolor: "rgba(255, 255, 255, 0.02)"
              }}>
                <List dense>
                  {Object.entries(strategyPerf.performance).map(([name, perf]) => (
                    <ListItem key={name}>
                      <ListItemText
                        primary={name.replace(/_/g, " ").toUpperCase()}
                        secondary={`${perf.signals} signals, ${perf.trades} trades`}
                      />
                    </ListItem>
                  ))}
                  {Object.keys(strategyPerf.performance).length === 0 && (
                    <Typography variant="caption" color="text.secondary" sx={{ p: 2 }}>
                      No strategy activity yet. Start the engine to begin trading.
                    </Typography>
                  )}
                </List>
              </Box>
            </Collapse>
          </Box>
        )}

        <Divider sx={{ mb: 3 }} />

        {/* Decision Log */}
        <Typography variant="subtitle2" fontWeight="bold" sx={{ mb: 2 }}>
          Live Decision Log
        </Typography>

        {status.decisions.length > 0 ? (
          <Stack spacing={2} sx={{ maxHeight: 300, overflow: "auto" }}>
            {status.decisions.map((decision) => (
              <Box
                key={decision.id}
                sx={{
                  p: 2,
                  borderRadius: 2,
                  border: "1px solid rgba(255,255,255,0.06)",
                  background: "rgba(12, 16, 26, 0.7)"
                }}
              >
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    {decision.time} · {decision.type}
                  </Typography>
                  <Chip
                    label={decision.status}
                    size="small"
                    color={
                      decision.status === "SUCCESS" ? "success" :
                      decision.status === "ERROR" ? "error" :
                      "default"
                    }
                  />
                </Stack>
                <Typography variant="body1" fontWeight="medium">
                  {decision.action}
                </Typography>
                {decision.metadata && decision.metadata.strategies && (
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
                    Strategies: {decision.metadata.strategies.join(", ")}
                  </Typography>
                )}
              </Box>
            ))}
          </Stack>
        ) : (
          <Alert severity="info">
            No decisions yet. The engine will log all trading decisions here in real-time.
          </Alert>
        )}

        <Divider sx={{ my: 3 }} />

        {/* Action Buttons */}
        <Stack direction="row" spacing={2}>
          <Button
            variant="outlined"
            startIcon={<SettingsIcon />}
            onClick={() => {
              window.dispatchEvent(new CustomEvent("app:navigate", { detail: { tab: 3 } }));
              notify("Opening AI configuration in Settings.", "info");
            }}
            fullWidth
          >
            Advanced Settings
          </Button>
          <Button
            variant="contained"
            color="error"
            startIcon={<Stop />}
            onClick={handleEmergencyStop}
            fullWidth
            disabled={!isRunning}
          >
            Emergency Stop
          </Button>
        </Stack>

      </CardContent>
    </Card>
  );
};

export default AutopilotControl;
