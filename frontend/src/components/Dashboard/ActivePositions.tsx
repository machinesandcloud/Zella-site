import { useEffect, useState } from "react";
import {
  Card,
  Button,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography
} from "@mui/material";
import { closePosition, fetchPositions } from "../../services/api";

const ActivePositions = () => {
  const [positions, setPositions] = useState<any[]>([]);

  useEffect(() => {
    fetchPositions()
      .then((data) => setPositions(data || []))
      .catch(() => setPositions([]));
  }, []);

  const notify = (message: string, severity: "success" | "info" | "warning" | "error" = "info") => {
    window.dispatchEvent(new CustomEvent("app:toast", { detail: { message, severity } }));
  };

  const handleClose = async (symbol: string) => {
    try {
      await closePosition(symbol);
      notify(`Close order sent for ${symbol}.`, "success");
      const data = await fetchPositions();
      setPositions(data || []);
    } catch (error) {
      notify(`Failed to close ${symbol}.`, "error");
    }
  };

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Active Positions
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Symbol</TableCell>
              <TableCell>Quantity</TableCell>
              <TableCell>Entry Price</TableCell>
              <TableCell>Current Price</TableCell>
              <TableCell>Unrealized PnL ($/%)</TableCell>
              <TableCell>Stop Loss</TableCell>
              <TableCell>Take Profit</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {positions.length === 0 && (
              <TableRow>
                <TableCell colSpan={8}>No active positions</TableCell>
              </TableRow>
            )}
            {positions.map((pos, idx) => (
              <TableRow key={`${pos.symbol}-${idx}`}>
                <TableCell>{pos.symbol}</TableCell>
                <TableCell>{pos.position}</TableCell>
                <TableCell>{pos.entry_price || pos.avg_cost || "--"}</TableCell>
                <TableCell>{pos.current_price || "--"}</TableCell>
                <TableCell>{pos.unrealized_pnl || "--"}</TableCell>
                <TableCell>{pos.stop_loss || "--"}</TableCell>
                <TableCell>{pos.take_profit || "--"}</TableCell>
                <TableCell>
                  <Button
                    size="small"
                    variant="outlined"
                    sx={{ mr: 1 }}
                    onClick={() => handleClose(pos.symbol)}
                  >
                    Close
                  </Button>
                  <Button
                    size="small"
                    onClick={() =>
                      notify(`Modify ticket opened for ${pos.symbol}.`, "info")
                    }
                  >
                    Modify
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
};

export default ActivePositions;
