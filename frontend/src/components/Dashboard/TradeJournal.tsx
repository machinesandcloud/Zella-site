import { useEffect, useState } from "react";
import {
  Button,
  Card,
  CardContent,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography
} from "@mui/material";
import { fetchTrades, updateTradeNotes } from "../../services/api";

type Trade = {
  id: number;
  symbol: string;
  action: string;
  quantity: number;
  entry_price?: number | null;
  exit_price?: number | null;
  pnl?: number | null;
  pnl_percent?: number | null;
  entry_time?: string | null;
  exit_time?: string | null;
  status?: string | null;
  notes?: string | null;
  setup_tag?: string | null;
  catalyst?: string | null;
  stop_method?: string | null;
  risk_mode?: string | null;
};

const TradeJournal = () => {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [editing, setEditing] = useState<Trade | null>(null);
  const [notes, setNotes] = useState("");
  const [setupTag, setSetupTag] = useState("");
  const [catalyst, setCatalyst] = useState("");
  const [stopMethod, setStopMethod] = useState("");
  const [riskMode, setRiskMode] = useState("");

  const load = () => {
    fetchTrades()
      .then((data) => setTrades(data || []))
      .catch(() => setTrades([]));
  };

  useEffect(() => {
    load();
  }, []);

  const openNotes = (trade: Trade) => {
    setEditing(trade);
    setNotes(trade.notes || "");
    setSetupTag(trade.setup_tag || "");
    setCatalyst(trade.catalyst || "");
    setStopMethod(trade.stop_method || "");
    setRiskMode(trade.risk_mode || "");
  };

  const saveNotes = async () => {
    if (!editing) return;
    await updateTradeNotes(editing.id, {
      notes,
      setup_tag: setupTag || undefined,
      catalyst: catalyst || undefined,
      stop_method: stopMethod || undefined,
      risk_mode: riskMode || undefined
    });
    setEditing(null);
    load();
  };

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
          <Typography variant="h6">Trade Journal</Typography>
          <Button size="small" variant="outlined" onClick={load}>
            Refresh
          </Button>
        </Stack>

        {trades.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No trades recorded.
          </Typography>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Symbol</TableCell>
                <TableCell>Side</TableCell>
                <TableCell>Qty</TableCell>
                <TableCell>Entry</TableCell>
                <TableCell>Exit</TableCell>
                <TableCell>PnL</TableCell>
                <TableCell>Setup</TableCell>
                <TableCell>Catalyst</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Notes</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {trades.map((trade) => (
                <TableRow key={trade.id} hover>
                  <TableCell>{trade.symbol}</TableCell>
                  <TableCell>{trade.action}</TableCell>
                  <TableCell>{trade.quantity}</TableCell>
                  <TableCell>{trade.entry_price ?? "--"}</TableCell>
                  <TableCell>{trade.exit_price ?? "--"}</TableCell>
                  <TableCell>{trade.pnl ?? 0}</TableCell>
                  <TableCell>{trade.setup_tag ?? "--"}</TableCell>
                  <TableCell>{trade.catalyst ?? "--"}</TableCell>
                  <TableCell>{trade.status ?? "--"}</TableCell>
                  <TableCell align="right">
                    <Button size="small" onClick={() => openNotes(trade)}>
                      Edit
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>

      <Dialog open={Boolean(editing)} onClose={() => setEditing(null)} fullWidth maxWidth="sm">
        <DialogTitle>Trade Notes</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              fullWidth
              label="Setup Tag (Momentum, Reversal, Penny, Trend Pullback)"
              value={setupTag}
              onChange={(e) => setSetupTag(e.target.value)}
            />
            <TextField
              fullWidth
              label="Catalyst (Earnings, FDA, PR, Technical Breakout)"
              value={catalyst}
              onChange={(e) => setCatalyst(e.target.value)}
            />
            <TextField
              fullWidth
              label="Stop Method (ATR, Std Dev, Support)"
              value={stopMethod}
              onChange={(e) => setStopMethod(e.target.value)}
            />
            <TextField
              fullWidth
              label="Risk Mode (Percent / Fixed $)"
              value={riskMode}
              onChange={(e) => setRiskMode(e.target.value)}
            />
          </Stack>
          <TextField
            fullWidth
            multiline
            minRows={6}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            sx={{ mt: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditing(null)}>Cancel</Button>
          <Button variant="contained" onClick={saveNotes}>
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Card>
  );
};

export default TradeJournal;
