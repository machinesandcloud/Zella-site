import { useEffect, useState } from "react";
import { Card, CardContent, Chip, Stack, Typography } from "@mui/material";
import { fetchOrders } from "../../services/api";

type OrderRow = {
  id: number;
  symbol: string;
  order_type: string;
  action: string;
  quantity: number;
  status?: string;
};

const OrderGrid = () => {
  const [orders, setOrders] = useState<OrderRow[]>([]);

  useEffect(() => {
    fetchOrders()
      .then((data) => setOrders(data || []))
      .catch(() => setOrders([]));
  }, []);

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Orders
        </Typography>
        {orders.length === 0 && (
          <Typography variant="body2" color="text.secondary">
            No orders yet.
          </Typography>
        )}
        <Stack spacing={1}>
          {orders.map((order) => (
            <Stack
              key={order.id}
              direction="row"
              alignItems="center"
              justifyContent="space-between"
              sx={{ borderBottom: "1px solid #eef2f7", pb: 1 }}
            >
              <Typography variant="body2">
                {order.symbol} · {order.action} · {order.order_type} · {order.quantity}
              </Typography>
              <Chip label={order.status || "SUBMITTED"} size="small" />
            </Stack>
          ))}
        </Stack>
      </CardContent>
    </Card>
  );
};

export default OrderGrid;
