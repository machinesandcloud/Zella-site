import { useState } from "react";
import {
  Autocomplete,
  Button,
  Card,
  CardContent,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Select,
  TextField,
  Typography
} from "@mui/material";
import api from "../../services/api";

const OrderEntry = () => {
  const [form, setForm] = useState({
    symbol: "",
    action: "BUY",
    order_type: "MKT",
    quantity: 1,
    limit_price: "",
    stop_price: "",
    take_profit: "",
    stop_loss: ""
  });

  const update = (key: string, value: string | number) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const symbols = ["AAPL", "MSFT", "TSLA", "NVDA", "AMD", "AMZN"];

  const riskAtStop = () => {
    const stop = Number(form.stop_loss || form.stop_price || 0);
    const limit = Number(form.limit_price || 0);
    const entry = limit || stop || 0;
    if (!entry || !stop) return "--";
    const risk = Math.abs(entry - stop) * Number(form.quantity);
    return `$${risk.toFixed(2)}`;
  };

  const handleSubmit = async () => {
    await api.post("/api/trading/order", {
      symbol: form.symbol,
      action: form.action,
      order_type: form.order_type,
      quantity: Number(form.quantity),
      limit_price: form.limit_price ? Number(form.limit_price) : undefined,
      stop_price: form.stop_price ? Number(form.stop_price) : undefined,
      take_profit: form.take_profit ? Number(form.take_profit) : undefined,
      stop_loss: form.stop_loss ? Number(form.stop_loss) : undefined
    });
  };

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Order Entry
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <Autocomplete
              freeSolo
              options={symbols}
              value={form.symbol}
              onInputChange={(_, value) => update("symbol", value.toUpperCase())}
              renderInput={(params) => <TextField {...params} label="Symbol" fullWidth />}
            />
          </Grid>
          <Grid item xs={6} md={4}>
            <FormControl fullWidth>
              <InputLabel>Action</InputLabel>
              <Select
                value={form.action}
                label="Action"
                onChange={(e) => update("action", e.target.value)}
              >
                <MenuItem value="BUY">BUY</MenuItem>
                <MenuItem value="SELL">SELL</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={6} md={4}>
            <FormControl fullWidth>
              <InputLabel>Order Type</InputLabel>
              <Select
                value={form.order_type}
                label="Order Type"
                onChange={(e) => update("order_type", e.target.value)}
              >
                <MenuItem value="MKT">Market</MenuItem>
                <MenuItem value="LMT">Limit</MenuItem>
                <MenuItem value="STP">Stop</MenuItem>
                <MenuItem value="BRACKET">Bracket</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={6} md={3}>
            <TextField
              fullWidth
              label="Quantity"
              type="number"
              value={form.quantity}
              onChange={(e) => update("quantity", Number(e.target.value))}
            />
          </Grid>
          <Grid item xs={6} md={3}>
            <TextField
              fullWidth
              label="Limit Price"
              value={form.limit_price}
              onChange={(e) => update("limit_price", e.target.value)}
            />
          </Grid>
          <Grid item xs={6} md={3}>
            <TextField
              fullWidth
              label="Stop Price"
              value={form.stop_price}
              onChange={(e) => update("stop_price", e.target.value)}
            />
          </Grid>
          <Grid item xs={6} md={3}>
            <TextField
              fullWidth
              label="Take Profit"
              value={form.take_profit}
              onChange={(e) => update("take_profit", e.target.value)}
            />
          </Grid>
          <Grid item xs={6} md={3}>
            <TextField
              fullWidth
              label="Stop Loss"
              value={form.stop_loss}
              onChange={(e) => update("stop_loss", e.target.value)}
            />
          </Grid>
          <Grid item xs={12} md={3}>
            <Typography variant="body2" color="text.secondary">
              Risk at stop
            </Typography>
            <Typography variant="h6">{riskAtStop()}</Typography>
          </Grid>
          <Grid item xs={12} md={3}>
            <Button variant="contained" color="primary" fullWidth onClick={handleSubmit}>
              Submit Order
            </Button>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
};

export default OrderEntry;
