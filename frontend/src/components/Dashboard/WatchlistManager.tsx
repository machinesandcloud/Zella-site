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
  FormControlLabel
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
    } catch (err) {
      console.error("Failed to fetch watchlist:", err);
      setError("Failed to load watchlist");
    } finally {
      setLoading(false);
    }
  };

  const fetchSnapshots = useCallback(async () => {
    if (!watchlist) return;

    setSnapshotsLoading(true);
    try {
      // Fetch snapshots for custom symbols + top default symbols (max 30)
      const symbolsToFetch = watchlist?.custom_symbols || [];
      const defaultSymbols = watchlist?.universe?.filter(
        s => !watchlist.custom_symbols.includes(s)
      ).slice(0, 30 - symbolsToFetch.length) || [];

      const allSymbols = [...symbolsToFetch, ...defaultSymbols];
      if (allSymbols.length === 0) return;

      const data = await fetchWatchlistSnapshots(allSymbols);
      setSnapshots(data.snapshots || {});
    } catch (err) {
      console.error("Failed to fetch snapshots:", err);
    } finally {
      setSnapshotsLoading(false);
    }
  }, [watchlist]);

  useEffect(() => {
    fetchWatchlist();
  }, []);

  // Fetch snapshots when watchlist loads
  useEffect(() => {
    if (watchlist) {
      fetchSnapshots();
    }
  }, [watchlist, fetchSnapshots]);

  // Auto-refresh snapshots every 5 seconds
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      fetchSnapshots();
    }, 5000);

    return () => clearInterval(interval);
  }, [autoRefresh, fetchSnapshots]);

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
        fetchWatchlist();
      } else if (result.already_exists?.length > 0) {
        setSuccess(`Already in watchlist: ${result.already_exists.join(", ")}`);
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

  // Get symbols to display in table (custom first, then top movers)
  const displaySymbols = [
    ...(watchlist?.custom_symbols || []),
    ...(watchlist?.universe?.filter(s => !watchlist?.custom_symbols?.includes(s)).slice(0, 20) || [])
  ];

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
              {watchlist?.total_symbols || 0} symbols being analyzed
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
              Real-Time Market Data
            </Typography>
            {snapshotsLoading && <CircularProgress size={14} />}
          </Stack>
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
                  <TableCell align="center" sx={{ bgcolor: "background.paper" }}></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {displaySymbols.map((symbol) => {
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
                        {isCustom && (
                          <IconButton
                            size="small"
                            onClick={() => handleRemoveSymbol(symbol)}
                            sx={{ color: "error.main" }}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>

        {/* Full Universe Toggle */}
        <Button
          variant="text"
          size="small"
          onClick={() => setExpanded(!expanded)}
          endIcon={expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          sx={{ textTransform: "none", mb: 1 }}
        >
          {expanded ? "Hide" : "Show"} All Symbols ({watchlist?.total_symbols || 0})
        </Button>

        <Collapse in={expanded}>
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

          {/* All Symbols */}
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
                <Tooltip
                  key={symbol}
                  title={
                    isCustomSymbol(symbol)
                      ? "Custom symbol (click to remove)"
                      : "Default symbol"
                  }
                >
                  <Chip
                    label={symbol}
                    size="small"
                    variant={isCustomSymbol(symbol) ? "filled" : "outlined"}
                    color={isCustomSymbol(symbol) ? "primary" : "default"}
                    onClick={
                      isCustomSymbol(symbol)
                        ? () => handleRemoveSymbol(symbol)
                        : undefined
                    }
                    sx={{
                      fontSize: "0.7rem",
                      height: 24,
                      cursor: isCustomSymbol(symbol) ? "pointer" : "default"
                    }}
                  />
                </Tooltip>
              ))}
              {filteredUniverse.length > 200 && (
                <Chip
                  label={`+${filteredUniverse.length - 200} more`}
                  size="small"
                  variant="outlined"
                  sx={{ fontSize: "0.7rem", height: 24 }}
                />
              )}
            </Stack>
          </Box>
        </Collapse>
      </CardContent>
    </Card>
  );
};

export default WatchlistManager;
