import { useEffect, useMemo, useState } from "react";
import {
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography
} from "@mui/material";
import { cancelOrder, fetchOrders, modifyOrder } from "../../services/api";

type OrderRow = {
  id: number;
  symbol: string;
  order_type: string;
  action: string;
  quantity: number;
  filled_quantity?: number | null;
  avg_fill_price?: number | null;
  limit_price?: number | null;
  stop_price?: number | null;
  status?: string | null;
  placed_at?: string | null;
};

const OrderGrid = () => {
  const [orders, setOrders] = useState<OrderRow[]>([]);
  const [editing, setEditing] = useState<OrderRow | null>(null);
  const [editForm, setEditForm] = useState({ quantity: "", limit_price: "", stop_price: "" });

  const load = () => {
    fetchOrders()
      .then((data) => setOrders(data || []))
      .catch(() => setOrders([]));
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 7000);
    return () => clearInterval(interval);
  }, []);

  const statusColor = (status?: string | null) => {
    const normalized = status?.toUpperCase();
    if (normalized === "FILLED") return "success";
    if (normalized === "REJECTED") return "error";
    if (normalized === "CANCELLED") return "default";
    return "warning";
  };

  const openEdit = (order: OrderRow) => {
    setEditing(order);
    setEditForm({
      quantity: String(order.quantity ?? ""),
      limit_price: order.limit_price ? String(order.limit_price) : "",
      stop_price: order.stop_price ? String(order.stop_price) : ""
    });
  };

  const handleModify = async () => {
    if (!editing) return;
    const payload = {
      symbol: editing.symbol,
      action: editing.action,
      order_type: editing.order_type,
      quantity: Number(editForm.quantity) || editing.quantity,
      limit_price: editForm.limit_price ? Number(editForm.limit_price) : undefined,
      stop_price: editForm.stop_price ? Number(editForm.stop_price) : undefined,
      asset_type: "STK"
    };
    await modifyOrder(editing.id, payload);
    setEditing(null);
    load();
  };

  const handleCancel = async (orderId: number) => {
    await cancelOrder(orderId);
    load();
  };

  const rows = useMemo(() => orders, [orders]);

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
          <Typography variant="h6">Orders</Typography>
          <Button size="small" variant="outlined" onClick={load}>
            Refresh
          </Button>
        </Stack>
        {rows.length === 0 && (
          <Typography variant="body2" color="text.secondary">
            No orders yet.
          </Typography>
        )}
        {rows.length > 0 && (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Time</TableCell>
                <TableCell>Symbol</TableCell>
                <TableCell>Side</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Qty</TableCell>
                <TableCell>Filled</TableCell>
                <TableCell>Price</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((order) => (
                <TableRow key={order.id} hover>
                  <TableCell>
                    {order.placed_at ? new Date(order.placed_at).toLocaleTimeString() : "--"}
                  </TableCell>
                  <TableCell>{order.symbol}</TableCell>
                  <TableCell>{order.action}</TableCell>
                  <TableCell>{order.order_type}</TableCell>
                  <TableCell>{order.quantity}</TableCell>
                  <TableCell>{order.filled_quantity ?? 0}</TableCell>
                  <TableCell>
                    {order.avg_fill_price ?? order.limit_price ?? order.stop_price ?? "--"}
                  </TableCell>
                  <TableCell>
                    <Chip label={order.status || "SUBMITTED"} size="small" color={statusColor(order.status)} />
                  </TableCell>
                  <TableCell align="right">
                    <Stack direction="row" spacing={1} justifyContent="flex-end">
                      <Tooltip title="Modify">
                        <span>
                          <IconButton
                            size="small"
                            onClick={() => openEdit(order)}
                            disabled={order.status?.toUpperCase() === "FILLED"}
                          >
                            ✏️
                          </IconButton>
                        </span>
                      </Tooltip>
                      <Tooltip title="Cancel">
                        <span>
                          <IconButton
                            size="small"
                            onClick={() => handleCancel(order.id)}
                            disabled={order.status?.toUpperCase() === "FILLED"}
                          >
                            ❌
                          </IconButton>
                        </span>
                      </Tooltip>
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>

      <Dialog open={Boolean(editing)} onClose={() => setEditing(null)} fullWidth maxWidth="sm">
        <DialogTitle>Modify Order</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="Quantity"
              type="number"
              value={editForm.quantity}
              onChange={(e) => setEditForm((prev) => ({ ...prev, quantity: e.target.value }))}
              fullWidth
            />
            <TextField
              label="Limit Price"
              value={editForm.limit_price}
              onChange={(e) => setEditForm((prev) => ({ ...prev, limit_price: e.target.value }))}
              fullWidth
            />
            <TextField
              label="Stop Price"
              value={editForm.stop_price}
              onChange={(e) => setEditForm((prev) => ({ ...prev, stop_price: e.target.value }))}
              fullWidth
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditing(null)}>Cancel</Button>
          <Button variant="contained" onClick={handleModify}>
            Save Changes
          </Button>
        </DialogActions>
      </Dialog>
    </Card>
  );
};

export default OrderGrid;
