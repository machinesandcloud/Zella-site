import { useEffect, useState, useRef, useCallback } from "react";
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
  Paper,
  LinearProgress,
  Tooltip,
  Badge,
  Divider,
  ToggleButton,
  ToggleButtonGroup,
  IconButton
} from "@mui/material";
import {
  CheckCircle,
  Cancel,
  TrendingUp,
  TrendingDown,
  Wifi,
  WifiOff,
  FilterList,
  Speed,
  Visibility,
  VisibilityOff,
  ExpandMore,
  ExpandLess,
  Radar,
  GpsFixed,
  Star,
  StarBorder
} from "@mui/icons-material";

interface StockEvaluation {
  symbol: string;
  passed: boolean;
  filters: Record<string, { passed: boolean; value?: number }>;
  scores?: {
    ml_score: number;
    momentum_score: number;
    combined_score: number;
  };
  data: {
    price: number;
    volume: number;
    relative_volume: number;
  };
}

interface ScannerResult {
  symbol: string;
  combined_score: number;
  ml_score: number;
  momentum_score: number;
  price: number;
  relative_volume: number;
  atr: number;
  atr_percent: number;
  pattern: string | null;
  news_catalyst: string | null;
  float_millions: number | null;
}

interface AnalyzedOpportunity {
  symbol: string;
  price: number;
  signals: string[];
  final_action: string;
  aggregate_confidence: number;
  num_strategies: number;
  strategies: string[];
  reasoning: string;
  ml_score: number;
  momentum_score: number;
  combined_score: number;
  relative_volume: number;
  atr: number;
  pattern: string | null;
}

interface FilterSummary {
  total: number;
  passed: number;
  failed_data: number;
  failed_volume: number;
  failed_price: number;
  failed_volatility: number;
  failed_rvol: number;
}

interface BotActivityMessage {
  channel: string;
  type: string;
  activity?: {
    analyzed_opportunities: AnalyzedOpportunity[];
    scanner_results: ScannerResult[];
    all_evaluations: StockEvaluation[];
    filter_summary?: FilterSummary;
  };
  timestamp: string;
}

