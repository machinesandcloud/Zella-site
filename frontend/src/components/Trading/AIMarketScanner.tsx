import { useEffect, useState } from "react";
import {
  Button,
  Card,
  CardContent,
  Chip,
  List,
  ListItem,
  ListItemText,
  Stack,
  Typography
} from "@mui/material";
import api from "../../services/api";

const AIMarketScanner = () => {
  const [picks, setPicks] = useState<any[]>([]);

  const load = () => {
    api
      .get("/api/ai/top?limit=6")
      .then((res) => setPicks(res.data.ranked || []))
      .catch(() => setPicks([]));
  };

  const autoTrade = async () => {
    const confirmed = window.confirm("Auto-trade will place PAPER orders for top picks. Continue?");
    if (!confirmed) return;
    await api.post("/api/ai/auto-trade?limit=5&execute=true&confirm_execute=true");
    load();
  };

  const addToWatchlist = (symbol: string) => {
    const stored = localStorage.getItem("zella_watchlist");
    const list = stored ? JSON.parse(stored) : [];
    if (!list.includes(symbol)) {
      const next = [...list, symbol];
      localStorage.setItem("zella_watchlist", JSON.stringify(next));
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          AI Market Picks
        </Typography>
        <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
          <Button size="small" variant="outlined" onClick={load}>
            Refresh
          </Button>
          <Button size="small" variant="contained" onClick={autoTrade}>
            Auto-Trade (Paper)
          </Button>
        </Stack>
        <List dense>
          {picks.length === 0 && <ListItem>No picks available</ListItem>}
          {picks.map((pick) => (
            <ListItem
              key={pick.symbol}
              secondaryAction={
                <Button size="small" onClick={() => addToWatchlist(pick.symbol)}>
                  Watch
                </Button>
              }
            >
              <ListItemText
                primary={
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Typography>{pick.symbol}</Typography>
                    <Chip label={`Score ${Number(pick.combined_score).toFixed(2)}`} size="small" />
                  </Stack>
                }
                secondary={`Confidence: ${(Number(pick.confidence) * 100).toFixed(0)}%`}
              />
            </ListItem>
          ))}
        </List>
      </CardContent>
    </Card>
  );
};

export default AIMarketScanner;
