import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  Chip,
  Stack,
  Typography,
  Box,
  Avatar,
  IconButton,
  Tooltip
} from "@mui/material";
import {
  TrendingUp,
  TrendingDown,
  Radar,
  Psychology,
  Error as ErrorIcon,
  Info,
  CheckCircle,
  Refresh
} from "@mui/icons-material";
import { fetchAiActivity, getAutonomousStatus } from "../../services/api";

type ActivityEvent = {
  event_type: string;
  message: string;
  level: string;
  details?: Record<string, any>;
  timestamp: string;
};

interface Decision {
  id: string;
  time: string;
  type: string;
  action: string;
  status: string;
  metadata?: any;
}

const AutonomyTimeline = () => {
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    setRefreshing(true);
    try {
      // Load both AI activity and autonomous decisions
      const [activityData, statusData] = await Promise.all([
        fetchAiActivity().catch(() => ({ events: [] })),
        getAutonomousStatus().catch(() => ({ decisions: [] }))
      ]);

      setEvents(activityData?.events || []);
      setDecisions(statusData?.decisions || []);
    } catch (error) {
      console.error("Error loading timeline:", error);
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const getEventIcon = (type: string, status?: string) => {
    switch (type) {
      case "SCAN":
        return <Radar />;
      case "TRADE":
        return status === "SUCCESS" ? <TrendingUp /> : <TrendingDown />;
      case "CLOSE":
        return <CheckCircle />;
      case "SYSTEM":
        return <Psychology />;
      case "ERROR":
        return <ErrorIcon />;
      default:
        return <Info />;
    }
  };

  const getEventColor = (type: string, status?: string): "success" | "info" | "warning" | "error" | "primary" | "secondary" | "default" => {
    if (status === "ERROR") return "error";
    switch (type) {
      case "SCAN":
        return "info";
      case "TRADE":
        return status === "SUCCESS" ? "success" : "warning";
      case "CLOSE":
        return "primary";
      case "SYSTEM":
        return "secondary";
      case "ERROR":
        return "error";
      default:
        return "default";
    }
  };

  // Combine decisions and events, sort by time
  const allItems = [
    ...decisions.map(d => ({ ...d, source: "decision" as const })),
    ...events.map(e => ({ ...e, source: "event" as const }))
  ].sort((a, b) => {
    const timeA = "time" in a ? a.time : new Date(a.timestamp).toLocaleTimeString();
    const timeB = "time" in b ? b.time : new Date(b.timestamp).toLocaleTimeString();
    return timeB.localeCompare(timeA);
  }).slice(0, 15); // Show last 15 items

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
          <Box>
            <Typography variant="h6" fontWeight="bold">
              Autonomy Timeline
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Real-time decision log and AI activity
            </Typography>
          </Box>
          <Stack direction="row" spacing={1} alignItems="center">
            <Chip
              label={`${allItems.length} events`}
              size="small"
              color="primary"
            />
            <Tooltip title="Refresh">
              <IconButton size="small" onClick={load} disabled={refreshing}>
                <Refresh className={refreshing ? "rotating" : ""} />
              </IconButton>
            </Tooltip>
          </Stack>
        </Stack>

        {allItems.length === 0 ? (
          <Box
            sx={{
              p: 4,
              textAlign: "center",
              borderRadius: 2,
              bgcolor: "rgba(255,255,255,0.02)",
              border: "1px dashed rgba(255,255,255,0.1)"
            }}
          >
            <Psychology sx={{ fontSize: 48, color: "text.secondary", mb: 1 }} />
            <Typography variant="body2" color="text.secondary">
              No AI activity logged yet. Start the autonomous engine to see real-time decisions.
            </Typography>
          </Box>
        ) : (
          <Stack spacing={2} sx={{ maxHeight: 500, overflow: "auto" }}>
            {allItems.map((item, index) => {
              const isDecision = item.source === "decision";
              const type = isDecision ? item.type : item.event_type;
              const message = isDecision ? item.action : item.message;
              const status = isDecision ? item.status : item.level;
              const time = isDecision ? item.time : new Date(item.timestamp).toLocaleTimeString();
              const details = isDecision ? item.metadata : item.details;
              const eventColor = getEventColor(type, status);

              return (
                <Box
                  key={isDecision ? item.id : `${item.timestamp}-${index}`}
                  sx={{
                    p: 2,
                    borderRadius: 2,
                    bgcolor: "rgba(255,255,255,0.02)",
                    border: "1px solid rgba(255,255,255,0.06)",
                    borderLeft: `4px solid`,
                    borderLeftColor: `${eventColor}.main`,
                    position: "relative"
                  }}
                >
                  <Stack direction="row" spacing={2} alignItems="flex-start">
                    <Avatar
                      sx={{
                        width: 36,
                        height: 36,
                        bgcolor: `${eventColor}.main`,
                        boxShadow: index === 0 ? "0 0 12px currentColor" : "none",
                        animation: index === 0 ? "pulse 2s ease-in-out infinite" : "none"
                      }}
                    >
                      {getEventIcon(type, status)}
                    </Avatar>
                    <Box sx={{ flex: 1 }}>
                      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                        <Chip
                          label={type}
                          size="small"
                          color={eventColor}
                          sx={{ height: 20, fontSize: "0.65rem" }}
                        />
                        <Chip
                          label={status}
                          size="small"
                          color={
                            status === "SUCCESS" ? "success" :
                            status === "ERROR" ? "error" :
                            "default"
                          }
                          sx={{ height: 20, fontSize: "0.65rem" }}
                        />
                        <Typography variant="caption" color="text.secondary" sx={{ ml: "auto" }}>
                          {time}
                        </Typography>
                      </Stack>
                      <Typography variant="body2" fontWeight="medium" sx={{ mb: 1 }}>
                        {message}
                      </Typography>
                      {details && Object.keys(details).length > 0 && (
                        <Box>
                          {details.strategies && (
                            <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                              Strategies: {Array.isArray(details.strategies) ? details.strategies.join(", ") : details.strategies}
                            </Typography>
                          )}
                          {details.confidence !== undefined && (
                            <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                              Confidence: {(details.confidence * 100).toFixed(0)}%
                            </Typography>
                          )}
                          {details.order_id && (
                            <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                              Order ID: {details.order_id}
                            </Typography>
                          )}
                          {details.count !== undefined && (
                            <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                              Count: {details.count}
                            </Typography>
                          )}
                        </Box>
                      )}
                    </Box>
                  </Stack>
                </Box>
              );
            })}
          </Stack>
        )}
      </CardContent>
    </Card>
  );
};

export default AutonomyTimeline;
