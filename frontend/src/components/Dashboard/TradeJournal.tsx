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
};

const TradeJournal = () => {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [editing, setEditing] = useState<Trade | null>(null);
  const [notes, setNotes] = useState("");

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
  };

  const saveNotes = async () => {
    if (!editing) return;
    await updateTradeNotes(editing.id, notes);
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
          <TextField
            fullWidth
            multiline
            minRows={6}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            sx={{ mt: 1 }}
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
