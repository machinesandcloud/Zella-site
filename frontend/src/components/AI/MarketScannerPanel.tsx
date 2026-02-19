import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  Typography,
  Box,
  Stack,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  LinearProgress,
  IconButton,
  Tooltip,
  Collapse,
  Paper,
  Alert,
  Divider
} from "@mui/material";
import {
  Refresh,
  TrendingUp,
  TrendingDown,
  AccessTime,
  Whatshot,
  ShowChart,
  ExpandMore,
  ExpandLess,
  Newspaper,
  Speed,
  Assessment
} from "@mui/icons-material";
import { getAutonomousStatus } from "../../services/api";

interface ScannerResult {
  symbol: string;
  ml_score: number;
  momentum_score: number;
  combined_score: number;
  last_price: number;
  relative_volume: number;
  float_millions: number | null;
  float_score: number;
  atr: number;
  atr_percent: number;
  pattern: string | null;
  pattern_score: number;
  news_catalyst: string | null;
  news_score: number;
  time_multiplier: number;
}

interface AnalyzedOpportunity {
  symbol: string;
  recommended_action: string;
  num_strategies: number;
  confidence: number;
  strategies: string[];
  reasoning: string;
  ml_score: number;
  momentum_score: number;
  combined_score: number;
  last_price: number;
  relative_volume: number;
  pattern: string | null;
  news_catalyst: string | null;
  atr: number;
}

interface ScannerStatus {
  enabled: boolean;
  running: boolean;
  symbols_scanned: number;
  scanner_results: ScannerResult[];
  analyzed_opportunities: AnalyzedOpportunity[];
  power_hour: {
    active: boolean;
    multiplier: number;
  };
  scoring_weights: Record<string, number>;
  last_scan: string | null;
}

