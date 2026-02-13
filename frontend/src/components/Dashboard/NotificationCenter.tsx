import { useEffect, useState } from "react";
import { Card, CardContent, Chip, Stack, Typography } from "@mui/material";
import { fetchAlerts, acknowledgeAlert } from "../../services/api";

type AlertItem = {
  id: string;
  severity: string;
  message: string;
  created_at: string;
  acknowledged: boolean;
};

const NotificationCenter = () => {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);

  const load = () => {
    fetchAlerts()
      .then((data) => setAlerts(data || []))
      .catch(() => setAlerts([]));
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, []);

  const ack = async (id: string) => {
    await acknowledgeAlert(id);
    load();
  };

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Notifications
        </Typography>
        {alerts.length === 0 && (
          <Typography variant="body2" color="text.secondary">
            No alerts.
          </Typography>
        )}
        <Stack spacing={1}>
          {alerts.map((alert) => (
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
      </CardContent>
    </Card>
  );
};

export default NotificationCenter;
