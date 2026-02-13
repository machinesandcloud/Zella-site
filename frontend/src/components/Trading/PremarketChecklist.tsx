import { useEffect, useState } from "react";
import { Card, CardContent, Chip, Stack, Typography } from "@mui/material";
import { fetchMarketSession } from "../../services/api";

const CHECKLIST = [
  "Limit orders only (premarket)",
  "Expect wider spreads and lower liquidity",
  "Confirm catalyst/news headline",
  "Use smaller size and defined stop",
  "Avoid holding into open unless planned"
];

const PremarketChecklist = () => {
  const [session, setSession] = useState<string>("UNKNOWN");

  useEffect(() => {
    fetchMarketSession()
      .then((data) => setSession(data?.session || "UNKNOWN"))
      .catch(() => setSession("UNKNOWN"));
  }, []);

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
          <Typography variant="h6">Premarket Checklist</Typography>
          <Chip label={session} size="small" color={session === "REGULAR" ? "success" : "default"} />
        </Stack>
        <Stack spacing={1}>
          {CHECKLIST.map((item) => (
            <Typography key={item} variant="body2" color="text.secondary">
              • {item}
            </Typography>
          ))}
        </Stack>
      </CardContent>
    </Card>
  );
};

export default PremarketChecklist;