const MarketScannerPanel = () => {
  const [status, setStatus] = useState<ScannerStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [showAnalyzed, setShowAnalyzed] = useState(true);

  const load = async () => {
    setRefreshing(true);
    try {
      const data = await getAutonomousStatus();
      setStatus(data);
    } catch (error) {
      console.error("Error loading scanner status:", error);
    } finally {
      setRefreshing(false);
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 5000);
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
          <Alert severity="info">
            Backend not connected. Start the backend to see scanner data.
          </Alert>
        </CardContent>
      </Card>
    );
  }

  const formatScore = (score: number, maxScore: number = 1) => {
    const percentage = (score / maxScore) * 100;
    return (
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <LinearProgress
          variant="determinate"
          value={Math.min(percentage, 100)}
          sx={{
            width: 60,
            height: 6,
            borderRadius: 3,
            bgcolor: "rgba(255,255,255,0.1)",
            "& .MuiLinearProgress-bar": {
              borderRadius: 3,
              background:
                percentage > 70
                  ? "linear-gradient(90deg, #4caf50, #81c784)"
                  : percentage > 40
                  ? "linear-gradient(90deg, #ff9800, #ffb74d)"
                  : "linear-gradient(90deg, #f44336, #e57373)"
            }
          }}
        />
        <Typography variant="caption" sx={{ minWidth: 35 }}>
          {(score * 100).toFixed(0)}%
        </Typography>
      </Box>
    );
  };

  const getPatternChip = (pattern: string | null) => {
    if (!pattern) return null;
    const colors: Record<string, "success" | "warning" | "info"> = {
      BULL_FLAG: "success",
      FLAT_TOP: "info",
    };
    return (
      <Chip
        icon={<ShowChart />}
        label={pattern.replace(/_/g, " ")}
        size="small"
        color={colors[pattern] || "default"}
        sx={{ height: 22, fontSize: "0.65rem" }}
      />
    );
  };

  const getCatalystChip = (catalyst: string | null) => {
    if (!catalyst) return null;
    const colors: Record<string, "error" | "warning" | "success" | "info"> = {
      EARNINGS: "warning",
      FDA: "error",
      "M&A": "success",
      ANALYST: "info",
    };
    return (
      <Chip
        icon={<Newspaper />}
        label={catalyst}
        size="small"
        color={colors[catalyst] || "default"}
        sx={{ height: 22, fontSize: "0.65rem" }}
      />
    );
  };

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        {/* Header */}
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
          <Box>
            <Stack direction="row" alignItems="center" spacing={1}>
              <Assessment sx={{ fontSize: 28, color: "primary.main" }} />
              <Typography variant="h6" fontWeight="bold">
                Market Scanner Analysis
              </Typography>
            </Stack>
            <Typography variant="body2" color="text.secondary">
              Real-time stock evaluation with Warrior Trading criteria
            </Typography>
          </Box>
          <Stack direction="row" spacing={1} alignItems="center">
            {status.power_hour?.active && (
              <Chip
                icon={<Whatshot />}
                label={`POWER HOUR (${status.power_hour.multiplier}x)`}
                color="warning"
                size="small"
                sx={{ animation: "pulse 2s infinite" }}
              />
            )}
            <Chip
              label={`${status.symbols_scanned} Scanned`}
              size="small"
              color="primary"
            />
            <Tooltip title="Refresh">
              <IconButton size="small" onClick={load} disabled={refreshing}>
                <Refresh className={refreshing ? "rotating" : ""} />
              </IconButton>
            </Tooltip>
          </Stack>
        </Stack>

        {/* Last Scan Time */}
        {status.last_scan && (
          <Box sx={{ mb: 2 }}>
            <Stack direction="row" alignItems="center" spacing={1}>
              <AccessTime sx={{ fontSize: 16, color: "text.secondary" }} />
              <Typography variant="caption" color="text.secondary">
                Last scan: {new Date(status.last_scan).toLocaleTimeString()}
              </Typography>
            </Stack>
          </Box>
        )}

        {/* Scoring Weights Legend */}
        {status.scoring_weights && (
          <Box sx={{ mb: 3, p: 2, borderRadius: 2, bgcolor: "rgba(255,255,255,0.02)" }}>
            <Typography variant="caption" fontWeight="bold" sx={{ display: "block", mb: 1 }}>
              Scoring Weights (Warrior Trading Aligned):
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" gap={1}>
              {Object.entries(status.scoring_weights).map(([key, weight]) => (
                <Chip
                  key={key}
                  label={`${key.replace(/_/g, " ")}: ${(weight * 100).toFixed(0)}%`}
                  size="small"
                  sx={{ fontSize: "0.6rem", height: 20, bgcolor: "rgba(255,255,255,0.05)" }}
                />
              ))}
            </Stack>
          </Box>
        )}

        {/* Toggle for Analyzed vs Raw Results */}
        <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
          <Chip
            label="Strategy Analyzed"
            onClick={() => setShowAnalyzed(true)}
            color={showAnalyzed ? "primary" : "default"}
            variant={showAnalyzed ? "filled" : "outlined"}
            sx={{ cursor: "pointer" }}
          />
          <Chip
            label="Raw Scanner"
            onClick={() => setShowAnalyzed(false)}
            color={!showAnalyzed ? "primary" : "default"}
            variant={!showAnalyzed ? "filled" : "outlined"}
            sx={{ cursor: "pointer" }}
          />
        </Stack>

        <Divider sx={{ mb: 2 }} />

        {/* Analyzed Opportunities Table */}
        {showAnalyzed && (
          <>
            <Typography variant="subtitle2" fontWeight="bold" sx={{ mb: 2 }}>
              Top Opportunities (Strategy Consensus)
            </Typography>
            {status.analyzed_opportunities?.length > 0 ? (
              <TableContainer component={Paper} sx={{ bgcolor: "transparent", maxHeight: 400 }}>
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: "bold" }}>Symbol</TableCell>
                      <TableCell sx={{ fontWeight: "bold" }}>Action</TableCell>
                      <TableCell sx={{ fontWeight: "bold" }}>Strategies</TableCell>
                      <TableCell sx={{ fontWeight: "bold" }}>Confidence</TableCell>
                      <TableCell sx={{ fontWeight: "bold" }}>Price</TableCell>
                      <TableCell sx={{ fontWeight: "bold" }}>Details</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {status.analyzed_opportunities.map((opp) => (
                      <>
                        <TableRow
                          key={opp.symbol}
                          hover
                          onClick={() => setExpandedRow(expandedRow === opp.symbol ? null : opp.symbol)}
                          sx={{ cursor: "pointer" }}
                        >
                          <TableCell>
                            <Stack direction="row" alignItems="center" spacing={1}>
                              <Typography fontWeight="bold">{opp.symbol}</Typography>
                              {opp.pattern && getPatternChip(opp.pattern)}
                              {opp.news_catalyst && getCatalystChip(opp.news_catalyst)}
                            </Stack>
                          </TableCell>
                          <TableCell>
                            <Chip
                              icon={opp.recommended_action === "BUY" ? <TrendingUp /> : <TrendingDown />}
                              label={opp.recommended_action}
                              size="small"
                              color={opp.recommended_action === "BUY" ? "success" : "error"}
                              sx={{ height: 24 }}
                            />
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={`${opp.num_strategies} agree`}
                              size="small"
                              color={opp.num_strategies >= 3 ? "success" : opp.num_strategies >= 2 ? "warning" : "default"}
                              sx={{ height: 20, fontSize: "0.65rem" }}
                            />
                          </TableCell>
                          <TableCell>{formatScore(opp.confidence)}</TableCell>
                          <TableCell>${opp.last_price?.toFixed(2)}</TableCell>
                          <TableCell>
                            <IconButton size="small">
                              {expandedRow === opp.symbol ? <ExpandLess /> : <ExpandMore />}
                            </IconButton>
                          </TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell colSpan={6} sx={{ py: 0 }}>
                            <Collapse in={expandedRow === opp.symbol}>
                              <Box sx={{ p: 2, bgcolor: "rgba(255,255,255,0.02)", borderRadius: 1, my: 1 }}>
                                <Typography variant="caption" fontWeight="bold" sx={{ display: "block", mb: 1 }}>
                                  Reasoning:
                                </Typography>
                                <Typography variant="body2" sx={{ mb: 2, fontStyle: "italic" }}>
                                  {opp.reasoning || "No specific reasoning available"}
                                </Typography>
                                <Typography variant="caption" fontWeight="bold" sx={{ display: "block", mb: 1 }}>
                                  Strategies Agreeing:
                                </Typography>
                                <Stack direction="row" spacing={0.5} flexWrap="wrap" gap={0.5} sx={{ mb: 2 }}>
                                  {opp.strategies?.map((strat, idx) => (
                                    <Chip
                                      key={idx}
                                      label={strat.replace(/_/g, " ")}
                                      size="small"
                                      sx={{ height: 18, fontSize: "0.6rem" }}
                                    />
                                  ))}
                                </Stack>
                                <Stack direction="row" spacing={3}>
                                  <Box>
                                    <Typography variant="caption" color="text.secondary">ML Score</Typography>
                                    <Typography variant="body2" fontWeight="bold">{(opp.ml_score * 100).toFixed(0)}%</Typography>
                                  </Box>
                                  <Box>
                                    <Typography variant="caption" color="text.secondary">Momentum</Typography>
                                    <Typography variant="body2" fontWeight="bold">{(opp.momentum_score * 100).toFixed(1)}%</Typography>
                                  </Box>
                                  <Box>
                                    <Typography variant="caption" color="text.secondary">Rel. Volume</Typography>
                                    <Typography variant="body2" fontWeight="bold">{opp.relative_volume?.toFixed(1)}x</Typography>
                                  </Box>
                                  <Box>
                                    <Typography variant="caption" color="text.secondary">ATR</Typography>
                                    <Typography variant="body2" fontWeight="bold">${opp.atr?.toFixed(2)}</Typography>
                                  </Box>
                                </Stack>
                              </Box>
                            </Collapse>
                          </TableCell>
                        </TableRow>
                      </>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Alert severity="info" icon={<Speed />}>
                No opportunities found yet. The bot is scanning for stocks matching Warrior Trading criteria.
              </Alert>
            )}
          </>
        )}

        {/* Raw Scanner Results Table */}
        {!showAnalyzed && (
          <>
            <Typography variant="subtitle2" fontWeight="bold" sx={{ mb: 2 }}>
              Raw Scanner Output (Top 20 by Combined Score)
            </Typography>
            {status.scanner_results?.length > 0 ? (
              <TableContainer component={Paper} sx={{ bgcolor: "transparent", maxHeight: 400 }}>
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: "bold" }}>Symbol</TableCell>
                      <TableCell sx={{ fontWeight: "bold" }}>Combined</TableCell>
                      <TableCell sx={{ fontWeight: "bold" }}>ML</TableCell>
                      <TableCell sx={{ fontWeight: "bold" }}>Momentum</TableCell>
                      <TableCell sx={{ fontWeight: "bold" }}>Float</TableCell>
                      <TableCell sx={{ fontWeight: "bold" }}>RVol</TableCell>
                      <TableCell sx={{ fontWeight: "bold" }}>ATR%</TableCell>
                      <TableCell sx={{ fontWeight: "bold" }}>Pattern</TableCell>
                      <TableCell sx={{ fontWeight: "bold" }}>News</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {status.scanner_results.map((result) => (
                      <TableRow key={result.symbol} hover>
                        <TableCell>
                          <Stack direction="row" alignItems="center" spacing={1}>
                            <Typography fontWeight="bold">{result.symbol}</Typography>
                            <Typography variant="caption" color="text.secondary">
                              ${result.last_price}
                            </Typography>
                          </Stack>
                        </TableCell>
                        <TableCell>{formatScore(result.combined_score)}</TableCell>
                        <TableCell>{formatScore(result.ml_score)}</TableCell>
                        <TableCell>
                          <Typography
                            variant="body2"
                            color={result.momentum_score > 0 ? "success.main" : "error.main"}
                          >
                            {(result.momentum_score * 100).toFixed(1)}%
                          </Typography>
                        </TableCell>
                        <TableCell>
                          {result.float_millions ? (
                            <Chip
                              label={`${result.float_millions}M`}
                              size="small"
                              color={result.float_millions < 50 ? "warning" : result.float_millions < 100 ? "default" : "default"}
                              sx={{ height: 20, fontSize: "0.6rem" }}
                            />
                          ) : (
                            "-"
                          )}
                        </TableCell>
                        <TableCell>
                          <Typography
                            variant="body2"
                            fontWeight={result.relative_volume >= 2 ? "bold" : "normal"}
                            color={result.relative_volume >= 2 ? "warning.main" : "text.primary"}
                          >
                            {result.relative_volume}x
                          </Typography>
                        </TableCell>
                        <TableCell>{result.atr_percent?.toFixed(1)}%</TableCell>
                        <TableCell>{getPatternChip(result.pattern) || "-"}</TableCell>
                        <TableCell>{getCatalystChip(result.news_catalyst) || "-"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Alert severity="info">
                No scanner results yet. Start the autonomous engine to begin scanning.
              </Alert>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
};

export default MarketScannerPanel;
