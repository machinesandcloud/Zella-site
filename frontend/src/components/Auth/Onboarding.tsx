import { Card, CardContent, List, ListItem, ListItemText, Typography } from "@mui/material";

const steps = [
  "Welcome tour",
  "Connect IBKR paper trading",
  "Configure risk settings",
  "Select strategies",
  "Complete paper trading tutorial",
  "Review dashboard walkthrough"
];

const Onboarding = () => {
  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Onboarding Checklist
        </Typography>
        <List dense>
          {steps.map((step, idx) => (
            <ListItem key={`${step}-${idx}`}>
              <ListItemText primary={step} />
            </ListItem>
          ))}
        </List>
      </CardContent>
    </Card>
  );
};

export default Onboarding;
