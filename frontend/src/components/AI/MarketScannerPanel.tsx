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
  Paper,
  Alert,
  Tabs,
  Tab,
  ToggleButton,
  ToggleButtonGroup,
  Badge,
  Divider,
  Button,
  CircularProgress
} from "@mui/material";
import {
  Refresh,
  CheckCircle,
  Cancel,
  TrendingUp,
  Whatshot,
  FilterList,
  Assessment,
  Speed,
  VolumeUp,
  AttachMoney,
  ShowChart,
  Newspaper,
  PlayArrow,
  AccessTime
} from "@mui/icons-material";
import { getAutonomousStatus, triggerManualScan } from "../../services/api";

interface FilterDetail {
  passed: boolean;
  value?: number | string;
  threshold?: number;
  reason?: string;
}

interface StockEvaluation {
  symbol: string;
  passed: boolean;
  rejection_reason: string | null;
  filters: {
    data_check?: FilterDetail;
    volume?: FilterDetail;
    price?: FilterDetail;
    volatility?: FilterDetail;
    relative_volume?: FilterDetail;
  };
  data: {
    price?: number;
    avg_volume?: number;
    last_volume?: number;
    relative_volume?: number;
    volatility?: number;
    float_millions?: number | null;
    atr?: number;
    atr_percent?: number;
    pattern?: string | null;
    news_catalyst?: string | null;
  };
  scores?: {
    ml_score: number;
    momentum_score: number;
    float_score: number;
    pattern_score: number;
    news_score: number;
    atr_score: number;
    time_multiplier: number;
    combined_score: number;
  };
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

interface ScannerStatus {
  enabled: boolean;
  running: boolean;
  symbols_scanned: number;
  all_evaluations: StockEvaluation[];
  filter_summary: FilterSummary;
  scanner_results: any[];
  active_strategies: string[];
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
  const [scanning, setScanning] = useState(false);
  const [viewTab, setViewTab] = useState(0);
  const [filterView, setFilterView] = useState<"all" | "passed" | "failed">("all");
  const [scanMessage, setScanMessage] = useState<string | null>(null);

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

  const handleManualScan = async () => {
    setScanning(true);
    setScanMessage(null);
    try {
      const result = await triggerManualScan();
      setScanMessage(`Scanned ${result.symbols_scanned} symbols, found ${result.opportunities_found} opportunities`);
      // Reload status to get fresh data
      await load();
    } catch (error: any) {
      setScanMessage(`Scan failed: ${error?.response?.data?.detail || error.message}`);
    } finally {
      setScanning(false);
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
          <Typography sx={{ mt: 2, textAlign: "center" }}>Loading scanner data...</Typography>
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

  const filteredEvaluations = status.all_evaluations?.filter(e => {
    if (filterView === "passed") return e.passed;
    if (filterView === "failed") return !e.passed;
    return true;
  }) || [];

  const passedCount = status.all_evaluations?.filter(e => e.passed).length || 0;
  const failedCount = status.all_evaluations?.filter(e => !e.passed).length || 0;

  const FilterIcon = ({ passed }: { passed: boolean }) => (
    passed ?
      <CheckCircle sx={{ fontSize: 14, color: "success.main" }} /> :
      <Cancel sx={{ fontSize: 14, color: "error.main" }} />
  );

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        {/* Header */}
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 2 }}>
          <Box>
            <Stack direction="row" alignItems="center" spacing={1}>
              <Assessment sx={{ fontSize: 28, color: "primary.main" }} />
              <Typography variant="h6" fontWeight="bold">
                Live Stock Evaluation Pipeline
              </Typography>
              {status.running && (
                <Chip
                  icon={<CircularProgress size={12} sx={{ color: "success.main" }} />}
                  label="LIVE"
                  color="success"
                  size="small"
                  sx={{ animation: "pulse 2s infinite" }}
                />
              )}
            </Stack>
            <Typography variant="body2" color="text.secondary">
              Real-time stock evaluation using Warrior Trading criteria
            </Typography>
          </Box>
          <Stack direction="row" spacing={1} alignItems="center">
            {status.power_hour?.active && (
              <Chip
                icon={<Whatshot />}
                label={`POWER HOUR ${status.power_hour.multiplier}x`}
                color="warning"
                size="small"
              />
            )}
            <Button
              variant="contained"
              color="primary"
              size="small"
              startIcon={scanning ? <CircularProgress size={16} color="inherit" /> : <PlayArrow />}
              onClick={handleManualScan}
              disabled={scanning}
              sx={{ minWidth: 120 }}
            >
              {scanning ? "Scanning..." : "Scan Now"}
            </Button>
            <Tooltip title="Refresh Status">
              <IconButton size="small" onClick={load} disabled={refreshing}>
                <Refresh className={refreshing ? "rotating" : ""} />
              </IconButton>
            </Tooltip>
          </Stack>
        </Stack>

