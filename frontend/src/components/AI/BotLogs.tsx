import { useEffect, useState, useRef } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Stack,
  IconButton,
  FormControlLabel,
  Switch
} from "@mui/material";
import { getAutonomousLogs, getAutonomousStatus } from "../../services/api";

type LogEntry = {
  type: string;
  message: string;
  category: string;
  details: Record<string, any>;
  timestamp?: string;
};

const getLogColor = (category: string): string => {
  switch (category) {
    case "SUCCESS": return "#4caf50";
    case "ERROR": return "#f44336";
    case "WARNING": return "#ff9800";
    case "INFO": return "#2196f3";
    default: return "#9e9e9e";
  }
};

const getLogIcon = (type: string): string => {
  switch (type) {
    case "TRADE": return "💰";
    case "SCAN": return "🔍";
    case "REJECTED": return "⛔";
    case "HALTED": return "🛑";
    case "CUTOFF": return "⏰";
    case "SCALE_OUT": return "📈";
    case "CLOSE_RUNNER": return "🏆";
    case "BREAKEVEN": return "🛡️";
    case "SYSTEM": return "⚙️";
    case "ERROR": return "❌";
    default: return "📋";
  }
};

const BotLogs = () => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [autoScroll, setAutoScroll] = useState(true);
  const [loading, setLoading] = useState(true);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const getLogTimestamp = (entry: LogEntry): number => {
    const raw = entry.timestamp || "";
    const parsed = new Date(raw).getTime();
    return Number.isFinite(parsed) ? parsed : 0;
  };

  const getLogKey = (entry: LogEntry): string => {
    const stamp = entry.timestamp || "";
    return `${stamp}-${entry.type}-${entry.message}`;
  };

  const mergeLogs = (existing: LogEntry[], incoming: LogEntry[]): LogEntry[] => {
    const map = new Map<string, LogEntry>();
    const upsert = (entry: LogEntry) => {
      const key = getLogKey(entry);
      const current = map.get(key);
      if (!current || getLogTimestamp(entry) >= getLogTimestamp(current)) {
        map.set(key, entry);
      }
    };
    existing.forEach(upsert);
    incoming.forEach(upsert);
    return Array.from(map.values()).sort(
      (a, b) => getLogTimestamp(b) - getLogTimestamp(a)
    );
  };

  const fetchLogs = async () => {
    try {
      const data = await getAutonomousLogs();
      const decisions = data.decisions || [];
      setLogs((prev) => mergeLogs(prev, decisions));
      localStorage.setItem("zella_bot_logs", JSON.stringify(decisions));
    } catch (error) {
      try {
        const fallback = await getAutonomousStatus();
        const decisions = fallback.decisions || [];
        setLogs((prev) => mergeLogs(prev, decisions));
        localStorage.setItem("zella_bot_logs", JSON.stringify(decisions));
      } catch (fallbackError) {
        console.warn("Failed to fetch bot logs:", fallbackError);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const cached = localStorage.getItem("zella_bot_logs");
    if (cached) {
      try {
        const parsed = JSON.parse(cached);
        if (Array.isArray(parsed)) {
          setLogs((prev) => mergeLogs(prev, parsed));
        }
        setLoading(false);
      } catch {
        // ignore cache parse errors
      }
    }
    fetchLogs();
    const interval = setInterval(fetchLogs, 5000); // Refresh every 5s
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, autoScroll]);

  const formatTime = (timestamp?: string): string => {
    if (!timestamp) return "--";
    try {
      const time = new Date(timestamp).toLocaleTimeString("en-US", {
        timeZone: "America/Chicago",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit"
      });
      return `${time} CT`;
    } catch {
      return "--";
    }
  };

  return (
    <Card elevation={0} sx={{ border: "1px solid rgba(255,255,255,0.1)", borderRadius: 3 }}>
      <CardContent sx={{ p: 3 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Bot Activity Logs
          </Typography>
          <Stack direction="row" spacing={2} alignItems="center">
            <Chip label={`${logs.length} entries`} size="small" />
            <FormControlLabel
              control={
                <Switch
                  checked={autoScroll}
                  onChange={(e) => setAutoScroll(e.target.checked)}
                  size="small"
                />
              }
              label={<Typography variant="caption">Auto-scroll</Typography>}
            />
            <IconButton size="small" onClick={fetchLogs} title="Refresh">
              🔄
            </IconButton>
          </Stack>
        </Stack>

        <Box
          sx={{
            maxHeight: 500,
            overflowY: "auto",
            border: "1px solid rgba(255,255,255,0.05)",
            borderRadius: 2,
            background: "rgba(0,0,0,0.2)",
            p: 1
          }}
        >
          {loading ? (
            <Box sx={{ p: 4, textAlign: "center" }}>
              <Typography color="text.secondary">Loading logs...</Typography>
            </Box>
          ) : logs.length === 0 ? (
            <Box sx={{ p: 4, textAlign: "center" }}>
              <Typography color="text.secondary">No activity yet</Typography>
              <Typography variant="caption" color="text.secondary">
                Logs will appear when the bot starts scanning
              </Typography>
            </Box>
          ) : (
            logs.map((log, idx) => (
              <Box
                key={idx}
                sx={{
                  p: 1.5,
                  mb: 1,
                  borderRadius: 1,
                  background: "rgba(255,255,255,0.02)",
                  borderLeft: `3px solid ${getLogColor(log.category)}`,
                  "&:hover": {
                    background: "rgba(255,255,255,0.05)"
                  }
                }}
              >
                <Stack direction="row" spacing={1} alignItems="flex-start">
                  <Typography sx={{ fontSize: "1.1rem" }}>{getLogIcon(log.type)}</Typography>
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                      <Chip
                        label={log.type}
                        size="small"
                        sx={{
                          height: 20,
                          fontSize: "0.65rem",
                          background: getLogColor(log.category),
                          color: "#fff"
                        }}
                      />
                      <Typography variant="caption" color="text.secondary">
                        {formatTime(log.timestamp)}
                      </Typography>
                    </Stack>
                    <Typography variant="body2" sx={{ mt: 0.5, wordBreak: "break-word" }}>
                      {log.message}
                    </Typography>
                    {log.details && Object.keys(log.details).length > 0 && (
                      <Box sx={{ mt: 1, p: 1, borderRadius: 1, background: "rgba(0,0,0,0.2)" }}>
                        <Typography
                          variant="caption"
                          component="pre"
                          sx={{
                            fontFamily: "monospace",
                            fontSize: "0.7rem",
                            color: "text.secondary",
                            whiteSpace: "pre-wrap",
                            margin: 0
                          }}
                        >
                          {JSON.stringify(log.details, null, 2)}
                        </Typography>
                      </Box>
                    )}
                  </Box>
                </Stack>
              </Box>
            ))
          )}
          <div ref={logsEndRef} />
        </Box>
      </CardContent>
    </Card>
  );
};

export default BotLogs;
