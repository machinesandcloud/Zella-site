import { useEffect, useState, useCallback } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Chip,
  Stack,
  IconButton,
  Tooltip,
  CircularProgress,
  Alert,
  Collapse,
  InputAdornment,
  Autocomplete,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Switch,
  FormControlLabel,
  Checkbox
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import SearchIcon from "@mui/icons-material/Search";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import RefreshIcon from "@mui/icons-material/Refresh";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import {
  fetchWatchlist as fetchWatchlistApi,
  addToWatchlist,
  removeFromWatchlist,
  searchSymbols as searchSymbolsApi,
  validateSymbol as validateSymbolApi,
  fetchWatchlistSnapshots
} from "../../services/api";

interface WatchlistInfo {
  total_symbols: number;
  default_symbols: number;
  custom_symbols: string[];
  custom_count: number;
  universe: string[];
}

interface SymbolOption {
  symbol: string;
  name: string;
  exchange?: string;
  tradable?: boolean;
}

interface MarketSnapshot {
  symbol: string;
  price: number;
  bid: number;
  ask: number;
  bid_size: number;
  ask_size: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  vwap: number;
  prev_close: number;
  change: number;
  change_pct: number;
  timestamp: string;
}

const DISPLAYED_SYMBOLS_KEY = "zella_displayed_watchlist_symbols";

const loadDisplayedSymbols = (): string[] => {
  try {
    const saved = localStorage.getItem(DISPLAYED_SYMBOLS_KEY);
    return saved ? JSON.parse(saved) : [];
  } catch {
    return [];
  }
};

const saveDisplayedSymbols = (symbols: string[]) => {
  try {
    localStorage.setItem(DISPLAYED_SYMBOLS_KEY, JSON.stringify(symbols));
  } catch (e) {
    console.error("Failed to save displayed symbols:", e);
  }
};

const formatPrice = (price: number) => {
  if (!price) return "-";
  return `$${price.toFixed(2)}`;
};

const formatVolume = (volume: number) => {
  if (!volume) return "-";
  if (volume >= 1000000) return `${(volume / 1000000).toFixed(1)}M`;
  if (volume >= 1000) return `${(volume / 1000).toFixed(0)}K`;
  return volume.toString();
};

const formatChange = (change: number, changePct: number) => {
  if (change === undefined || change === null) return "-";
  const sign = change >= 0 ? "+" : "";
  return `${sign}${change.toFixed(2)} (${sign}${changePct.toFixed(2)}%)`;
};

