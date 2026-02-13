import { useEffect, useMemo, useState } from "react";
import {
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  List,
  ListItem,
  ListItemText,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography
} from "@mui/material";
import api from "../../services/api";

type ScanMode = "MOMENTUM" | "REVERSAL" | "PENNY";

const AIMarketScanner = () => {
  const [picks, setPicks] = useState<any[]>([]);
  const [mode, setMode] = useState<ScanMode>("MOMENTUM");

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
    window.dispatchEvent(
      new CustomEvent("app:toast", {
        detail: { message: "Auto-trade submitted for top picks.", severity: "success" }
      })
    );
  };

  const addToWatchlist = (symbol: string) => {
    const stored = localStorage.getItem("zella_watchlist");
    const list = stored ? JSON.parse(stored) : [];
    if (!list.includes(symbol)) {
      const next = [...list, symbol];
      localStorage.setItem("zella_watchlist", JSON.stringify(next));
      window.dispatchEvent(new Event("watchlist:update"));
      window.dispatchEvent(
        new CustomEvent("app:toast", {
          detail: { message: `${symbol} added to watchlist.`, severity: "info" }
        })
      );
    }
  };

  const criteria = useMemo(() => {
    if (mode === "PENNY") {
      return [
        "Price near $1-$5 with exchange listing",
        "Breaking news catalyst (earnings, FDA, PR)",
        "Float under 100M (prefer under 50M)",
        "Premarket gap with strong relative volume",
        "Bull flag or premarket high breakout"
      ];
    }
    if (mode === "REVERSAL") {
      return [
        "New intraday high/low with 5-10 same-color candles",
        "RSI extreme (<10 or >90)",
        "Entry near inflection point (support/resistance)",
        "Stop just beyond high/low or fixed buffer",
        "Use trailing stops to protect profits"
      ];
    }
    return [
      "Float under 100M shares",
      "Strong daily chart above key MAs",
      "Relative volume >= 2x average",
      "Catalyst or technical breakout",
      "Bull flag or micro-pullback at open"
    ];
  }, [mode]);

  useEffect(() => {
    load();
  }, []);

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Stack spacing={1} sx={{ mb: 2 }}>
          <Typography variant="h6">AI Market Picks</Typography>
          <Typography variant="body2" color="text.secondary">
            Playbook-guided scans based on momentum, reversal, and penny-stock criteria.
          </Typography>
        </Stack>
        <ToggleButtonGroup
          size="small"
          value={mode}
          exclusive
          onChange={(_, value) => value && setMode(value)}
          sx={{ mb: 2 }}
        >
          <ToggleButton value="MOMENTUM">Momentum</ToggleButton>
          <ToggleButton value="REVERSAL">Reversal</ToggleButton>
          <ToggleButton value="PENNY">Penny</ToggleButton>
        </ToggleButtonGroup>

        <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mb: 2 }}>
          {criteria.map((item) => (
            <Chip key={item} label={item} size="small" />
          ))}
        </Stack>

        <Divider sx={{ mb: 2 }} />
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
