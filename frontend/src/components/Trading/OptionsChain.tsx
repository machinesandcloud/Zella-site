import { Card, CardContent, Grid, Typography } from "@mui/material";

const OPTIONS = [
  { strike: 150, call: 2.4, put: 2.1, iv: 32, delta: 0.52 },
  { strike: 155, call: 1.8, put: 2.7, iv: 34, delta: 0.45 },
  { strike: 160, call: 1.2, put: 3.4, iv: 36, delta: 0.38 },
];

const OptionsChain = () => {
  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Options Chain (Mock)
        </Typography>
        <Grid container spacing={1} sx={{ mb: 1 }}>
          <Grid item xs={3}>
            <Typography variant="caption">Call</Typography>
          </Grid>
          <Grid item xs={2}>
            <Typography variant="caption">Strike</Typography>
          </Grid>
          <Grid item xs={3}>
            <Typography variant="caption">Put</Typography>
          </Grid>
          <Grid item xs={2}>
            <Typography variant="caption">IV</Typography>
          </Grid>
          <Grid item xs={2}>
            <Typography variant="caption">Delta</Typography>
          </Grid>
        </Grid>
        {OPTIONS.map((row) => (
          <Grid container spacing={1} key={row.strike} sx={{ mb: 1 }}>
            <Grid item xs={3}>
              <Typography>{row.call}</Typography>
            </Grid>
            <Grid item xs={2}>
              <Typography>{row.strike}</Typography>
            </Grid>
            <Grid item xs={3}>
              <Typography>{row.put}</Typography>
            </Grid>
            <Grid item xs={2}>
              <Typography>{row.iv}%</Typography>
            </Grid>
            <Grid item xs={2}>
              <Typography>{row.delta}</Typography>
            </Grid>
          </Grid>
        ))}
      </CardContent>
    </Card>
  );
};

export default OptionsChain;
