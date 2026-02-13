import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  Grid,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography
} from "@mui/material";
import { fetchAccountSummary, fetchPositions } from "../../services/api";

type Position = {
  symbol: string;
  position: number;
  avg_cost: number;
  market_price?: number;
};

const PortfolioAnalysis = () => {
  const [positions, setPositions] = useState<Position[]>([]);
  const [accountValue, setAccountValue] = useState(0);

  useEffect(() => {
    fetchPositions()
      .then((data) => setPositions(data || []))
      .catch(() => setPositions([]));
    fetchAccountSummary()
      .then((data) => setAccountValue(Number(data?.NetLiquidation || 0)))
      .catch(() => setAccountValue(0));
  }, []);

  const totalExposure = positions.reduce(
    (acc, pos) => acc + Math.abs(Number(pos.position || 0) * Number(pos.avg_cost || 0)),
    0
  );

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Portfolio Analysis
        </Typography>
        <Grid container spacing={2} sx={{ mb: 2 }}>
          <Grid item xs={12} md={4}>
            <Typography variant="overline">Account Value</Typography>
            <Typography variant="h6">${accountValue.toFixed(2)}</Typography>
          </Grid>
          <Grid item xs={12} md={4}>
            <Typography variant="overline">Total Exposure</Typography>
            <Typography variant="h6">${totalExposure.toFixed(2)}</Typography>
          </Grid>
          <Grid item xs={12} md={4}>
            <Typography variant="overline">Positions</Typography>
            <Typography variant="h6">{positions.length}</Typography>
          </Grid>
        </Grid>

        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Symbol</TableCell>
              <TableCell>Shares</TableCell>
              <TableCell>Avg Cost</TableCell>
              <TableCell>Market Value</TableCell>
              <TableCell>% of Account</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {positions.map((pos) => {
              const marketValue = Number(pos.position || 0) * Number(pos.avg_cost || 0);
              const percent = accountValue ? (marketValue / accountValue) * 100 : 0;
              return (
                <TableRow key={pos.symbol} hover>
                  <TableCell>{pos.symbol}</TableCell>
                  <TableCell>{pos.position}</TableCell>
                  <TableCell>${Number(pos.avg_cost || 0).toFixed(2)}</TableCell>
                  <TableCell>${marketValue.toFixed(2)}</TableCell>
                  <TableCell>{percent.toFixed(2)}%</TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>

        {positions.length === 0 && (
          <Stack sx={{ mt: 2 }}>
            <Typography variant="body2" color="text.secondary">
              No positions to analyze.
            </Typography>
          </Stack>
        )}
      </CardContent>
    </Card>
  );
};

export default PortfolioAnalysis;
