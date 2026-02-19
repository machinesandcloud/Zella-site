import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  Typography,
  Box,
  LinearProgress,
  Stack,
  Chip,
  Grid,
  List,
  ListItem,
  ListItemText,
  Paper
} from "@mui/material";
import { Radar, TrendingUp, Psychology } from "@mui/icons-material";

interface ScanData {
  scanning: boolean;
  current_symbol?: string;
  scanned_count: number;
  total_symbols: number;
  opportunities_found: number;
  last_scan_time?: string;
  top_candidates: Array<{
    symbol: string;
    ml_score: number;
    momentum_score: number;
    combined_score: number;
    last_price: number;
    relative_volume: number;
  }>;
}

const AutonomousScannerLive = () => {
  const [scanData, setScanData] = useState<ScanData>({
    scanning: false,
    scanned_count: 0,
    total_symbols: 100,
    opportunities_found: 0,
    top_candidates: []
  });

  useEffect(() => {
    // Simulate scanning data - replace with real WebSocket connection
    const interval = setInterval(() => {
      setScanData(prev => ({
        ...prev,
        scanning: Math.random() > 0.3,
        scanned_count: Math.floor(Math.random() * 100),
        total_symbols: 100,
        opportunities_found: Math.floor(Math.random() * 15),
        current_symbol: ["AAPL", "TSLA", "NVDA", "AMD", "MSFT"][Math.floor(Math.random() * 5)],
        last_scan_time: new Date().toISOString()
      }));
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  const progress = scanData.total_symbols > 0
    ? (scanData.scanned_count / scanData.total_symbols) * 100
    : 0;

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        {/* Header */}
        <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 3 }}>
          <Radar sx={{ fontSize: 32, color: scanData.scanning ? "primary.main" : "text.secondary" }} />
          <Box>
            <Typography variant="h6" fontWeight="bold">
              Market Scanner
            </Typography>
            <Typography variant="body2" color="text.secondary">
              AI-powered stock screening in real-time
            </Typography>
          </Box>
          {scanData.scanning && (
            <Chip
              label="SCANNING"
              color="primary"
              size="small"
              sx={{
                animation: "pulse 1.5s ease-in-out infinite",
                "@keyframes pulse": {
                  "0%, 100%": { opacity: 1 },
                  "50%": { opacity: 0.6 }
                }
              }}
            />
          )}
        </Stack>

        {/* Scanning Progress */}
        <Box sx={{ mb: 3 }}>
          <Stack direction="row" justifyContent="space-between" sx={{ mb: 1 }}>
            <Typography variant="body2" color="text.secondary">
              {scanData.scanning ? `Scanning: ${scanData.current_symbol || "..."}` : "Waiting for next scan"}
            </Typography>
            <Typography variant="body2" fontWeight="bold">
              {scanData.scanned_count} / {scanData.total_symbols} symbols
            </Typography>
          </Stack>
          <LinearProgress
            variant="determinate"
            value={progress}
            sx={{
              height: 8,
              borderRadius: 4,
              backgroundColor: "rgba(255,255,255,0.05)",
              "& .MuiLinearProgress-bar": {
                borderRadius: 4,
                background: "linear-gradient(90deg, #3fd0c9, #f4c76f)"
              }
            }}
          />
        </Box>

        {/* Metrics */}
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={4}>
            <Paper sx={{ p: 2, textAlign: "center", bgcolor: "rgba(63, 208, 201, 0.08)" }}>
              <TrendingUp sx={{ fontSize: 24, color: "primary.main", mb: 0.5 }} />
              <Typography variant="h5" fontWeight="bold">
                {scanData.opportunities_found}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Opportunities
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={4}>
            <Paper sx={{ p: 2, textAlign: "center", bgcolor: "rgba(244, 199, 111, 0.08)" }}>
              <Psychology sx={{ fontSize: 24, color: "warning.main", mb: 0.5 }} />
              <Typography variant="h5" fontWeight="bold">
                {scanData.top_candidates.length}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Top Picks
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={4}>
            <Paper sx={{ p: 2, textAlign: "center", bgcolor: "rgba(255, 255, 255, 0.03)" }}>
              <Typography variant="h5" fontWeight="bold">
                {Math.round(progress)}%
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Complete
              </Typography>
            </Paper>
          </Grid>
        </Grid>

        {/* Top Candidates */}
        <Box>
          <Typography variant="subtitle2" fontWeight="bold" sx={{ mb: 1 }}>
            Top ML-Ranked Candidates
          </Typography>
          {scanData.top_candidates.length > 0 ? (
            <List dense sx={{ maxHeight: 200, overflow: "auto" }}>
              {scanData.top_candidates.map((candidate, idx) => (
                <ListItem
                  key={candidate.symbol}
                  sx={{
                    borderRadius: 2,
                    mb: 1,
                    bgcolor: "rgba(255,255,255,0.02)",
                    border: "1px solid rgba(255,255,255,0.06)"
                  }}
                >
                  <ListItemText
                    primary={
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Chip label={idx + 1} size="small" sx={{ width: 32 }} />
                        <Typography variant="body2" fontWeight="bold">
                          {candidate.symbol}
                        </Typography>
                        <Chip
                          label={`${(candidate.combined_score * 100).toFixed(0)}% score`}
                          size="small"
                          color="primary"
                        />
                      </Stack>
                    }
                    secondary={
                      <Typography variant="caption" color="text.secondary">
                        ${candidate.last_price.toFixed(2)} • Vol: {candidate.relative_volume.toFixed(1)}x
                      </Typography>
                    }
                  />
                </ListItem>
              ))}
            </List>
          ) : (
            <Box
              sx={{
                p: 3,
                textAlign: "center",
                borderRadius: 2,
                bgcolor: "rgba(255,255,255,0.02)",
                border: "1px dashed rgba(255,255,255,0.1)"
              }}
            >
              <Typography variant="body2" color="text.secondary">
                No candidates yet. Scanner will populate this list during market hours.
              </Typography>
            </Box>
          )}
        </Box>

        {scanData.last_scan_time && (
          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 2, textAlign: "center" }}>
            Last scan: {new Date(scanData.last_scan_time).toLocaleTimeString()}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

export default AutonomousScannerLive;
