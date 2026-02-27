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
  Paper
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import SearchIcon from "@mui/icons-material/Search";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import RefreshIcon from "@mui/icons-material/Refresh";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";

const API_URL = import.meta.env.VITE_API_URL || "";

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

const WatchlistManager = () => {
  const [watchlist, setWatchlist] = useState<WatchlistInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [newSymbol, setNewSymbol] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

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
      const token = localStorage.getItem("zella_token");
      const response = await fetch(`${API_URL}/api/ai/watchlist`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        }
      });

      if (!response.ok) throw new Error("Failed to fetch watchlist");
      const data = await response.json();
      setWatchlist(data);
      setError(null);
    } catch (err) {
      setError("Failed to load watchlist");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWatchlist();
  }, []);

  // Debounced symbol search
  const searchSymbols = useCallback(async (query: string) => {
    if (!query || query.length < 1) {
      setOptions([]);
      return;
    }

    setSearchLoading(true);
    try {
      const token = localStorage.getItem("zella_token");
      const response = await fetch(
        `${API_URL}/api/ai/symbols/search?q=${encodeURIComponent(query)}&limit=15`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json"
          }
        }
      );

      if (response.ok) {
        const data = await response.json();
        setOptions(data.symbols || []);
      }
    } catch (err) {
      console.error("Symbol search failed:", err);
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
      const token = localStorage.getItem("zella_token");
      const response = await fetch(
        `${API_URL}/api/ai/symbols/validate?symbol=${encodeURIComponent(symbol)}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json"
          }
        }
      );

      if (response.ok) {
        const result = await response.json();
        setValidationResult(result);
        return result.valid;
      }
    } catch (err) {
      console.error("Validation failed:", err);
    } finally {
      setValidating(false);
    }

    return false;
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
      const token = localStorage.getItem("zella_token");
      const response = await fetch(`${API_URL}/api/ai/watchlist/add`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ symbols: [symbolToAdd] })
      });

      if (!response.ok) throw new Error("Failed to add symbol");
      const result = await response.json();

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
      setError("Failed to add symbol");
      setTimeout(() => setError(null), 3000);
    }
  };

  const handleRemoveSymbol = async (symbol: string) => {
    try {
      const token = localStorage.getItem("zella_token");
      const response = await fetch(`${API_URL}/api/ai/watchlist/remove`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ symbols: [symbol] })
      });

      if (!response.ok) throw new Error("Failed to remove symbol");
      const result = await response.json();

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
          <Stack direction="row" spacing={1}>
            <Chip
              label={`${watchlist?.custom_count || 0} custom`}
              size="small"
              color="primary"
              variant="outlined"
            />
            <IconButton size="small" onClick={fetchWatchlist}>
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
            filterOptions={(x) => x} // Disable client-side filtering
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

        {/* Custom Symbols */}
        {watchlist?.custom_symbols && watchlist.custom_symbols.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
              Custom Symbols
            </Typography>
            <Stack direction="row" flexWrap="wrap" gap={1}>
              {watchlist.custom_symbols.map((symbol) => (
                <Chip
                  key={symbol}
                  label={symbol}
                  size="small"
                  color="primary"
                  onDelete={() => handleRemoveSymbol(symbol)}
                  deleteIcon={<DeleteIcon />}
                />
              ))}
            </Stack>
          </Box>
        )}

        {/* Full Universe Toggle */}
        <Button
          variant="text"
          size="small"
          onClick={() => setExpanded(!expanded)}
          endIcon={expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          sx={{ textTransform: "none", mb: 1 }}
        >
          {expanded ? "Hide" : "Show"} Full Watchlist (
          {watchlist?.total_symbols || 0})
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
