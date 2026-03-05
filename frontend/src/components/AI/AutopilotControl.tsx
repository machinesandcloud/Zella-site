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
  Collapse,
  Tooltip
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
  getAutonomousLogs,
  updateAutonomousConfig,
  getStrategyPerformance,
  liquidateAllPositions
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
  market_session?: {
    session?: string;
    regular?: boolean;
    premarket?: boolean;
    afterhours?: boolean;
    clock_source?: string;
  };
  hotlist?: {
    symbols?: string[];
    count?: number;
    generated_at?: string | null;
  };
}

interface Decision {
  id: string;
  time: string;
  timestamp?: string;
  type: string;
  action: string;
  status: string;
  category?: string;
  message?: string;
  details?: Record<string, any>;
  metadata?: any;
}

interface StrategyPerformance {
  strategies: string[];
  performance: Record<string, { signals: number; trades: number }>;
  total_strategies: number;
}

const AutopilotControl = () => {
  const [status, setStatus] = useState<AutonomousStatus | null>(null);
  const [decisionLogs, setDecisionLogs] = useState<Decision[]>([]);
  const [loading, setLoading] = useState(true);
  const [strategyPerf, setStrategyPerf] = useState<StrategyPerformance | null>(null);
  const [expandedStrategies, setExpandedStrategies] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [showHotlist, setShowHotlist] = useState(false);
  const STATUS_CACHE_KEY = "zella_autonomous_status";

  const getDecisionTimestamp = (decision: Decision): number => {
    const raw = decision.timestamp || decision.time || "";
    const parsed = new Date(raw).getTime();
    return Number.isFinite(parsed) ? parsed : 0;
  };

  const getDecisionKey = (decision: Decision): string => {
    if (decision.id) return decision.id;
    const stamp = decision.timestamp || decision.time || "";
    const message = decision.message || decision.action || "";
    return `${stamp}-${decision.type}-${message}`;
  };

  const mergeDecisions = (existing: Decision[], incoming: Decision[]): Decision[] => {
    const map = new Map<string, Decision>();
    const upsert = (decision: Decision) => {
      const key = getDecisionKey(decision);
      const current = map.get(key);
      if (!current || getDecisionTimestamp(decision) >= getDecisionTimestamp(current)) {
        map.set(key, decision);
      }
    };
    existing.forEach(upsert);
    incoming.forEach(upsert);
    return Array.from(map.values()).sort(
      (a, b) => getDecisionTimestamp(b) - getDecisionTimestamp(a)
    );
  };

  const loadStatus = async () => {
    setRefreshing(true);
    try {
      const data = await getAutonomousStatus();
      setStatus(data);
      localStorage.setItem(STATUS_CACHE_KEY, JSON.stringify(data));
    } catch (error: any) {
      console.error("Error loading autonomous status:", error);
      const cached = localStorage.getItem(STATUS_CACHE_KEY);
      if (cached) {
        try {
          setStatus(JSON.parse(cached));
        } catch {
          setStatus(null);
        }
      } else {
        // Set demo status on ANY error - don't show annoying notifications repeatedly
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

  const loadDecisionLogs = async () => {
    try {
      const data = await getAutonomousLogs();
      setDecisionLogs((prev) => mergeDecisions(prev, data.decisions || []));
    } catch (error) {
      const cached = localStorage.getItem(STATUS_CACHE_KEY);
      if (cached) {
        try {
          const parsed = JSON.parse(cached);
          if (parsed?.decisions?.length) {
            setDecisionLogs((prev) => mergeDecisions(prev, parsed.decisions));
          }
        } catch {
          // ignore cache parse errors
        }
      }
    }
  };

  useEffect(() => {
    const cached = localStorage.getItem(STATUS_CACHE_KEY);
    if (cached) {
      try {
        setStatus(JSON.parse(cached));
        setLoading(false);
      } catch {
        // ignore cache parse errors
      }
    }

    loadStatus();
    loadStrategyPerformance();
    loadDecisionLogs();

    // Auto-refresh every 5 seconds
    const interval = setInterval(() => {
      loadStatus();
      loadDecisionLogs();
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

  const handleForceCloseAll = async () => {
    const confirmed = window.confirm(
      "🚨 FORCE CLOSE ALL POSITIONS\n\nThis will immediately:\n• Cancel ALL pending orders\n• Sell ALL open positions at market price\n• Day trading rule: NO overnight holds!\n\nContinue?"
    );
    if (!confirmed) return;

    try {
      notify("🔄 Closing all positions...", "warning");
      const result = await liquidateAllPositions();
      notify(`✅ Closed ${result.positions_closed} positions`, "success");
      await loadStatus();
    } catch (error: any) {
      notify(error.message || "Failed to close positions", "error");
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
  const sessionLabel = status.market_session?.session || "UNKNOWN";
  const sessionSource = status.market_session?.clock_source || "local";
  const hotlistCount = status.hotlist?.count ?? 0;
  const hotlistSymbols = status.hotlist?.symbols?.slice(0, 5) || [];
  const hotlistTooltip = hotlistSymbols.length ? hotlistSymbols.join(", ") : "No hotlist yet";
  const sessionColor =
    sessionLabel === "REGULAR"
      ? "success"
      : sessionLabel === "PREMARKET" || sessionLabel === "AFTERHOURS"
        ? "warning"
        : "default";

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
            <Chip
              label={`SESSION: ${sessionLabel}`}
              color={sessionColor}
              size="small"
            />
            <Chip
              label={`Clock: ${sessionSource.toUpperCase()}`}
              size="small"
              variant="outlined"
            />
            <Tooltip title={hotlistTooltip} arrow>
              <Chip
                label={`Hotlist: ${hotlistCount}`}
                size="small"
                variant="outlined"
              />
            </Tooltip>
            <IconButton
              size="small"
              onClick={() => setShowHotlist((prev) => !prev)}
              disabled={hotlistSymbols.length === 0}
            >
              <ExpandMore
                sx={{
                  transform: showHotlist ? "rotate(180deg)" : "rotate(0deg)",
                  transition: "transform 0.2s ease",
                }}
              />
            </IconButton>
          </Stack>
        </Stack>

        <Collapse in={showHotlist} timeout="auto" unmountOnExit>
          <Stack direction="row" spacing={1} sx={{ mb: 2, flexWrap: "wrap" }}>
            {hotlistSymbols.map((symbol) => (
              <Chip key={symbol} label={symbol} size="small" color="info" variant="outlined" />
            ))}
          </Stack>
        </Collapse>

        {/* Connection Warning */}
        {!status.connected && (
          <Alert severity="warning" sx={{ mb: 3 }}>
            Not connected to broker. You can still run scan-only mode, but trades won’t execute until the broker reconnects.
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
                  disabled={!status}
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

        {decisionLogs.length > 0 ? (
          <Stack spacing={2} sx={{ maxHeight: 300, overflow: "auto" }}>
            {decisionLogs.map((decision) => (
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
                    {decision.timestamp ? `${new Date(decision.timestamp).toLocaleTimeString("en-US", { timeZone: "America/Chicago", hour: "2-digit", minute: "2-digit", second: "2-digit" })} CT` : "--"} · {decision.type}
                  </Typography>
                  <Chip
                    label={decision.category || decision.status || "INFO"}
                    size="small"
                    color={
                      (decision.category || decision.status) === "SUCCESS" ? "success" :
                      (decision.category || decision.status) === "ERROR" ? "error" :
                      (decision.category || decision.status) === "WARNING" ? "warning" :
                      "default"
                    }
                  />
                </Stack>
                <Typography variant="body1" fontWeight="medium">
                  {decision.message || decision.action || "No message"}
                </Typography>
                {(decision.details || decision.metadata)?.strategies && (
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
                    Strategies: {Array.isArray((decision.details || decision.metadata).strategies)
                      ? (decision.details || decision.metadata).strategies.join(", ")
                      : String((decision.details || decision.metadata).strategies)}
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
          >
            Settings
          </Button>
          <Button
            variant="contained"
            color="warning"
            onClick={handleForceCloseAll}
            disabled={!status?.connected}
          >
            Close All Positions
          </Button>
          <Button
            variant="contained"
            color="error"
            startIcon={<Stop />}
            onClick={handleEmergencyStop}
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