        {/* Scan Result Message */}
        {scanMessage && (
          <Alert
            severity={scanMessage.includes("failed") ? "error" : "success"}
            onClose={() => setScanMessage(null)}
            sx={{ mb: 2 }}
          >
            {scanMessage}
          </Alert>
        )}

        {/* Filter Pipeline Summary */}
        {status.filter_summary && (
          <Box sx={{ mb: 3, p: 2, borderRadius: 2, bgcolor: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)" }}>
            <Typography variant="subtitle2" fontWeight="bold" sx={{ mb: 2 }}>
              Evaluation Pipeline Results
            </Typography>
            <Stack direction="row" spacing={2} flexWrap="wrap" gap={1}>
              <Box sx={{ textAlign: "center", minWidth: 80 }}>
                <Typography variant="h5" fontWeight="bold" color="primary.main">
                  {status.filter_summary.total}
                </Typography>
                <Typography variant="caption" color="text.secondary">Total Scanned</Typography>
              </Box>
              <Box sx={{ display: "flex", alignItems: "center", px: 2 }}>
                <Typography variant="h4" color="text.secondary">→</Typography>
              </Box>
              <Tooltip title="Failed: Insufficient price data">
                <Box sx={{ textAlign: "center", minWidth: 70 }}>
                  <Typography variant="body1" fontWeight="bold" color="error.main">
                    -{status.filter_summary.failed_data || 0}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">Data</Typography>
                </Box>
              </Tooltip>
              <Tooltip title="Failed: Average volume < 500K">
                <Box sx={{ textAlign: "center", minWidth: 70 }}>
                  <Typography variant="body1" fontWeight="bold" color="error.main">
                    -{status.filter_summary.failed_volume || 0}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">Volume</Typography>
                </Box>
              </Tooltip>
              <Tooltip title="Failed: Price outside $5-$1000 range">
                <Box sx={{ textAlign: "center", minWidth: 70 }}>
                  <Typography variant="body1" fontWeight="bold" color="error.main">
                    -{status.filter_summary.failed_price || 0}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">Price</Typography>
                </Box>
              </Tooltip>
              <Tooltip title="Failed: Volatility too low">
                <Box sx={{ textAlign: "center", minWidth: 70 }}>
                  <Typography variant="body1" fontWeight="bold" color="error.main">
                    -{status.filter_summary.failed_volatility || 0}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">Volatility</Typography>
                </Box>
              </Tooltip>
              <Tooltip title="Failed: Relative volume < 2x">
                <Box sx={{ textAlign: "center", minWidth: 70 }}>
                  <Typography variant="body1" fontWeight="bold" color="error.main">
                    -{status.filter_summary.failed_rvol || 0}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">RVol</Typography>
                </Box>
              </Tooltip>
              <Box sx={{ display: "flex", alignItems: "center", px: 2 }}>
                <Typography variant="h4" color="text.secondary">→</Typography>
              </Box>
              <Box sx={{ textAlign: "center", minWidth: 80, p: 1, borderRadius: 1, bgcolor: "rgba(46, 125, 50, 0.1)" }}>
                <Typography variant="h5" fontWeight="bold" color="success.main">
                  {status.filter_summary.passed}
                </Typography>
                <Typography variant="caption" color="success.main">Passed All</Typography>
              </Box>
            </Stack>
          </Box>
        )}

        {/* Tabs */}
        <Tabs value={viewTab} onChange={(_, v) => setViewTab(v)} sx={{ mb: 2 }}>
          <Tab
            label={
              <Stack direction="row" spacing={1} alignItems="center">
                <span>All Evaluations</span>
                <Chip label={status.all_evaluations?.length || 0} size="small" sx={{ height: 20 }} />
              </Stack>
            }
          />
          <Tab
            label={
              <Stack direction="row" spacing={1} alignItems="center">
                <span>Top Opportunities</span>
                <Chip label={passedCount} size="small" color="success" sx={{ height: 20 }} />
              </Stack>
            }
          />
          <Tab
            label={
              <Stack direction="row" spacing={1} alignItems="center">
                <span>Active Strategies</span>
                <Chip label={status.active_strategies?.length || 0} size="small" color="primary" sx={{ height: 20 }} />
              </Stack>
            }
          />
        </Tabs>

        <Divider sx={{ mb: 2 }} />

        {/* Tab 0: All Evaluations */}
        {viewTab === 0 && (
          <>
            <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
              <ToggleButtonGroup
                value={filterView}
                exclusive
                onChange={(_, v) => v && setFilterView(v)}
                size="small"
              >
                <ToggleButton value="all">
                  <Badge badgeContent={status.all_evaluations?.length || 0} color="primary" max={999}>
                    <FilterList sx={{ mr: 1 }} /> All
                  </Badge>
                </ToggleButton>
                <ToggleButton value="passed">
                  <Badge badgeContent={passedCount} color="success" max={999}>
                    <CheckCircle sx={{ mr: 1, color: "success.main" }} /> Passed
                  </Badge>
                </ToggleButton>
                <ToggleButton value="failed">
                  <Badge badgeContent={failedCount} color="error" max={999}>
                    <Cancel sx={{ mr: 1, color: "error.main" }} /> Failed
                  </Badge>
                </ToggleButton>
              </ToggleButtonGroup>
            </Stack>

            {filteredEvaluations.length > 0 ? (
              <TableContainer component={Paper} sx={{ bgcolor: "transparent", maxHeight: 500 }}>
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: "bold", minWidth: 80 }}>Symbol</TableCell>
                      <TableCell sx={{ fontWeight: "bold" }}>Status</TableCell>
                      <TableCell sx={{ fontWeight: "bold" }}>Price</TableCell>
                      <TableCell sx={{ fontWeight: "bold" }}>
                        <Tooltip title="Average Volume Filter (≥500K)">
                          <Stack direction="row" alignItems="center" spacing={0.5}>
                            <VolumeUp sx={{ fontSize: 14 }} />
                            <span>Vol</span>
                          </Stack>
                        </Tooltip>
                      </TableCell>
                      <TableCell sx={{ fontWeight: "bold" }}>
                        <Tooltip title="Price Filter ($5-$1000)">
                          <Stack direction="row" alignItems="center" spacing={0.5}>
                            <AttachMoney sx={{ fontSize: 14 }} />
                            <span>Price</span>
                          </Stack>
                        </Tooltip>
                      </TableCell>
                      <TableCell sx={{ fontWeight: "bold" }}>
                        <Tooltip title="Volatility Filter (≥0.5%)">
                          <Stack direction="row" alignItems="center" spacing={0.5}>
                            <Speed sx={{ fontSize: 14 }} />
                            <span>Vol%</span>
                          </Stack>
                        </Tooltip>
                      </TableCell>
                      <TableCell sx={{ fontWeight: "bold" }}>
                        <Tooltip title="Relative Volume (≥2x avg)">
                          <Stack direction="row" alignItems="center" spacing={0.5}>
                            <TrendingUp sx={{ fontSize: 14 }} />
                            <span>RVol</span>
                          </Stack>
                        </Tooltip>
                      </TableCell>
                      <TableCell sx={{ fontWeight: "bold" }}>Score</TableCell>
                      <TableCell sx={{ fontWeight: "bold" }}>Reason</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {filteredEvaluations.map((evaluation) => (
                      <TableRow
                        key={evaluation.symbol}
                        sx={{
                          bgcolor: evaluation.passed
                            ? "rgba(46, 125, 50, 0.05)"
                            : "rgba(244, 67, 54, 0.03)",
                          "&:hover": {
                            bgcolor: evaluation.passed
                              ? "rgba(46, 125, 50, 0.1)"
                              : "rgba(244, 67, 54, 0.08)"
                          }
                        }}
                      >
                        <TableCell>
                          <Stack direction="row" alignItems="center" spacing={1}>
                            <Typography fontWeight="bold">{evaluation.symbol}</Typography>
                            {evaluation.data?.pattern && (
                              <Chip
                                icon={<ShowChart />}
                                label={evaluation.data.pattern.replace("_", " ")}
                                size="small"
                                color="success"
                                sx={{ height: 18, fontSize: "0.6rem" }}
                              />
                            )}
                            {evaluation.data?.news_catalyst && (
                              <Chip
                                icon={<Newspaper />}
                                label={evaluation.data.news_catalyst}
                                size="small"
                                color="warning"
                                sx={{ height: 18, fontSize: "0.6rem" }}
                              />
                            )}
                          </Stack>
                        </TableCell>
                        <TableCell>
                          <Chip
                            icon={evaluation.passed ? <CheckCircle /> : <Cancel />}
                            label={evaluation.passed ? "PASS" : "FAIL"}
                            size="small"
                            color={evaluation.passed ? "success" : "error"}
                            sx={{ height: 24 }}
                          />
                        </TableCell>
                        <TableCell>
                          ${evaluation.data?.price?.toFixed(2) || "-"}
                        </TableCell>
                        <TableCell>
                          <FilterIcon passed={evaluation.filters?.volume?.passed !== false} />
                          <Typography variant="caption" sx={{ ml: 0.5 }}>
                            {evaluation.data?.avg_volume
                              ? `${(evaluation.data.avg_volume / 1000000).toFixed(1)}M`
                              : "-"}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <FilterIcon passed={evaluation.filters?.price?.passed !== false} />
                        </TableCell>
                        <TableCell>
                          <FilterIcon passed={evaluation.filters?.volatility?.passed !== false} />
                          <Typography variant="caption" sx={{ ml: 0.5 }}>
                            {evaluation.data?.volatility
                              ? `${(evaluation.data.volatility * 100).toFixed(1)}%`
                              : "-"}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <FilterIcon passed={evaluation.filters?.relative_volume?.passed !== false} />
                          <Typography
                            variant="caption"
                            sx={{ ml: 0.5 }}
                            color={evaluation.data?.relative_volume && evaluation.data.relative_volume >= 2 ? "warning.main" : "text.secondary"}
                            fontWeight={evaluation.data?.relative_volume && evaluation.data.relative_volume >= 2 ? "bold" : "normal"}
                          >
                            {evaluation.data?.relative_volume?.toFixed(1) || "-"}x
                          </Typography>
                        </TableCell>
                        <TableCell>
                          {evaluation.passed && evaluation.scores?.combined_score ? (
                            <Chip
                              label={`${(evaluation.scores.combined_score * 100).toFixed(0)}%`}
                              size="small"
                              color={evaluation.scores.combined_score > 0.5 ? "success" : evaluation.scores.combined_score > 0.3 ? "warning" : "default"}
                              sx={{ height: 20, fontSize: "0.65rem" }}
                            />
                          ) : "-"}
                        </TableCell>
                        <TableCell sx={{ maxWidth: 200 }}>
                          <Typography
                            variant="caption"
                            color={evaluation.passed ? "success.main" : "error.main"}
                            sx={{
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              whiteSpace: "nowrap",
                              display: "block"
                            }}
                          >
                            {evaluation.passed
                              ? `Score: ${(evaluation.scores?.combined_score || 0 * 100).toFixed(0)}% | ML: ${((evaluation.scores?.ml_score || 0) * 100).toFixed(0)}%`
                              : evaluation.rejection_reason || "Unknown"}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Alert severity="info">
                No stocks evaluated yet. Start the autonomous engine to begin scanning.
              </Alert>
            )}
          </>
        )}

        {/* Tab 1: Top Opportunities */}
        {viewTab === 1 && (
          <>
            <Typography variant="subtitle2" sx={{ mb: 2 }}>
              Stocks that passed all filters, ranked by combined score
            </Typography>
            {status.scanner_results?.length > 0 ? (
              <TableContainer component={Paper} sx={{ bgcolor: "transparent", maxHeight: 400 }}>
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: "bold" }}>#</TableCell>
                      <TableCell sx={{ fontWeight: "bold" }}>Symbol</TableCell>
                      <TableCell sx={{ fontWeight: "bold" }}>Price</TableCell>
                      <TableCell sx={{ fontWeight: "bold" }}>Combined</TableCell>
                      <TableCell sx={{ fontWeight: "bold" }}>ML</TableCell>
                      <TableCell sx={{ fontWeight: "bold" }}>Momentum</TableCell>
                      <TableCell sx={{ fontWeight: "bold" }}>RVol</TableCell>
                      <TableCell sx={{ fontWeight: "bold" }}>ATR%</TableCell>
                      <TableCell sx={{ fontWeight: "bold" }}>Signals</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {status.scanner_results.map((result, idx) => (
                      <TableRow key={result.symbol} hover>
                        <TableCell>
                          <Chip
                            label={idx + 1}
                            size="small"
                            color={idx === 0 ? "success" : idx < 3 ? "warning" : "default"}
                            sx={{ height: 20, minWidth: 24 }}
                          />
                        </TableCell>
                        <TableCell>
                          <Typography fontWeight="bold">{result.symbol}</Typography>
                        </TableCell>
                        <TableCell>${result.last_price?.toFixed(2)}</TableCell>
                        <TableCell>
                          <Stack direction="row" alignItems="center" spacing={1}>
                            <LinearProgress
                              variant="determinate"
                              value={Math.min(result.combined_score * 100, 100)}
                              sx={{
                                width: 50,
                                height: 6,
                                borderRadius: 3,
                                bgcolor: "rgba(255,255,255,0.1)",
                                "& .MuiLinearProgress-bar": {
                                  borderRadius: 3,
                                  bgcolor: result.combined_score > 0.5 ? "success.main" : "warning.main"
                                }
                              }}
                            />
                            <Typography variant="caption" fontWeight="bold">
                              {(result.combined_score * 100).toFixed(0)}%
                            </Typography>
                          </Stack>
                        </TableCell>
                        <TableCell>{(result.ml_score * 100).toFixed(0)}%</TableCell>
                        <TableCell>
                          <Typography color={result.momentum_score > 0 ? "success.main" : "error.main"}>
                            {(result.momentum_score * 100).toFixed(1)}%
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography fontWeight={result.relative_volume >= 3 ? "bold" : "normal"} color={result.relative_volume >= 3 ? "warning.main" : "inherit"}>
                            {result.relative_volume?.toFixed(1)}x
                          </Typography>
                        </TableCell>
                        <TableCell>{result.atr_percent?.toFixed(1)}%</TableCell>
                        <TableCell>
                          <Stack direction="row" spacing={0.5}>
                            {result.pattern && (
                              <Chip label={result.pattern.replace("_", " ")} size="small" color="success" sx={{ height: 18, fontSize: "0.55rem" }} />
                            )}
                            {result.news_catalyst && (
                              <Chip label={result.news_catalyst} size="small" color="warning" sx={{ height: 18, fontSize: "0.55rem" }} />
                            )}
                            {result.time_multiplier > 1 && (
                              <Chip icon={<Whatshot />} label={`${result.time_multiplier}x`} size="small" sx={{ height: 18, fontSize: "0.55rem" }} />
                            )}
                          </Stack>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Alert severity="info">
                No opportunities found yet. The scanner will identify stocks matching all criteria.
              </Alert>
            )}
          </>
        )}

        {/* Tab 2: Active Strategies */}
        {viewTab === 2 && (
          <>
            <Typography variant="subtitle2" sx={{ mb: 2 }}>
              All strategies are automatically enabled and running
            </Typography>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
              {status.active_strategies?.map((strategy) => (
                <Chip
                  key={strategy}
                  icon={<CheckCircle />}
                  label={strategy.replace(/_/g, " ").toUpperCase()}
                  color="success"
                  variant="outlined"
                  size="small"
                  sx={{
                    borderRadius: 1,
                    "& .MuiChip-icon": { color: "success.main" }
                  }}
                />
              )) || (
                <Typography color="text.secondary">No strategies loaded</Typography>
              )}
            </Box>
            <Box sx={{ mt: 3, p: 2, borderRadius: 2, bgcolor: "rgba(255,255,255,0.02)" }}>
              <Typography variant="subtitle2" fontWeight="bold" sx={{ mb: 1 }}>
                How Strategies Work:
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Each stock that passes the screening filters is analyzed by ALL active strategies.
                When multiple strategies agree on a BUY or SELL signal, the confidence score increases.
                A trade is executed when enough strategies agree (based on risk posture settings).
              </Typography>
            </Box>
          </>
        )}

        {/* Last Scan Time */}
        <Box sx={{ mt: 2, pt: 2, borderTop: "1px solid rgba(255,255,255,0.06)" }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Stack direction="row" spacing={1} alignItems="center">
              <AccessTime sx={{ fontSize: 16, color: "text.secondary" }} />
              {status.last_scan ? (
                <Typography variant="caption" color="text.secondary">
                  Last scan: {new Date(status.last_scan).toLocaleString()} ({Math.round((Date.now() - new Date(status.last_scan).getTime()) / 1000)}s ago)
                </Typography>
              ) : (
                <Typography variant="caption" color="warning.main">
                  No scans yet - Click "Scan Now" to start
                </Typography>
              )}
            </Stack>
            <Typography variant="caption" color="text.secondary">
              Auto-refresh: every 5 seconds
            </Typography>
          </Stack>
        </Box>
      </CardContent>
    </Card>
  );
};

export default MarketScannerPanel;
