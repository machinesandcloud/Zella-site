import { useEffect, useMemo, useState } from "react";
import { Chip, Stack, Tooltip, Typography, Box } from "@mui/material";
import { getApiTimings } from "../../services/api";

type ApiTiming = {
  url: string;
  method: string;
  status: number | "ERR";
  durationMs: number;
  ts: number;
  ok: boolean;
};

const formatUrl = (url: string) => {
  if (!url) return "-";
  return url.replace(/^https?:\/\/[^/]+/, "");
};

const ApiLatencyBadge = () => {
  const [timings, setTimings] = useState<ApiTiming[]>([]);

  useEffect(() => {
    setTimings(getApiTimings() as ApiTiming[]);
    const handler = (event: Event) => {
      const detail = (event as CustomEvent<ApiTiming>).detail;
      if (detail) {
        setTimings((prev) => [detail, ...prev].slice(0, 50));
      }
    };
    window.addEventListener("api:timing", handler as EventListener);
    return () => {
      window.removeEventListener("api:timing", handler as EventListener);
    };
  }, []);

  const stats = useMemo(() => {
    const recent = timings.slice(0, 10);
    if (!recent.length) {
      return { avg: 0, last: 0, ok: true };
    }
    const avg = Math.round(recent.reduce((sum, t) => sum + t.durationMs, 0) / recent.length);
    const last = recent[0]?.durationMs ?? 0;
    const ok = recent[0]?.ok ?? true;
    return { avg, last, ok };
  }, [timings]);

  const color = stats.avg < 200 ? "success" : stats.avg < 500 ? "warning" : "error";

  return (
    <Tooltip
      title={
        <Box sx={{ p: 0.5 }}>
          <Typography variant="caption" sx={{ display: "block", mb: 0.5 }}>
            API latency (last 10): avg {stats.avg}ms
          </Typography>
          <Stack spacing={0.25}>
            {timings.slice(0, 8).map((t, idx) => (
              <Typography key={`${t.ts}-${idx}`} variant="caption" sx={{ display: "block" }}>
                {t.method} {formatUrl(t.url)} · {t.durationMs}ms · {t.status}
              </Typography>
            ))}
            {timings.length === 0 && (
              <Typography variant="caption">No API samples yet</Typography>
            )}
          </Stack>
        </Box>
      }
      arrow
    >
      <Chip
        label={`API ${stats.last || stats.avg}ms`}
        color={color}
        size="small"
        variant={stats.ok ? "outlined" : "filled"}
      />
    </Tooltip>
  );
};

export default ApiLatencyBadge;
