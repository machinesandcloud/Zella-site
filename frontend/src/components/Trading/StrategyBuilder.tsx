import { useState } from "react";
import {
  Button,
  Card,
  CardContent,
  Grid,
  Stack,
  TextField,
  Typography
} from "@mui/material";

const StrategyBuilder = () => {
  const [name, setName] = useState("");
  const [rules, setRules] = useState<string[]>(["RSI < 30", "Price above VWAP"]);
  const [newRule, setNewRule] = useState("");

  const addRule = () => {
    if (!newRule.trim()) return;
    setRules((prev) => [...prev, newRule.trim()]);
    setNewRule("");
  };

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Strategy Builder (Mock)
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Strategy Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Add Rule"
              value={newRule}
              onChange={(e) => setNewRule(e.target.value)}
            />
          </Grid>
          <Grid item xs={12}>
            <Stack direction="row" spacing={2}>
              <Button size="small" variant="outlined" onClick={addRule}>
                Add Rule
              </Button>
              <Button size="small" variant="contained">
                Save Strategy
              </Button>
            </Stack>
          </Grid>
        </Grid>

        <Stack spacing={1} sx={{ mt: 2 }}>
          {rules.map((rule, idx) => (
            <Typography key={`${rule}-${idx}`} variant="body2">
              • {rule}
            </Typography>
          ))}
        </Stack>
      </CardContent>
    </Card>
  );
};

export default StrategyBuilder;
