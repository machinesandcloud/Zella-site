import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Autocomplete,
  Button,
  Card,
  CardContent,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography
} from "@mui/material";
import api, { fetchAccountSummary } from "../../services/api";

type SizingMode = "FIXED" | "RISK_BASED";

type OrderForm = {
  symbol: string;
  action: "BUY" | "SELL";
  order_type: string;
  quantity: number;
  limit_price: string;
  stop_price: string;
  take_profit: string;
  stop_loss: string;
  tif: string;
  sizing_mode: SizingMode;
  risk_percent: string;
};

const ORDER_TYPES = [
  "MKT",
  "LMT",
  "STP",
  "STP_LMT",
  "TRAIL",
  "BRACKET",
  "OCO",
  "MOO",
  "MOC",
  "ICEBERG",
  "TWAP",
  "VWAP"
];

const SUPPORTED_ORDER_TYPES = ["MKT", "LMT", "STP", "BRACKET"];

const OrderEntry = () => {
  const [form, setForm] = useState<OrderForm>({
    symbol: "",
    action: "BUY",
    order_type: "MKT",
    quantity: 1,
    limit_price: "",
    stop_price: "",
    take_profit: "",
    stop_loss: "",
    tif: "DAY",
    sizing_mode: "FIXED",
    risk_percent: "1"
  });
  const [accountValue, setAccountValue] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);

  useEffect(() => {
    fetchAccountSummary()
      .then((data) => setAccountValue(Number(data?.NetLiquidation || 0)))
      .catch(() => setAccountValue(0));
  }, []);

  const update = (key: keyof OrderForm, value: string | number) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const symbols = ["AAPL", "MSFT", "TSLA", "NVDA", "AMD", "AMZN"];

  const entryPrice = useMemo(() => {
    const limit = Number(form.limit_price || 0);
    const stop = Number(form.stop_price || 0);
    return limit || stop || 0;
  }, [form.limit_price, form.stop_price]);

  const stopPrice = useMemo(() => Number(form.stop_loss || form.stop_price || 0), [form]);

  const riskPerShare = useMemo(() => {
    if (!entryPrice || !stopPrice) return 0;
    return Math.abs(entryPrice - stopPrice);
  }, [entryPrice, stopPrice]);

  const calculatedShares = useMemo(() => {
    if (form.sizing_mode !== "RISK_BASED") return form.quantity;
    if (!riskPerShare || !accountValue) return 0;
    const riskPct = Number(form.risk_percent || 0) / 100;
    const dollarsAtRisk = accountValue * riskPct;
    return Math.max(0, Math.floor(dollarsAtRisk / riskPerShare));
  }, [form.sizing_mode, form.quantity, form.risk_percent, riskPerShare, accountValue]);

  const riskAtStop = useMemo(() => {
    if (!riskPerShare) return "--";
    const qty = form.sizing_mode === "RISK_BASED" ? calculatedShares : form.quantity;
    return `$${(riskPerShare * qty).toFixed(2)}`;
  }, [riskPerShare, calculatedShares, form.sizing_mode, form.quantity]);

  const unsupported = !SUPPORTED_ORDER_TYPES.includes(form.order_type);

  const applyRMultiple = (multiple: number) => {
    if (!entryPrice || !riskPerShare) return;
    const target =
      form.action === "BUY"
        ? entryPrice + riskPerShare * multiple
        : entryPrice - riskPerShare * multiple;
    update("take_profit", target.toFixed(2));
  };

  const handleSubmit = async () => {
    setError(null);
    setWarning(null);

    if (!form.symbol) {
      setError("Symbol is required.");
      return;
    }
    if (unsupported) {
      setError("Selected order type is not available in the current IBKR mock.");
      return;
    }
    if (form.order_type === "BRACKET" && (!form.take_profit || !form.stop_loss)) {
      setError("Bracket orders require take profit and stop loss.");
      return;
    }

    const quantity = form.sizing_mode === "RISK_BASED" ? calculatedShares : form.quantity;
    if (!quantity || quantity <= 0) {
      setError("Quantity must be greater than zero.");
      return;
    }

    await api.post("/api/trading/order", {
      symbol: form.symbol,
      action: form.action,
      order_type: form.order_type,
      quantity,
      limit_price: form.limit_price ? Number(form.limit_price) : undefined,
      stop_price: form.stop_price ? Number(form.stop_price) : undefined,
      take_profit: form.take_profit ? Number(form.take_profit) : undefined,
      stop_loss: form.stop_loss ? Number(form.stop_loss) : undefined
    });

    setWarning("Order submitted.");
  };

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
          <Typography variant="h6">Advanced Order Entry</Typography>
          <Typography variant="body2" color="text.secondary">
            Account: ${accountValue.toLocaleString() || "0"}
          </Typography>
        </Stack>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        {warning && (
          <Alert severity="success" sx={{ mb: 2 }}>
            {warning}
          </Alert>
        )}

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
                {ORDER_TYPES.map((type) => (
                  <MenuItem key={type} value={type}>
                    {type}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={6} md={3}>
            <FormControl fullWidth>
              <InputLabel>Sizing</InputLabel>
              <Select
                value={form.sizing_mode}
                label="Sizing"
                onChange={(e) => update("sizing_mode", e.target.value)}
              >
                <MenuItem value="FIXED">Fixed</MenuItem>
                <MenuItem value="RISK_BASED">Risk %</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={6} md={3}>
            <TextField
              fullWidth
              label="Risk %"
              value={form.risk_percent}
              onChange={(e) => update("risk_percent", e.target.value)}
              disabled={form.sizing_mode !== "RISK_BASED"}
            />
          </Grid>
          <Grid item xs={6} md={3}>
            <TextField
              fullWidth
              label="Quantity"
              type="number"
              value={form.sizing_mode === "RISK_BASED" ? calculatedShares : form.quantity}
              onChange={(e) => update("quantity", Number(e.target.value))}
              disabled={form.sizing_mode === "RISK_BASED"}
            />
          </Grid>
          <Grid item xs={6} md={3}>
            <FormControl fullWidth>
              <InputLabel>TIF</InputLabel>
              <Select value={form.tif} label="TIF" onChange={(e) => update("tif", e.target.value)}>
                <MenuItem value="DAY">DAY</MenuItem>
                <MenuItem value="GTC">GTC</MenuItem>
              </Select>
            </FormControl>
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

          <Grid item xs={12} md={4}>
            <Typography variant="body2" color="text.secondary">
              Risk at stop
            </Typography>
            <Typography variant="h6">{riskAtStop}</Typography>
          </Grid>
          <Grid item xs={12} md={8}>
            <Stack direction="row" spacing={1} flexWrap="wrap">
              <Button size="small" variant="outlined" onClick={() => applyRMultiple(1)}>
                1R
              </Button>
              <Button size="small" variant="outlined" onClick={() => applyRMultiple(2)}>
                2R
              </Button>
              <Button
                size="small"
                variant="outlined"
                onClick={() => update("quantity", Math.max(1, Math.floor(form.quantity / 2)))}
              >
                Close 50%
              </Button>
              <Button size="small" variant="outlined" onClick={() => update("action", "SELL")}>
                Close All
              </Button>
              <Button
                size="small"
                variant="outlined"
                onClick={() => update("action", form.action === "BUY" ? "SELL" : "BUY")}
              >
                Reverse
              </Button>
            </Stack>
          </Grid>
          <Grid item xs={12}>
            <Button variant="contained" color="primary" fullWidth onClick={handleSubmit}>
              Submit Order
            </Button>
            {unsupported && (
              <Typography variant="caption" color="text.secondary">
                Unsupported types will be enabled when IBKR order APIs go live.
              </Typography>
            )}
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
};

export default OrderEntry;
