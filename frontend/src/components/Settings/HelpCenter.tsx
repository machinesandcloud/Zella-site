import { Card, CardContent, List, ListItem, ListItemText, Typography } from "@mui/material";

const HelpCenter = () => {
  const items = [
    { title: "Quick Start Guide", detail: "Setup, connect Alpaca, place first trade" },
    { title: "Risk Management", detail: "Daily loss limits, kill switch, position sizing" },
    { title: "Strategy Guide", detail: "How strategies work and when to use them" },
    { title: "Troubleshooting", detail: "Connection issues, data feed, order errors" }
  ];

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Help Center
        </Typography>
        <List dense>
          {items.map((item) => (
            <ListItem key={item.title}>
              <ListItemText primary={item.title} secondary={item.detail} />
            </ListItem>
          ))}
        </List>
      </CardContent>
    </Card>
  );
};

export default HelpCenter;
