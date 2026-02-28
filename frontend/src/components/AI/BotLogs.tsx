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

const API_URL = import.meta.env.VITE_API_URL?.trim() || "http://localhost:8000";

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

  const fetchLogs = async () => {
    try {
      const token = localStorage.getItem("zella_token");
      const response = await fetch(`${API_URL}/api/ai-trading/autonomous/status`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        }
      });

      if (response.ok) {
        const data = await response.json();
        // decisions is an array of {type, message, category, details, timestamp}
        const decisions = data.decisions || [];
        setLogs(decisions.reverse()); // Show newest first
      }
    } catch (error) {
      console.warn("Failed to fetch bot logs:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
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
      return new Date(timestamp).toLocaleTimeString();
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
