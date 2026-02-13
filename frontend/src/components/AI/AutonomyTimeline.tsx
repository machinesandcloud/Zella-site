import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  Chip,
  Divider,
  Stack,
  Typography
} from "@mui/material";
import { fetchAiActivity } from "../../services/api";

type ActivityEvent = {
  event_type: string;
  message: string;
  level: string;
  details?: Record<string, string>;
  timestamp: string;
};

const AutonomyTimeline = () => {
  const [events, setEvents] = useState<ActivityEvent[]>([]);

  const load = () => {
    fetchAiActivity()
      .then((data) => setEvents(data?.events || []))
      .catch(() => setEvents([]));
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 7000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
          <Typography variant="h6">Autonomy Timeline</Typography>
          <Chip label={`${events.length} events`} size="small" />
        </Stack>
        <Stack spacing={2}>
          {events.length === 0 && (
            <Typography variant="body2" color="text.secondary">
              No AI activity logged yet.
            </Typography>
          )}
          {events.map((event, index) => (
            <Stack key={`${event.timestamp}-${index}`} spacing={1}>
              <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between">
                <Stack direction="row" spacing={1} alignItems="center">
                  <Chip label={event.event_type} size="small" />
                  <Typography variant="subtitle2">{event.message}</Typography>
                </Stack>
                <Typography variant="caption" color="text.secondary">
                  {new Date(event.timestamp).toLocaleTimeString()}
                </Typography>
              </Stack>
              {event.details && Object.keys(event.details).length > 0 && (
                <Typography variant="caption" color="text.secondary">
                  {Object.entries(event.details)
                    .map(([key, value]) => `${key}: ${value}`)
                    .join(" · ")}
                </Typography>
              )}
              {index < events.length - 1 && <Divider />}
            </Stack>
          ))}
        </Stack>
      </CardContent>
    </Card>
  );
};

export default AutonomyTimeline;