const WatchlistManager = () => {
  const [watchlist, setWatchlist] = useState<WatchlistInfo | null>(null);
  const [snapshots, setSnapshots] = useState<Record<string, MarketSnapshot>>({});
  const [loading, setLoading] = useState(true);
  const [snapshotsLoading, setSnapshotsLoading] = useState(false);
  const [newSymbol, setNewSymbol] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Displayed symbols (which ones show in real-time table)
  const [displayedSymbols, setDisplayedSymbols] = useState<string[]>(() => loadDisplayedSymbols());

  // Autocomplete state
  const [options, setOptions] = useState<SymbolOption[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState<SymbolOption | null>(null);
  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<{
    valid: boolean;
    reason?: string;
  } | null>(null);

  const fetchWatchlist = async () => {
    try {
      const data = await fetchWatchlistApi();
      setWatchlist(data);
      setError(null);

      // If no displayed symbols saved, default to custom + first 10 default
      if (displayedSymbols.length === 0 && data) {
        const defaultDisplayed = [
          ...(data.custom_symbols || []),
          ...(data.universe?.filter((s: string) => !data.custom_symbols?.includes(s)).slice(0, 10) || [])
        ];
        setDisplayedSymbols(defaultDisplayed);
        saveDisplayedSymbols(defaultDisplayed);
      }
    } catch (err) {
      console.error("Failed to fetch watchlist:", err);
      setError("Failed to load watchlist");
    } finally {
      setLoading(false);
    }
  };

  const fetchSnapshots = useCallback(async () => {
    if (!watchlist || displayedSymbols.length === 0) return;

    setSnapshotsLoading(true);
    try {
      const data = await fetchWatchlistSnapshots(displayedSymbols);
      setSnapshots(data.snapshots || {});
    } catch (err) {
      console.error("Failed to fetch snapshots:", err);
    } finally {
      setSnapshotsLoading(false);
    }
  }, [watchlist, displayedSymbols]);

  useEffect(() => {
    fetchWatchlist();
  }, []);

  // Fetch snapshots when watchlist loads or displayed symbols change
  useEffect(() => {
    if (watchlist && displayedSymbols.length > 0) {
      fetchSnapshots();
    }
  }, [watchlist, displayedSymbols, fetchSnapshots]);

  // Auto-refresh snapshots every 5 seconds
  useEffect(() => {
    if (!autoRefresh || displayedSymbols.length === 0) return;

    const interval = setInterval(() => {
      fetchSnapshots();
    }, 5000);

    return () => clearInterval(interval);
  }, [autoRefresh, fetchSnapshots, displayedSymbols]);

  // Toggle symbol display
  const toggleSymbolDisplay = (symbol: string) => {
    setDisplayedSymbols(prev => {
      const newDisplayed = prev.includes(symbol)
        ? prev.filter(s => s !== symbol)
        : [...prev, symbol];
      saveDisplayedSymbols(newDisplayed);
      return newDisplayed;
    });
  };

  // Add all visible symbols to display
  const addAllToDisplay = () => {
    const symbolsToAdd = filteredUniverse.slice(0, 50);
    const newDisplayed = Array.from(new Set([...displayedSymbols, ...symbolsToAdd]));
    setDisplayedSymbols(newDisplayed);
    saveDisplayedSymbols(newDisplayed);
  };

  // Clear all displayed symbols
  const clearAllDisplay = () => {
    setDisplayedSymbols([]);
    saveDisplayedSymbols([]);
    setSnapshots({});
  };

  // Debounced symbol search
  const searchSymbols = useCallback(async (query: string) => {
    if (!query || query.length < 1) {
      setOptions([]);
      return;
    }

    setSearchLoading(true);
    try {
      const data = await searchSymbolsApi(query, 15);
      setOptions(data.symbols || []);
    } catch (err) {
      console.error("Symbol search failed:", err);
      setOptions([]);
    } finally {
      setSearchLoading(false);
    }
  }, []);

  // Debounce the search
  useEffect(() => {
    const timer = setTimeout(() => {
      if (newSymbol && !selectedSymbol) {
        searchSymbols(newSymbol);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [newSymbol, selectedSymbol, searchSymbols]);

  // Validate symbol before adding
  const validateSymbol = async (symbol: string): Promise<boolean> => {
    setValidating(true);
    setValidationResult(null);

    try {
      const result = await validateSymbolApi(symbol);
      setValidationResult(result);
      return result.valid;
    } catch (err) {
      console.error("Validation failed:", err);
      return false;
    } finally {
      setValidating(false);
    }
  };

  const handleAddSymbol = async () => {
    const symbolToAdd = selectedSymbol?.symbol || newSymbol.toUpperCase().trim();
    if (!symbolToAdd) return;

    // Validate the symbol first
    const isValid = await validateSymbol(symbolToAdd);
    if (!isValid) {
      setError(`"${symbolToAdd}" is not a valid tradable stock symbol`);
      setTimeout(() => setError(null), 4000);
      return;
    }

    try {
      const result = await addToWatchlist([symbolToAdd]);

      if (result.added?.length > 0) {
        setSuccess(`Added: ${result.added.join(", ")}`);
        // Auto-add to display list
        const newDisplayed = Array.from(new Set([...displayedSymbols, ...result.added]));
        setDisplayedSymbols(newDisplayed);
        saveDisplayedSymbols(newDisplayed);
        fetchWatchlist();
      } else if (result.already_exists?.length > 0) {
        setSuccess(`Already in watchlist: ${result.already_exists.join(", ")}`);
        // Still add to display if not already displayed
        const newDisplayed = Array.from(new Set([...displayedSymbols, ...result.already_exists]));
        setDisplayedSymbols(newDisplayed);
        saveDisplayedSymbols(newDisplayed);
      }

      setNewSymbol("");
      setSelectedSymbol(null);
      setValidationResult(null);
      setOptions([]);
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      console.error("Failed to add symbol:", err);
      setError("Failed to add symbol");
      setTimeout(() => setError(null), 3000);
    }
  };

  const handleRemoveSymbol = async (symbol: string) => {
    try {
      const result = await removeFromWatchlist([symbol]);

      if (result.removed?.length > 0) {
        setSuccess(`Removed: ${symbol}`);
        // Also remove from display
        const newDisplayed = displayedSymbols.filter(s => s !== symbol);
        setDisplayedSymbols(newDisplayed);
        saveDisplayedSymbols(newDisplayed);
        fetchWatchlist();
      } else if (result.protected?.length > 0) {
        setError(`${symbol} is a default symbol and cannot be removed`);
      }

      setTimeout(() => {
        setSuccess(null);
        setError(null);
      }, 3000);
    } catch (err) {
      console.error("Failed to remove symbol:", err);
      setError("Failed to remove symbol");
      setTimeout(() => setError(null), 3000);
    }
  };

  const filteredUniverse =
    watchlist?.universe.filter((symbol) =>
      symbol.toLowerCase().includes(searchTerm.toLowerCase())
    ) || [];

  const isCustomSymbol = (symbol: string) =>
    watchlist?.custom_symbols.includes(symbol) || false;

  const isDisplayed = (symbol: string) => displayedSymbols.includes(symbol);

  if (loading) {
    return (
      <Card
        elevation={0}
        sx={{ border: "1px solid rgba(255,255,255,0.1)", borderRadius: 3 }}
      >
        <CardContent sx={{ p: 3, textAlign: "center" }}>
          <CircularProgress size={24} />
          <Typography sx={{ mt: 1 }}>Loading watchlist...</Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card
      elevation={0}
      sx={{ border: "1px solid rgba(255,255,255,0.1)", borderRadius: 3 }}
    >
      <CardContent sx={{ p: 3 }}>
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            mb: 2
          }}
        >
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Watchlist
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {displayedSymbols.length} displayed / {watchlist?.total_symbols || 0} total
            </Typography>
          </Box>
          <Stack direction="row" spacing={1} alignItems="center">
            <FormControlLabel
              control={
                <Switch
                  size="small"
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                />
              }
              label={<Typography variant="caption">Auto-refresh</Typography>}
            />
            <Chip
              label={`${watchlist?.custom_count || 0} custom`}
              size="small"
              color="primary"
              variant="outlined"
            />
            <IconButton size="small" onClick={() => { fetchWatchlist(); fetchSnapshots(); }}>
              <RefreshIcon fontSize="small" />
            </IconButton>
          </Stack>
        </Box>

        {/* Add Symbol Input with Autocomplete */}
        <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
          <Autocomplete
            freeSolo
            options={options}
            getOptionLabel={(option) =>
              typeof option === "string" ? option : option.symbol
            }
            value={selectedSymbol}
            inputValue={newSymbol}
            onInputChange={(_, value) => {
              setNewSymbol(value.toUpperCase());
              setValidationResult(null);
            }}
            onChange={(_, value) => {
              if (typeof value === "string") {
                setSelectedSymbol(null);
                setNewSymbol(value.toUpperCase());
              } else {
                setSelectedSymbol(value);
                setNewSymbol(value?.symbol || "");
              }
              setValidationResult(null);
            }}
            loading={searchLoading}
            filterOptions={(x) => x}
            renderOption={(props, option) => (
              <Box
                component="li"
                {...props}
                sx={{ display: "flex", justifyContent: "space-between", gap: 2 }}
              >
                <Box>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {option.symbol}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" noWrap>
                    {option.name?.slice(0, 40)}
                    {option.name && option.name.length > 40 ? "..." : ""}
                  </Typography>
                </Box>
                {option.exchange && (
                  <Chip
                    label={option.exchange}
                    size="small"
                    variant="outlined"
                    sx={{ fontSize: "0.65rem", height: 20 }}
                  />
                )}
              </Box>
            )}
            PaperComponent={(props) => (
              <Paper {...props} sx={{ bgcolor: "background.paper" }} />
            )}
            sx={{ flex: 1 }}
            renderInput={(params) => (
              <TextField
                {...params}
                size="small"
                placeholder="Search stock symbol (e.g., AAPL)"
                onKeyPress={(e) => e.key === "Enter" && handleAddSymbol()}
                InputProps={{
                  ...params.InputProps,
                  startAdornment: (
                    <InputAdornment position="start">
                      {validating ? (
                        <CircularProgress size={16} />
                      ) : validationResult?.valid ? (
                        <CheckCircleIcon
                          fontSize="small"
                          sx={{ color: "success.main" }}
                        />
                      ) : validationResult?.valid === false ? (
                        <ErrorIcon fontSize="small" sx={{ color: "error.main" }} />
                      ) : (
                        <AddIcon fontSize="small" />
                      )}
                    </InputAdornment>
                  ),
                  endAdornment: (
                    <>
                      {searchLoading ? (
                        <CircularProgress color="inherit" size={16} />
                      ) : null}
                      {params.InputProps.endAdornment}
                    </>
                  )
                }}
              />
            )}
          />
          <Button
            variant="contained"
            onClick={handleAddSymbol}
            disabled={!newSymbol.trim() || validating}
            sx={{ textTransform: "none" }}
          >
            {validating ? <CircularProgress size={20} /> : "Add"}
          </Button>
        </Stack>

        {/* Validation Hint */}
        {selectedSymbol && (
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ display: "block", mb: 1 }}
          >
            {selectedSymbol.name} ({selectedSymbol.exchange})
          </Typography>
        )}

        {/* Alerts */}
        <Collapse in={!!error}>
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        </Collapse>
        <Collapse in={!!success}>
          <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
            {success}
          </Alert>
        </Collapse>

        {/* Real-Time Data Table */}
        <Box sx={{ mb: 2 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
              Real-Time Market Data ({displayedSymbols.length} symbols)
            </Typography>
            {snapshotsLoading && <CircularProgress size={14} />}
          </Stack>
          {displayedSymbols.length === 0 ? (
            <Alert severity="info" sx={{ mb: 2 }}>
              No symbols selected for display. Expand "Manage Display" below to select symbols.
            </Alert>
          ) : (
            <TableContainer
              component={Paper}
              sx={{
                maxHeight: 400,
                bgcolor: "rgba(255,255,255,0.02)",
                border: "1px solid rgba(255,255,255,0.1)"
              }}
            >
              <Table size="small" stickyHeader>
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600, bgcolor: "background.paper" }}>Symbol</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600, bgcolor: "background.paper" }}>Price</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600, bgcolor: "background.paper" }}>Change</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600, bgcolor: "background.paper" }}>Bid</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600, bgcolor: "background.paper" }}>Ask</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600, bgcolor: "background.paper" }}>Volume</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600, bgcolor: "background.paper" }}>High</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600, bgcolor: "background.paper" }}>Low</TableCell>
                    <TableCell align="center" sx={{ bgcolor: "background.paper" }}>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {displayedSymbols.map((symbol) => {
                    const snapshot = snapshots[symbol];
                    const isCustom = isCustomSymbol(symbol);
                    const changePositive = (snapshot?.change || 0) >= 0;

                    return (
                      <TableRow
                        key={symbol}
                        sx={{
                          bgcolor: isCustom ? "rgba(25, 118, 210, 0.08)" : "transparent",
                          "&:hover": { bgcolor: "rgba(255,255,255,0.05)" }
                        }}
                      >
                        <TableCell>
                          <Stack direction="row" alignItems="center" spacing={0.5}>
                            <Typography variant="body2" sx={{ fontWeight: 600 }}>
                              {symbol}
                            </Typography>
                            {isCustom && (
                              <Chip label="Custom" size="small" color="primary" sx={{ height: 16, fontSize: "0.6rem" }} />
                            )}
                          </Stack>
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2" sx={{ fontWeight: 500 }}>
                            {formatPrice(snapshot?.price)}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Stack direction="row" alignItems="center" justifyContent="flex-end" spacing={0.5}>
                            {snapshot?.change !== undefined && snapshot?.change !== 0 && (
                              changePositive ? (
                                <TrendingUpIcon sx={{ fontSize: 14, color: "success.main" }} />
                              ) : (
                                <TrendingDownIcon sx={{ fontSize: 14, color: "error.main" }} />
                              )
                            )}
                            <Typography
                              variant="body2"
                              sx={{ color: changePositive ? "success.main" : "error.main" }}
                            >
                              {formatChange(snapshot?.change, snapshot?.change_pct)}
                            </Typography>
                          </Stack>
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2" color="text.secondary">
                            {formatPrice(snapshot?.bid)}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2" color="text.secondary">
                            {formatPrice(snapshot?.ask)}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2" color="text.secondary">
                            {formatVolume(snapshot?.volume)}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2" color="text.secondary">
                            {formatPrice(snapshot?.high)}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2" color="text.secondary">
                            {formatPrice(snapshot?.low)}
                          </Typography>
                        </TableCell>
                        <TableCell align="center">
                          <Stack direction="row" spacing={0.5} justifyContent="center">
                            <Tooltip title="Hide from display">
                              <IconButton
                                size="small"
                                onClick={() => toggleSymbolDisplay(symbol)}
                              >
                                <VisibilityOffIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                            {isCustom && (
                              <Tooltip title="Remove from watchlist">
                                <IconButton
                                  size="small"
                                  onClick={() => handleRemoveSymbol(symbol)}
                                  sx={{ color: "error.main" }}
                                >
                                  <DeleteIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            )}
                          </Stack>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Box>

        {/* Manage Display Toggle */}
        <Button
          variant="text"
          size="small"
          onClick={() => setExpanded(!expanded)}
          endIcon={expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          sx={{ textTransform: "none", mb: 1 }}
        >
          {expanded ? "Hide" : "Manage Display"} ({watchlist?.total_symbols || 0} available)
        </Button>

        <Collapse in={expanded}>
          {/* Quick Actions */}
          <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
            <Button
              size="small"
              variant="outlined"
              onClick={addAllToDisplay}
              startIcon={<VisibilityIcon />}
              sx={{ textTransform: "none" }}
            >
              Add Filtered to Display
            </Button>
            <Button
              size="small"
              variant="outlined"
              color="warning"
              onClick={clearAllDisplay}
              startIcon={<VisibilityOffIcon />}
              sx={{ textTransform: "none" }}
            >
              Clear Display
            </Button>
          </Stack>

          {/* Search */}
          <TextField
            size="small"
            placeholder="Filter symbols..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            sx={{ width: "100%", mb: 2 }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              )
            }}
          />

          {/* All Symbols with checkboxes */}
          <Box
            sx={{
              maxHeight: 300,
              overflowY: "auto",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 1,
              p: 1
            }}
          >
            <Stack direction="row" flexWrap="wrap" gap={0.5}>
              {filteredUniverse.slice(0, 200).map((symbol) => (
                <Chip
                  key={symbol}
                  icon={
                    <Checkbox
                      size="small"
                      checked={isDisplayed(symbol)}
                      onChange={() => toggleSymbolDisplay(symbol)}
                      sx={{ p: 0, ml: 0.5 }}
                    />
                  }
                  label={symbol}
                  size="small"
                  variant={isDisplayed(symbol) ? "filled" : "outlined"}
                  color={isCustomSymbol(symbol) ? "primary" : isDisplayed(symbol) ? "success" : "default"}
                  onClick={() => toggleSymbolDisplay(symbol)}
                  onDelete={isCustomSymbol(symbol) ? () => handleRemoveSymbol(symbol) : undefined}
                  sx={{
                    fontSize: "0.7rem",
                    height: 28,
                    cursor: "pointer",
                    "& .MuiChip-deleteIcon": { fontSize: 14 }
                  }}
                />
              ))}
              {filteredUniverse.length > 200 && (
                <Chip
                  label={`+${filteredUniverse.length - 200} more`}
                  size="small"
                  variant="outlined"
                  sx={{ fontSize: "0.7rem", height: 28 }}
                />
              )}
            </Stack>
          </Box>

          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
            Tip: Click symbols to toggle display. Green = displayed. Delete icon removes custom symbols from watchlist.
          </Typography>
        </Collapse>
      </CardContent>
    </Card>
  );
};

export default WatchlistManager;
