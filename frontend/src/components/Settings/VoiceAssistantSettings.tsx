import { Card, CardContent, Stack, Switch, Typography } from "@mui/material";

const VoiceAssistantSettings = () => {
  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Voice Assistant
        </Typography>
        <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 1 }}>
          <Typography>Enable voice commands</Typography>
          <Switch defaultChecked />
        </Stack>
        <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 1 }}>
          <Typography>Wake word: "Hey Zella"</Typography>
          <Switch defaultChecked />
        </Stack>
        <Typography variant="body2" color="text.secondary">
          Voice interface runs locally in browser. Commands require confirmation for trades.
        </Typography>
      </CardContent>
    </Card>
  );
};

export default VoiceAssistantSettings;
