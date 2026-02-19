import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  Typography,
  Box,
  Stack,
  Chip,
  Alert,
  LinearProgress,
  Divider
} from "@mui/material";
import { Psychology, AccessTime, TrendingUp } from "@mui/icons-material";
import { getAutonomousStatus } from "../../services/api";

interface Decision {
  id: string;
  time: string;
  type: string;
  action: string;
  status: string;
  metadata?: {
    strategies?: string[];
    confidence?: number;
    raw_confidence?: number;
    num_strategies?: number;
    order_id?: string;
    count?: number;
    atr?: number;
    stop_loss?: number;
    take_profit?: number;
    power_hour?: boolean;
    position_sizing?: string;
    patterns_detected?: number;
    news_catalysts?: number;
    top_symbols?: string[];
  };
}

interface BotStatus {
  enabled: boolean;
  running: boolean;
  mode: string;
  risk_posture: string;
  last_scan: string | null;
  decisions: Decision[];
  connected: boolean;
}

const BotThinkingProcess = () => {
  const [status, setStatus] = useState<BotStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await getAutonomousStatus();
        setStatus(data);
      } catch (error) {
        console.error("Error loading bot status:", error);
      } finally {
        setLoading(false);
      }
    };

    load();
    const interval = setInterval(load, 3000); // Refresh every 3 seconds
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
        <CardContent>
          <LinearProgress />
        </CardContent>
      </Card>
    );
  }

  if (!status) {
    return (
      <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
        <CardContent>
          <Alert severity="warning">
            Backend not connected. Bot thinking process unavailable.
          </Alert>
        </CardContent>
      </Card>
    );
  }

  // Extract recent SCAN and TRADE decisions
  const scanDecisions = status.decisions.filter(d => d.type === "SCAN");
  const tradeDecisions = status.decisions.filter(d => d.type === "TRADE");
  const lastScan = scanDecisions.length > 0 ? scanDecisions[0] : null;
  const recentTrades = tradeDecisions.slice(0, 5);

  // Check market hours (9:30 AM - 4:00 PM ET)
  const now = new Date();
  const etTime = new Date(now.toLocaleString("en-US", { timeZone: "America/New_York" }));
  const hours = etTime.getHours();
  const minutes = etTime.getMinutes();
  const isMarketHours = (hours > 9 || (hours === 9 && minutes >= 30)) && hours < 16;

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        {/* Header */}
        <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 3 }}>
          <Psychology sx={{ fontSize: 32, color: status.running ? "primary.main" : "text.secondary" }} />
          <Box>
            <Typography variant="h6" fontWeight="bold">
              Bot Thinking Process
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Real-time view of bot's decision-making
            </Typography>
          </Box>
        </Stack>

        {/* Market Status */}
        {!isMarketHours && (
          <Alert severity="info" icon={<AccessTime />} sx={{ mb: 2 }}>
            Market is currently closed. Bot will resume scanning during market hours (9:30 AM - 4:00 PM ET).
          </Alert>
        )}

        {/* Bot Status */}
        <Box sx={{ mb: 3 }}>
          <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
            <Chip
              label={status.running ? "RUNNING" : "STOPPED"}
              color={status.running ? "success" : "default"}
              size="small"
            />
            <Chip label={status.mode} size="small" variant="outlined" />
            <Chip label={status.risk_posture} size="small" variant="outlined" />
          </Stack>

          {!status.connected && (
            <Alert severity="error" sx={{ mb: 2 }}>
              Not connected to broker. Bot cannot trade without broker connection.
            </Alert>
          )}

          {!status.running && status.connected && (
            <Alert severity="warning">
              Bot is stopped. Enable it in the Autonomous Trading Engine control panel above.
            </Alert>
          )}
        </Box>

        <Divider sx={{ mb: 3 }} />

        {/* Last Scan */}
        {lastScan && (
          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle2" fontWeight="bold" sx={{ mb: 1 }}>
              Last Market Scan
            </Typography>
            <Box
              sx={{
                p: 2,
                borderRadius: 2,
                bgcolor: "rgba(63, 208, 201, 0.08)",
                border: "1px solid rgba(63, 208, 201, 0.2)"
              }}
            >
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                <Typography variant="body2" fontWeight="medium">
                  {lastScan.action}
                </Typography>
                <Stack direction="row" spacing={1} alignItems="center">
                  {lastScan.metadata?.power_hour && (
                    <Chip label="POWER HOUR" size="small" color="warning" sx={{ height: 18, fontSize: "0.6rem" }} />
                  )}
                  <Typography variant="caption" color="text.secondary">
                    {lastScan.time}
                  </Typography>
                </Stack>
              </Stack>
              <Stack spacing={1}>
                {lastScan.metadata?.count !== undefined && (
                  <Typography variant="body2" color="success.main" fontWeight="bold">
                    Found {lastScan.metadata.count} opportunities
                  </Typography>
                )}
                <Stack direction="row" spacing={2}>
                  {lastScan.metadata?.patterns_detected !== undefined && (
                    <Typography variant="caption" color="text.secondary">
                      Patterns: {lastScan.metadata.patterns_detected}
                    </Typography>
                  )}
                  {lastScan.metadata?.news_catalysts !== undefined && (
                    <Typography variant="caption" color="text.secondary">
                      News Catalysts: {lastScan.metadata.news_catalysts}
                    </Typography>
                  )}
                </Stack>
                {lastScan.metadata?.top_symbols && lastScan.metadata.top_symbols.length > 0 && (
                  <Box>
                    <Typography variant="caption" color="text.secondary" fontWeight="bold" sx={{ display: "block", mb: 0.5 }}>
                      Top Picks:
                    </Typography>
                    <Stack direction="row" spacing={0.5} flexWrap="wrap" gap={0.5}>
                      {lastScan.metadata.top_symbols.map((symbol: string, idx: number) => (
                        <Chip
                          key={idx}
                          label={symbol}
                          size="small"
                          color={idx === 0 ? "success" : idx === 1 ? "warning" : "default"}
                          sx={{ height: 20, fontSize: "0.65rem" }}
                        />
                      ))}
                    </Stack>
                  </Box>
                )}
              </Stack>
            </Box>
          </Box>
        )}

        {/* Recent Trades */}
        {recentTrades.length > 0 && (
          <Box>
            <Typography variant="subtitle2" fontWeight="bold" sx={{ mb: 2 }}>
              Recent Trading Decisions
            </Typography>
            <Stack spacing={2}>
              {recentTrades.map((trade) => {
                // Extract symbol from action text (e.g., "BUY 10 AAPL @ $150.50")
                const actionParts = trade.action.match(/(BUY|SELL)\s+(\d+)\s+([A-Z]+)\s+@\s+\$([0-9.]+)/);
                const symbol = actionParts ? actionParts[3] : "Unknown";
                const quantity = actionParts ? actionParts[2] : "?";
                const price = actionParts ? actionParts[4] : "?";
                const side = actionParts ? actionParts[1] : "?";

                return (
                  <Box
                    key={trade.id}
                    sx={{
                      p: 2,
                      borderRadius: 2,
                      bgcolor: trade.status === "SUCCESS"
                        ? "rgba(46, 125, 50, 0.08)"
                        : "rgba(255, 152, 0, 0.08)",
                      border: trade.status === "SUCCESS"
                        ? "1px solid rgba(46, 125, 50, 0.2)"
                        : "1px solid rgba(255, 152, 0, 0.2)"
                    }}
                  >
                    <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 1 }}>
                      <Stack direction="row" spacing={1} alignItems="center">
                        <TrendingUp
                          sx={{
                            fontSize: 20,
                            color: side === "BUY" ? "success.main" : "error.main"
                          }}
                        />
                        <Typography variant="body2" fontWeight="bold">
                          {side} {quantity} {symbol}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          @ ${price}
                        </Typography>
                      </Stack>
                      <Stack spacing={0.5} alignItems="flex-end">
                        <Chip
                          label={trade.status}
                          size="small"
                          color={trade.status === "SUCCESS" ? "success" : "warning"}
                          sx={{ height: 20, fontSize: "0.65rem" }}
                        />
                        <Typography variant="caption" color="text.secondary">
                          {trade.time}
                        </Typography>
                      </Stack>
                    </Stack>

                    {/* Strategies Used */}
                    {trade.metadata?.strategies && trade.metadata.strategies.length > 0 && (
                      <Box sx={{ mb: 1 }}>
                        <Typography variant="caption" color="text.secondary" fontWeight="bold" sx={{ display: "block", mb: 0.5 }}>
                          Strategies Used:
                        </Typography>
                        <Stack direction="row" spacing={0.5} flexWrap="wrap" gap={0.5}>
                          {trade.metadata.strategies.map((strategy, idx) => (
                            <Chip
                              key={idx}
                              label={strategy.replace(/_/g, " ")}
                              size="small"
                              sx={{
                                height: 18,
                                fontSize: "0.6rem",
                                bgcolor: "rgba(255,255,255,0.05)"
                              }}
                            />
                          ))}
                        </Stack>
                      </Box>
                    )}

                    {/* Confidence */}
                    {trade.metadata?.confidence !== undefined && (
                      <Box>
                        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 0.5 }}>
                          <Typography variant="caption" color="text.secondary" fontWeight="bold">
                            Confidence:
                          </Typography>
                          <Typography variant="caption" fontWeight="bold" color={
                            trade.metadata.confidence > 0.75 ? "success.main" : "warning.main"
                          }>
                            {(trade.metadata.confidence * 100).toFixed(0)}%
                          </Typography>
                        </Stack>
                        <LinearProgress
                          variant="determinate"
                          value={trade.metadata.confidence * 100}
                          sx={{
                            height: 6,
                            borderRadius: 3,
                            bgcolor: "rgba(255,255,255,0.05)",
                            "& .MuiLinearProgress-bar": {
                              borderRadius: 3,
                              background: trade.metadata.confidence > 0.75
                                ? "linear-gradient(90deg, #4caf50, #81c784)"
                                : "linear-gradient(90deg, #ff9800, #ffb74d)"
                            }
                          }}
                        />
                      </Box>
                    )}

                    {/* Number of strategies agreeing */}
                    {trade.metadata?.num_strategies && (
                      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
                        {trade.metadata.num_strategies} strategies agreed on this trade
                      </Typography>
                    )}

                    {/* ATR-based Risk Management */}
                    {trade.metadata?.atr !== undefined && (
                      <Box sx={{ mt: 1, pt: 1, borderTop: "1px solid rgba(255,255,255,0.1)" }}>
                        <Typography variant="caption" color="text.secondary" fontWeight="bold" sx={{ display: "block", mb: 0.5 }}>
                          Risk Management (ATR-based):
                        </Typography>
                        <Stack direction="row" spacing={2}>
                          <Box>
                            <Typography variant="caption" color="text.secondary">ATR</Typography>
                            <Typography variant="body2" fontWeight="bold">${trade.metadata.atr.toFixed(2)}</Typography>
                          </Box>
                          {trade.metadata.stop_loss && (
                            <Box>
                              <Typography variant="caption" color="text.secondary">Stop Loss</Typography>
                              <Typography variant="body2" fontWeight="bold" color="error.main">
                                ${trade.metadata.stop_loss.toFixed(2)}
                              </Typography>
                            </Box>
                          )}
                          {trade.metadata.take_profit && (
                            <Box>
                              <Typography variant="caption" color="text.secondary">Take Profit</Typography>
                              <Typography variant="body2" fontWeight="bold" color="success.main">
                                ${trade.metadata.take_profit.toFixed(2)}
                              </Typography>
                            </Box>
                          )}
                        </Stack>
                        {trade.metadata.power_hour && (
                          <Chip
                            label="POWER HOUR SIGNAL"
                            size="small"
                            color="warning"
                            sx={{ mt: 1, height: 18, fontSize: "0.6rem" }}
                          />
                        )}
                      </Box>
                    )}
                  </Box>
                );
              })}
            </Stack>
          </Box>
        )}

        {/* No Activity */}
        {recentTrades.length === 0 && !lastScan && (
          <Box
            sx={{
              p: 4,
              textAlign: "center",
              borderRadius: 2,
              bgcolor: "rgba(255,255,255,0.02)",
              border: "1px dashed rgba(255,255,255,0.1)"
            }}
          >
            <Psychology sx={{ fontSize: 48, color: "text.secondary", mb: 1 }} />
            <Typography variant="body2" color="text.secondary">
              No bot activity yet. Enable the autonomous engine to start trading.
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default BotThinkingProcess;
