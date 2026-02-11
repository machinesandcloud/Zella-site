import { Card, CardContent, Chip, Stack, Typography } from "@mui/material";

const Watchlist = () => {
  const symbols = ["AAPL", "MSFT", "TSLA", "NVDA"];

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Watchlist
        </Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap">
          {symbols.map((symbol) => (
            <Chip key={symbol} label={symbol} variant="outlined" />
          ))}
        </Stack>
      </CardContent>
    </Card>
  );
};

export default Watchlist;
