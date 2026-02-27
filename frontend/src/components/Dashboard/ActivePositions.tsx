import { useEffect, useState } from "react";
import {
  Box,
  Card,
  Button,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
  Chip
} from "@mui/material";
import { closePosition, fetchPositions } from "../../services/api";

const formatCurrency = (value: number | undefined): string => {
  if (value === undefined || value === null) return "--";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2
  }).format(value);
};

const ActivePositions = () => {
  const [positions, setPositions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const loadPositions = async () => {
    try {
      const data = await fetchPositions();
      // API returns array directly from alpaca_client.get_positions()
      const posArray = Array.isArray(data) ? data : (data?.positions || []);
      setPositions(posArray);
    } catch {
      setPositions([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPositions();
    const interval = setInterval(loadPositions, 15000); // Refresh every 15s
    return () => clearInterval(interval);
  }, []);

  const notify = (message: string, severity: "success" | "info" | "warning" | "error" = "info") => {
    window.dispatchEvent(new CustomEvent("app:toast", { detail: { message, severity } }));
  };

  const handleClose = async (symbol: string) => {
    try {
      await closePosition(symbol);
      notify(`Close order sent for ${symbol}.`, "success");
      await loadPositions();
    } catch {
      notify(`Failed to close ${symbol}.`, "error");
    }
  };

  return (
    <Card elevation={0} sx={{ border: "1px solid rgba(255,255,255,0.1)", borderRadius: 3 }}>
      <CardContent sx={{ p: 3 }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Active Positions
          </Typography>
          <Chip
            label={`${positions.length} position${positions.length !== 1 ? "s" : ""}`}
            size="small"
            color={positions.length > 0 ? "primary" : "default"}
          />
        </Box>

        {loading ? (
          <Typography color="text.secondary">Loading positions...</Typography>
        ) : positions.length === 0 ? (
          <Box sx={{
            p: 4,
            textAlign: "center",
            border: "1px dashed rgba(255,255,255,0.1)",
            borderRadius: 2
          }}>
            <Typography color="text.secondary">No active positions</Typography>
            <Typography variant="caption" color="text.secondary">
              The bot will open positions when opportunities are found
            </Typography>
          </Box>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 600 }}>Symbol</TableCell>
                <TableCell sx={{ fontWeight: 600 }} align="right">Qty</TableCell>
                <TableCell sx={{ fontWeight: 600 }} align="right">Entry</TableCell>
                <TableCell sx={{ fontWeight: 600 }} align="right">Current</TableCell>
                <TableCell sx={{ fontWeight: 600 }} align="right">P&L</TableCell>
                <TableCell sx={{ fontWeight: 600 }} align="right">Value</TableCell>
                <TableCell sx={{ fontWeight: 600 }} align="center">Action</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {positions.map((pos, idx) => {
                // Use correct field names from alpaca_client.get_positions()
                const pnl = parseFloat(pos.unrealizedPnL) || 0;
                const pnlPercent = parseFloat(pos.unrealizedPnLPercent) || 0;
                const isProfitable = pnl >= 0;

                return (
                  <TableRow key={`${pos.symbol}-${idx}`}>
                    <TableCell>
                      <Typography sx={{ fontWeight: 600 }}>{pos.symbol}</Typography>
                    </TableCell>
                    <TableCell align="right">
                      {pos.quantity || pos.qty || "--"}
                    </TableCell>
                    <TableCell align="right">
                      {formatCurrency(pos.avgPrice || pos.avg_entry_price)}
                    </TableCell>
                    <TableCell align="right">
                      {formatCurrency(pos.currentPrice || pos.current_price)}
                    </TableCell>
                    <TableCell align="right">
                      <Box sx={{ color: isProfitable ? "#4caf50" : "#f44336" }}>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {isProfitable ? "+" : ""}{formatCurrency(pnl)}
                        </Typography>
                        <Typography variant="caption">
                          ({isProfitable ? "+" : ""}{pnlPercent.toFixed(2)}%)
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell align="right">
                      {formatCurrency(pos.marketValue || pos.market_value)}
                    </TableCell>
                    <TableCell align="center">
                      <Button
                        size="small"
                        variant="outlined"
                        color="error"
                        onClick={() => handleClose(pos.symbol)}
                        sx={{ textTransform: "none", minWidth: 60 }}
                      >
                        Close
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
};

export default ActivePositions;