const BotStockAnalysisLive = () => {
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [evaluations, setEvaluations] = useState<StockEvaluation[]>([]);
  const [scannerResults, setScannerResults] = useState<ScannerResult[]>([]);
  const [opportunities, setOpportunities] = useState<AnalyzedOpportunity[]>([]);
  const [filterSummary, setFilterSummary] = useState<FilterSummary | null>(null);
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"leveraged" | "passed" | "all">("leveraged");
  const [showAllEvaluations, setShowAllEvaluations] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const getWebSocketUrl = useCallback(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = import.meta.env.VITE_API_URL?.replace(/^https?:\/\//, "") || "localhost:8000";
    return `${protocol}//${host}/ws/bot-activity`;
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setConnecting(true);

    try {
      const ws = new WebSocket(getWebSocketUrl());

      ws.onopen = () => {
        setConnected(true);
        setConnecting(false);
      };

      ws.onmessage = (event) => {
        try {
          const message: BotActivityMessage = JSON.parse(event.data);

          if (message.type === "bot_activity" && message.activity) {
            const { analyzed_opportunities, scanner_results, all_evaluations, filter_summary } = message.activity;

            if (analyzed_opportunities) setOpportunities(analyzed_opportunities);
            if (scanner_results) setScannerResults(scanner_results);
            if (all_evaluations) setEvaluations(all_evaluations);
            if (filter_summary) setFilterSummary(filter_summary);

            setLastUpdate(message.timestamp);
          }
        } catch (e) {
          console.error("Error parsing bot activity message:", e);
        }
      };

      ws.onerror = () => {
        setConnected(false);
        setConnecting(false);
      };

      ws.onclose = () => {
        setConnected(false);
        setConnecting(false);
        reconnectTimeoutRef.current = setTimeout(connect, 3000);
      };

      wsRef.current = ws;
    } catch (e) {
      setConnecting(false);
    }
  }, [getWebSocketUrl]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnected(false);
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, []);

  const passedCount = evaluations.filter(e => e.passed).length;
  const leveragedCount = opportunities.length;

  const formatVolume = (volume: number) => {
    if (volume >= 1000000) return `${(volume / 1000000).toFixed(1)}M`;
    if (volume >= 1000) return `${(volume / 1000).toFixed(1)}K`;
    return volume?.toFixed(0) || "-";
  };

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        {/* Header */}
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 2 }}>
          <Stack direction="row" alignItems="center" spacing={2}>
            <Radar sx={{ fontSize: 28, color: "primary.main" }} />
            <Box>
              <Stack direction="row" alignItems="center" spacing={1}>
                <Typography variant="h6" fontWeight="bold">
                  Bot Stock Analysis
                </Typography>
                <Badge
                  badgeContent={connected ? "LIVE" : "OFF"}
                  color={connected ? "success" : "error"}
                  sx={{
                    "& .MuiBadge-badge": {
                      fontSize: "0.6rem",
                      height: 16,
                      minWidth: 32,
                    },
                  }}
                />
              </Stack>
              <Typography variant="body2" color="text.secondary">
                Real-time view of all stocks being analyzed by the bot
              </Typography>
            </Box>
          </Stack>

          <Stack direction="row" spacing={1} alignItems="center">
            {connected ? (
              <Chip
                icon={<Wifi />}
                label="Connected"
                color="success"
                size="small"
                sx={{ animation: "pulse 2s infinite" }}
              />
            ) : connecting ? (
              <Chip icon={<Speed />} label="Connecting..." color="warning" size="small" />
            ) : (
              <Chip
                icon={<WifiOff />}
                label="Disconnected"
                color="error"
                size="small"
                onClick={connect}
                sx={{ cursor: "pointer" }}
              />
            )}
          </Stack>
        </Stack>

        {/* Summary Stats */}
        {filterSummary && (
          <Box
            sx={{
              mb: 2,
              p: 2,
              borderRadius: 2,
              bgcolor: "rgba(255,255,255,0.02)",
              border: "1px solid rgba(255,255,255,0.06)",
            }}
          >
            <Stack direction="row" spacing={3} alignItems="center" flexWrap="wrap" gap={1}>
              <Box sx={{ textAlign: "center" }}>
                <Typography variant="h5" fontWeight="bold" color="primary.main">
                  {filterSummary.total}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Scanned
                </Typography>
              </Box>
              <TrendingDown sx={{ color: "error.main", fontSize: 20 }} />
              <Box sx={{ textAlign: "center" }}>
                <Typography variant="body1" fontWeight="bold" color="error.main">
                  {filterSummary.total - filterSummary.passed}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Filtered Out
                </Typography>
              </Box>
              <TrendingUp sx={{ color: "success.main", fontSize: 20 }} />
              <Box
                sx={{
                  textAlign: "center",
                  p: 1,
                  borderRadius: 1,
                  bgcolor: "rgba(46, 125, 50, 0.1)",
                }}
              >
                <Typography variant="h5" fontWeight="bold" color="success.main">
                  {filterSummary.passed}
                </Typography>
                <Typography variant="caption" color="success.main">
                  Passed Filters
                </Typography>
              </Box>
              <GpsFixed sx={{ color: "warning.main", fontSize: 20 }} />
              <Box
                sx={{
                  textAlign: "center",
                  p: 1,
                  borderRadius: 1,
                  bgcolor: "rgba(255, 152, 0, 0.1)",
                }}
              >
                <Typography variant="h5" fontWeight="bold" color="warning.main">
                  {leveragedCount}
                </Typography>
                <Typography variant="caption" color="warning.main">
                  Being Leveraged
                </Typography>
              </Box>
            </Stack>
          </Box>
        )}

        {/* View Mode Toggle */}
        <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }}>
          <ToggleButtonGroup
            value={viewMode}
            exclusive
            onChange={(_, v) => v && setViewMode(v)}
            size="small"
          >
            <ToggleButton value="leveraged">
              <Badge badgeContent={leveragedCount} color="warning" max={99}>
                <Star sx={{ mr: 1, color: "warning.main" }} />
                Leveraged
              </Badge>
            </ToggleButton>
            <ToggleButton value="passed">
              <Badge badgeContent={passedCount} color="success" max={99}>
                <CheckCircle sx={{ mr: 1, color: "success.main" }} />
                Passed
              </Badge>
            </ToggleButton>
            <ToggleButton value="all">
              <Badge badgeContent={evaluations.length} color="primary" max={999}>
                <FilterList sx={{ mr: 1 }} />
                All
              </Badge>
            </ToggleButton>
          </ToggleButtonGroup>

          {viewMode === "all" && (
            <IconButton size="small" onClick={() => setShowAllEvaluations(!showAllEvaluations)}>
              {showAllEvaluations ? <VisibilityOff /> : <Visibility />}
            </IconButton>
          )}
        </Stack>

        <Divider sx={{ mb: 2 }} />

        {connecting && <LinearProgress sx={{ mb: 2 }} />}

        {/* Leveraged Stocks View - Stocks the bot is actively analyzing/trading */}
        {viewMode === "leveraged" && (
          <>
            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
              Stocks the bot is actively analyzing for trades
            </Typography>
            {opportunities.length > 0 ? (
              <TableContainer component={Paper} sx={{ bgcolor: "transparent", maxHeight: 350 }}>
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: "bold", bgcolor: "background.paper" }}>Symbol</TableCell>
                      <TableCell align="right" sx={{ fontWeight: "bold", bgcolor: "background.paper" }}>Price</TableCell>
                      <TableCell align="center" sx={{ fontWeight: "bold", bgcolor: "background.paper" }}>Action</TableCell>
                      <TableCell align="right" sx={{ fontWeight: "bold", bgcolor: "background.paper" }}>Score</TableCell>
                      <TableCell align="right" sx={{ fontWeight: "bold", bgcolor: "background.paper" }}>Confidence</TableCell>
                      <TableCell align="right" sx={{ fontWeight: "bold", bgcolor: "background.paper" }}>Strategies</TableCell>
                      <TableCell sx={{ fontWeight: "bold", bgcolor: "background.paper" }}>Signals</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {opportunities.map((opp, idx) => (
                      <TableRow
                        key={opp.symbol}
                        sx={{
                          bgcolor:
                            opp.final_action === "BUY"
                              ? "rgba(46, 125, 50, 0.08)"
                              : opp.final_action === "SELL"
                              ? "rgba(211, 47, 47, 0.08)"
                              : "transparent",
                          "&:hover": { bgcolor: "rgba(255,255,255,0.05)" },
                        }}
                      >
                        <TableCell>
                          <Stack direction="row" alignItems="center" spacing={1}>
                            {idx < 3 && <Star sx={{ fontSize: 14, color: "warning.main" }} />}
                            <Typography fontWeight="bold">{opp.symbol}</Typography>
                            {opp.pattern && (
                              <Chip
                                label={opp.pattern.replace("_", " ")}
                                size="small"
                                color="success"
                                sx={{ height: 16, fontSize: "0.55rem" }}
                              />
                            )}
                          </Stack>
                        </TableCell>
                        <TableCell align="right">${opp.price?.toFixed(2)}</TableCell>
                        <TableCell align="center">
                          <Chip
                            label={opp.final_action}
                            size="small"
                            color={
                              opp.final_action === "BUY"
                                ? "success"
                                : opp.final_action === "SELL"
                                ? "error"
                                : "default"
                            }
                            sx={{ height: 20, minWidth: 50 }}
                          />
                        </TableCell>
                        <TableCell align="right">
                          <Stack direction="row" alignItems="center" justifyContent="flex-end" spacing={1}>
                            <LinearProgress
                              variant="determinate"
                              value={Math.min((opp.combined_score || 0) * 100, 100)}
                              sx={{
                                width: 40,
                                height: 5,
                                borderRadius: 2,
                                bgcolor: "rgba(255,255,255,0.1)",
                                "& .MuiLinearProgress-bar": {
                                  borderRadius: 2,
                                  bgcolor:
                                    (opp.combined_score || 0) > 0.5 ? "success.main" : "warning.main",
                                },
                              }}
                            />
                            <Typography variant="caption" fontWeight="bold">
                              {((opp.combined_score || 0) * 100).toFixed(0)}%
                            </Typography>
                          </Stack>
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="caption">
                            {((opp.aggregate_confidence || 0) * 100).toFixed(0)}%
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Tooltip title={opp.strategies?.join(", ") || "N/A"}>
                            <Chip
                              label={`${opp.num_strategies || 0} active`}
                              size="small"
                              sx={{ height: 18, fontSize: "0.6rem" }}
                            />
                          </Tooltip>
                        </TableCell>
                        <TableCell>
                          <Stack direction="row" spacing={0.5} flexWrap="wrap">
                            {opp.signals?.slice(0, 2).map((signal, i) => (
                              <Chip
                                key={i}
                                label={signal}
                                size="small"
                                variant="outlined"
                                sx={{ height: 16, fontSize: "0.5rem" }}
                              />
                            ))}
                            {(opp.signals?.length || 0) > 2 && (
                              <Chip
                                label={`+${opp.signals.length - 2}`}
                                size="small"
                                sx={{ height: 16, fontSize: "0.5rem" }}
                              />
                            )}
                          </Stack>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Box sx={{ textAlign: "center", py: 4 }}>
                <StarBorder sx={{ fontSize: 48, color: "text.secondary", mb: 1 }} />
                <Typography variant="body2" color="text.secondary">
                  No stocks currently being leveraged. The bot will identify opportunities during market hours.
                </Typography>
              </Box>
            )}
          </>
        )}

        {/* Passed Stocks View - Stocks that passed all filters */}
        {viewMode === "passed" && (
          <>
            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
              Stocks that passed all screening criteria
            </Typography>
            {scannerResults.length > 0 ? (
              <TableContainer component={Paper} sx={{ bgcolor: "transparent", maxHeight: 350 }}>
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: "bold", bgcolor: "background.paper" }}>#</TableCell>
                      <TableCell sx={{ fontWeight: "bold", bgcolor: "background.paper" }}>Symbol</TableCell>
                      <TableCell align="right" sx={{ fontWeight: "bold", bgcolor: "background.paper" }}>Price</TableCell>
                      <TableCell align="right" sx={{ fontWeight: "bold", bgcolor: "background.paper" }}>Score</TableCell>
                      <TableCell align="right" sx={{ fontWeight: "bold", bgcolor: "background.paper" }}>ML</TableCell>
                      <TableCell align="right" sx={{ fontWeight: "bold", bgcolor: "background.paper" }}>RVol</TableCell>
                      <TableCell align="right" sx={{ fontWeight: "bold", bgcolor: "background.paper" }}>ATR%</TableCell>
                      <TableCell sx={{ fontWeight: "bold", bgcolor: "background.paper" }}>Pattern</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {scannerResults.map((result, idx) => (
                      <TableRow key={result.symbol} hover>
                        <TableCell>
                          <Chip
                            label={idx + 1}
                            size="small"
                            color={idx === 0 ? "success" : idx < 3 ? "warning" : "default"}
                            sx={{ height: 18, minWidth: 22 }}
                          />
                        </TableCell>
                        <TableCell>
                          <Typography fontWeight="bold">{result.symbol}</Typography>
                        </TableCell>
                        <TableCell align="right">${result.price?.toFixed(2)}</TableCell>
                        <TableCell align="right">
                          <Typography
                            fontWeight="bold"
                            color={
                              result.combined_score > 0.5
                                ? "success.main"
                                : result.combined_score > 0.3
                                ? "warning.main"
                                : "text.primary"
                            }
                          >
                            {((result.combined_score || 0) * 100).toFixed(0)}%
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          {((result.ml_score || 0) * 100).toFixed(0)}%
                        </TableCell>
                        <TableCell align="right">
                          <Typography
                            fontWeight={result.relative_volume >= 3 ? "bold" : "normal"}
                            color={result.relative_volume >= 3 ? "warning.main" : "inherit"}
                          >
                            {result.relative_volume?.toFixed(1)}x
                          </Typography>
                        </TableCell>
                        <TableCell align="right">{result.atr_percent?.toFixed(1)}%</TableCell>
                        <TableCell>
                          {result.pattern && (
                            <Chip
                              label={result.pattern.replace("_", " ")}
                              size="small"
                              color="success"
                              sx={{ height: 16, fontSize: "0.55rem" }}
                            />
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Box sx={{ textAlign: "center", py: 4 }}>
                <CheckCircle sx={{ fontSize: 48, color: "text.secondary", mb: 1 }} />
                <Typography variant="body2" color="text.secondary">
                  No stocks have passed all filters yet. Start the autonomous engine to begin scanning.
                </Typography>
              </Box>
            )}
          </>
        )}

        {/* All Evaluations View - Shows pass/fail status for every stock */}
        {viewMode === "all" && (
          <>
            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
              Complete evaluation status for all scanned stocks
            </Typography>
            {evaluations.length > 0 ? (
              <TableContainer component={Paper} sx={{ bgcolor: "transparent", maxHeight: showAllEvaluations ? 600 : 300 }}>
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: "bold", bgcolor: "background.paper" }}>Symbol</TableCell>
                      <TableCell sx={{ fontWeight: "bold", bgcolor: "background.paper" }}>Status</TableCell>
                      <TableCell align="right" sx={{ fontWeight: "bold", bgcolor: "background.paper" }}>Price</TableCell>
                      <TableCell align="right" sx={{ fontWeight: "bold", bgcolor: "background.paper" }}>Volume</TableCell>
                      <TableCell align="right" sx={{ fontWeight: "bold", bgcolor: "background.paper" }}>RVol</TableCell>
                      <TableCell sx={{ fontWeight: "bold", bgcolor: "background.paper" }}>Filters</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {evaluations.map((evaluation) => (
                      <TableRow
                        key={evaluation.symbol}
                        sx={{
                          bgcolor: evaluation.passed
                            ? "rgba(46, 125, 50, 0.05)"
                            : "rgba(244, 67, 54, 0.03)",
                          "&:hover": {
                            bgcolor: evaluation.passed
                              ? "rgba(46, 125, 50, 0.1)"
                              : "rgba(244, 67, 54, 0.08)",
                          },
                        }}
                      >
                        <TableCell>
                          <Typography fontWeight={evaluation.passed ? "bold" : "normal"}>
                            {evaluation.symbol}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip
                            icon={evaluation.passed ? <CheckCircle /> : <Cancel />}
                            label={evaluation.passed ? "PASS" : "FAIL"}
                            size="small"
                            color={evaluation.passed ? "success" : "error"}
                            sx={{ height: 20 }}
                          />
                        </TableCell>
                        <TableCell align="right">
                          ${evaluation.data?.price?.toFixed(2) || "-"}
                        </TableCell>
                        <TableCell align="right">
                          {formatVolume(evaluation.data?.volume || 0)}
                        </TableCell>
                        <TableCell align="right">
                          <Typography
                            color={
                              evaluation.data?.relative_volume >= 2
                                ? "warning.main"
                                : "text.secondary"
                            }
                            fontWeight={
                              evaluation.data?.relative_volume >= 2 ? "bold" : "normal"
                            }
                          >
                            {evaluation.data?.relative_volume?.toFixed(1) || "-"}x
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Stack direction="row" spacing={0.5}>
                            {Object.entries(evaluation.filters || {}).map(([key, filter]) => (
                              <Tooltip key={key} title={`${key}: ${filter.passed ? "passed" : "failed"}`}>
                                {filter.passed ? (
                                  <CheckCircle sx={{ fontSize: 14, color: "success.main" }} />
                                ) : (
                                  <Cancel sx={{ fontSize: 14, color: "error.main" }} />
                                )}
                              </Tooltip>
                            ))}
                          </Stack>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Box sx={{ textAlign: "center", py: 4 }}>
                <FilterList sx={{ fontSize: 48, color: "text.secondary", mb: 1 }} />
                <Typography variant="body2" color="text.secondary">
                  No stocks evaluated yet. Start the autonomous engine to begin scanning.
                </Typography>
              </Box>
            )}

            {evaluations.length > 10 && (
              <Box sx={{ textAlign: "center", mt: 1 }}>
                <IconButton size="small" onClick={() => setShowAllEvaluations(!showAllEvaluations)}>
                  {showAllEvaluations ? <ExpandLess /> : <ExpandMore />}
                </IconButton>
                <Typography variant="caption" color="text.secondary">
                  {showAllEvaluations ? "Show less" : `Show all ${evaluations.length} stocks`}
                </Typography>
              </Box>
            )}
          </>
        )}

        {/* Footer */}
        <Box sx={{ mt: 2, pt: 1, borderTop: "1px solid rgba(255,255,255,0.06)" }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Typography variant="caption" color="text.secondary">
              {evaluations.length} stocks scanned | {passedCount} passed | {leveragedCount} leveraged
            </Typography>
            {lastUpdate && (
              <Typography variant="caption" color="text.secondary">
                Last update: {new Date(lastUpdate).toLocaleTimeString()}
              </Typography>
            )}
          </Stack>
        </Box>
      </CardContent>
    </Card>
  );
};

export default BotStockAnalysisLive;
