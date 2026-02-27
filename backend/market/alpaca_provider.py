"""Alpaca Market Data Provider for day trading universe"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from functools import lru_cache
import logging
import threading
import time
import hashlib

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest, StockSnapshotRequest, StockLatestTradeRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from market.market_data_provider import MarketDataProvider
from market.universe import get_default_universe
from pathlib import Path
import json

logger = logging.getLogger("alpaca_provider")

# Persistent watchlist file
WATCHLIST_FILE = Path("data/custom_watchlist.json")

# Rate limiting configuration
RATE_LIMIT_REQUESTS_PER_MINUTE = 150  # Alpaca free tier is 200/min, leave buffer
MIN_REQUEST_INTERVAL = 60.0 / RATE_LIMIT_REQUESTS_PER_MINUTE  # ~0.4 seconds between requests
MAX_BACKOFF_SECONDS = 60
INITIAL_BACKOFF_SECONDS = 2


class AlpacaMarketDataProvider(MarketDataProvider):
    """
    Market data provider using Alpaca's free market data API.

    Provides:
    - Day trading universe (90+ high volume stocks)
    - Real-time and historical data via Alpaca
    - Batch quote fetching for efficiency
    - Aggressive caching to avoid rate limits
    - Exponential backoff on 429 errors
    """

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        universe: Optional[List[str]] = None,
        cache_ttl: float = 5.0  # Cache TTL in seconds (5s - good balance for day trading)
    ) -> None:
        """
        Initialize Alpaca market data provider.

        Args:
            api_key: Alpaca API key
            secret_key: Alpaca secret key
            universe: Optional custom universe (defaults to day trading universe)
            cache_ttl: How long to cache quotes (in seconds)
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.cache_ttl = cache_ttl

        # Use provided universe or default
        self._default_universe = universe if universe else get_default_universe()
        self._custom_symbols: List[str] = []
        self._load_custom_watchlist()

        # Always merge custom symbols with default universe
        self._universe = list(set(self._default_universe + self._custom_symbols))

        # Alpaca market data client
        self.data_client = StockHistoricalDataClient(
            api_key=api_key,
            secret_key=secret_key
        )

        # Quote cache for fast lookups
        self._quote_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamp: float = 0
        self._cache_lock = threading.Lock()

        # Historical bars cache: key = (symbol, duration, bar_size), value = (timestamp, data)
        self._bars_cache: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
        self._bars_cache_ttl = 60.0  # Cache historical bars for 60 seconds
        self._bars_cache_lock = threading.Lock()

        # Rate limiting state
        self._last_request_time: float = 0
        self._request_lock = threading.Lock()
        self._backoff_until: float = 0
        self._current_backoff: float = INITIAL_BACKOFF_SECONDS

        # Start background refresh thread
        self._refresh_thread = threading.Thread(target=self._background_refresh, daemon=True)
        self._refresh_thread.start()

        logger.info(f"Alpaca Market Data Provider initialized with {len(self._universe)} symbols (cache_ttl={cache_ttl}s)")

    def _wait_for_rate_limit(self) -> None:
        """Wait if we need to respect rate limits or backoff"""
        with self._request_lock:
            now = time.time()

            # Check if we're in backoff period (from 429 error)
            if now < self._backoff_until:
                wait_time = self._backoff_until - now
                logger.debug(f"Rate limit backoff: waiting {wait_time:.1f}s")
                time.sleep(wait_time)
                now = time.time()

            # Ensure minimum interval between requests
            elapsed = now - self._last_request_time
            if elapsed < MIN_REQUEST_INTERVAL:
                time.sleep(MIN_REQUEST_INTERVAL - elapsed)

            self._last_request_time = time.time()

    def _handle_rate_limit_error(self, error: Exception) -> None:
        """Handle 429 rate limit errors with exponential backoff"""
        error_str = str(error).lower()
        if "429" in error_str or "too many requests" in error_str or "rate limit" in error_str:
            with self._request_lock:
                self._backoff_until = time.time() + self._current_backoff
                logger.warning(f"Rate limited! Backing off for {self._current_backoff}s")
                # Exponential backoff, max 60 seconds
                self._current_backoff = min(self._current_backoff * 2, MAX_BACKOFF_SECONDS)
        else:
            # Reset backoff on successful request or non-rate-limit error
            self._current_backoff = INITIAL_BACKOFF_SECONDS

    def _reset_backoff(self) -> None:
        """Reset backoff after successful request"""
        with self._request_lock:
            self._current_backoff = INITIAL_BACKOFF_SECONDS

    def _background_refresh(self) -> None:
        """Background thread to continuously refresh quotes with rate limiting"""
        while True:
            try:
                # Check if we should skip due to backoff
                if time.time() < self._backoff_until:
                    wait_time = self._backoff_until - time.time()
                    logger.debug(f"Background refresh delayed {wait_time:.1f}s due to rate limit")
                    time.sleep(max(wait_time, self.cache_ttl))
                    continue

                self._refresh_all_quotes()
                self._reset_backoff()  # Successful refresh, reset backoff
            except Exception as e:
                self._handle_rate_limit_error(e)
                logger.debug(f"Background refresh error: {e}")

            # Wait before next refresh cycle
            time.sleep(self.cache_ttl)

    def _refresh_all_quotes(self) -> None:
        """Fetch snapshots for all universe symbols in batches using Snapshot API"""
        try:
            # Batch symbols (Alpaca allows up to 100 per request, use 75 to be safe)
            batch_size = 75
            all_quotes = {}

            for i in range(0, len(self._universe), batch_size):
                batch = self._universe[i:i + batch_size]
                try:
                    # Wait for rate limit before each batch
                    self._wait_for_rate_limit()

                    # Use Snapshot API - provides quote, trade, daily bar, and previous day bar
                    request = StockSnapshotRequest(symbol_or_symbols=batch)
                    snapshots = self.data_client.get_stock_snapshot(request)

                    for symbol in batch:
                        if symbol not in snapshots:
                            continue

                        snap = snapshots[symbol]
                        quote_data = {}

                        # Get latest quote (bid/ask)
                        if snap.latest_quote:
                            q = snap.latest_quote
                            quote_data["bid"] = float(q.bid_price) if q.bid_price else 0
                            quote_data["ask"] = float(q.ask_price) if q.ask_price else 0
                            quote_data["bid_size"] = int(q.bid_size) if q.bid_size else 0
                            quote_data["ask_size"] = int(q.ask_size) if q.ask_size else 0
                            quote_data["quote_timestamp"] = q.timestamp.isoformat() if q.timestamp else None

                        # Get latest trade
                        if snap.latest_trade:
                            t = snap.latest_trade
                            quote_data["price"] = float(t.price) if t.price else 0
                            quote_data["last_trade"] = float(t.price) if t.price else 0
                            quote_data["trade_size"] = int(t.size) if t.size else 0
                            quote_data["trade_timestamp"] = t.timestamp.isoformat() if t.timestamp else None

                        # Get today's daily bar (open, high, low, close, volume)
                        if snap.daily_bar:
                            db = snap.daily_bar
                            quote_data["open"] = float(db.open) if db.open else 0
                            quote_data["high"] = float(db.high) if db.high else 0
                            quote_data["low"] = float(db.low) if db.low else 0
                            quote_data["close"] = float(db.close) if db.close else 0
                            quote_data["volume"] = int(db.volume) if db.volume else 0
                            quote_data["vwap"] = float(db.vwap) if db.vwap else 0

                        # Get previous day's close
                        if snap.previous_daily_bar:
                            pdb = snap.previous_daily_bar
                            quote_data["prev_close"] = float(pdb.close) if pdb.close else 0
                            quote_data["prev_volume"] = int(pdb.volume) if pdb.volume else 0

                        # Calculate change from previous close
                        if quote_data.get("price") and quote_data.get("prev_close"):
                            prev = quote_data["prev_close"]
                            curr = quote_data["price"]
                            quote_data["change"] = round(curr - prev, 2)
                            quote_data["change_pct"] = round((curr - prev) / prev * 100, 2) if prev else 0

                        if quote_data.get("price"):
                            all_quotes[symbol] = quote_data

                except Exception as e:
                    error_str = str(e).lower()
                    if "429" in error_str or "too many requests" in error_str:
                        self._handle_rate_limit_error(e)
                        logger.warning(f"Rate limit hit during batch {i}-{i+batch_size}, backing off")
                        break  # Stop this refresh cycle, let backoff handle it
                    logger.debug(f"Error fetching snapshot batch {i}-{i+batch_size}: {e}")

            # Update cache atomically (even partial results are useful)
            if all_quotes:
                with self._cache_lock:
                    # Merge with existing cache instead of replacing
                    self._quote_cache.update(all_quotes)
                    self._cache_timestamp = time.time()

                logger.debug(f"Refreshed {len(all_quotes)} snapshots")

        except Exception as e:
            self._handle_rate_limit_error(e)
            logger.error(f"Error refreshing snapshots: {e}")

    def get_universe(self) -> List[str]:
        """Get the trading universe (90+ day trading stocks)"""
        return self._universe

    def _get_bars_cache_key(self, symbol: str, duration: str, bar_size: str) -> str:
        """Generate cache key for historical bars"""
        return f"{symbol}:{duration}:{bar_size}"

    def _get_cached_bars(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached bars if still valid"""
        with self._bars_cache_lock:
            if cache_key in self._bars_cache:
                timestamp, data = self._bars_cache[cache_key]
                if time.time() - timestamp < self._bars_cache_ttl:
                    logger.debug(f"Bars cache hit for {cache_key}")
                    return data
                else:
                    # Expired, remove from cache
                    del self._bars_cache[cache_key]
        return None

    def _set_cached_bars(self, cache_key: str, data: List[Dict[str, Any]]) -> None:
        """Cache historical bars"""
        with self._bars_cache_lock:
            self._bars_cache[cache_key] = (time.time(), data)
            # Limit cache size to prevent memory issues
            if len(self._bars_cache) > 500:
                # Remove oldest entries
                sorted_keys = sorted(
                    self._bars_cache.keys(),
                    key=lambda k: self._bars_cache[k][0]
                )
                for key in sorted_keys[:100]:
                    del self._bars_cache[key]

    def get_historical_bars(
        self,
        symbol: str,
        duration: str,
        bar_size: str
    ) -> List[Dict[str, Any]]:
        """
        Get historical bars from Alpaca with caching.

        Args:
            symbol: Stock symbol
            duration: Time period (e.g., "1 D", "5 D", "1 M")
            bar_size: Bar size (e.g., "1 min", "5 mins", "1 hour")

        Returns:
            List of bar dictionaries with OHLCV data
        """
        # Check cache first
        cache_key = self._get_bars_cache_key(symbol, duration, bar_size)
        cached = self._get_cached_bars(cache_key)
        if cached is not None:
            return cached

        try:
            # Wait for rate limit
            self._wait_for_rate_limit()

            # Map duration to start date
            duration_map = {
                "1 D": timedelta(days=1),
                "2 D": timedelta(days=2),
                "5 D": timedelta(days=5),
                "1 W": timedelta(weeks=1),
                "1 M": timedelta(days=30),
                "3 M": timedelta(days=90),
                "6 M": timedelta(days=180),
                "1 Y": timedelta(days=365),
            }

            # Map bar size to Alpaca TimeFrame
            timeframe_map = {
                "1 min": TimeFrame.Minute,
                "5 mins": TimeFrame(5, TimeFrameUnit.Minute),
                "15 mins": TimeFrame(15, TimeFrameUnit.Minute),
                "1 hour": TimeFrame.Hour,
                "1 day": TimeFrame.Day,
            }

            delta = duration_map.get(duration, timedelta(days=1))
            timeframe = timeframe_map.get(bar_size, TimeFrame(5, TimeFrameUnit.Minute))

            start_date = datetime.now() - delta
            end_date = datetime.now()

            # Create request
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=timeframe,
                start=start_date,
                end=end_date
            )

            # Fetch bars
            bars_response = self.data_client.get_stock_bars(request)

            # Alpaca returns a BarSet object - access .data for the actual dict
            bars_data = bars_response.data if hasattr(bars_response, 'data') else bars_response

            if symbol not in bars_data:
                logger.warning(f"No bars returned for {symbol}")
                return []

            # Convert to list of dicts
            bars = []
            for bar in bars_data[symbol]:
                bars.append({
                    "date": bar.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "open": float(bar.open),
                    "high": float(bar.high),
                    "low": float(bar.low),
                    "close": float(bar.close),
                    "volume": int(bar.volume)
                })

            # Cache the results
            if bars:
                self._set_cached_bars(cache_key, bars)
                self._reset_backoff()  # Successful request

            logger.debug(f"Retrieved {len(bars)} bars for {symbol}")
            return bars

        except Exception as e:
            self._handle_rate_limit_error(e)
            logger.error(f"Error fetching bars for {symbol}: {e}")
            return []

    def get_latest_bar(self, symbol: str) -> Dict[str, Any]:
        """
        Get latest bar for a symbol (uses cache first).

        Args:
            symbol: Stock symbol

        Returns:
            Latest bar dict or empty dict if error
        """
        # Try cache first (much faster, no API call)
        with self._cache_lock:
            cached = self._quote_cache.get(symbol)
            if cached and cached.get("price"):
                return {
                    "date": cached.get("trade_timestamp") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "open": cached.get("open", cached.get("price", 0)),
                    "high": cached.get("high", cached.get("price", 0)),
                    "low": cached.get("low", cached.get("price", 0)),
                    "close": cached.get("price", 0),
                    "volume": cached.get("volume", 0)
                }

        # Fallback to API call only if not in cache
        try:
            self._wait_for_rate_limit()

            request = StockLatestQuoteRequest(
                symbol_or_symbols=symbol
            )

            quote = self.data_client.get_stock_latest_quote(request)

            if symbol not in quote:
                return {}

            q = quote[symbol]
            self._reset_backoff()

            return {
                "date": q.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "open": float(q.bid_price),  # Use bid as proxy for open
                "high": float(q.ask_price),  # Use ask as proxy for high
                "low": float(q.bid_price),   # Use bid as proxy for low
                "close": float((q.bid_price + q.ask_price) / 2),  # Mid price
                "volume": int(q.bid_size + q.ask_size)
            }

        except Exception as e:
            self._handle_rate_limit_error(e)
            logger.error(f"Error fetching latest quote for {symbol}: {e}")
            return {}

    def get_market_snapshot(self, symbol: str) -> Dict[str, Any]:
        """
        Get market snapshot for a symbol from cache (fast, no API call).

        Args:
            symbol: Stock symbol

        Returns:
            Snapshot dict with price, volume, etc.
        """
        with self._cache_lock:
            cached = self._quote_cache.get(symbol)
            if cached:
                return {
                    "symbol": symbol,
                    "price": cached.get("price", 0),
                    "bid": cached.get("bid", 0),
                    "ask": cached.get("ask", 0),
                    "bid_size": cached.get("bid_size", 0),
                    "ask_size": cached.get("ask_size", 0),
                    # Daily data
                    "open": cached.get("open", 0),
                    "high": cached.get("high", 0),
                    "low": cached.get("low", 0),
                    "close": cached.get("close", 0),
                    "volume": cached.get("volume", 0),
                    "vwap": cached.get("vwap", 0),
                    # Previous day
                    "prev_close": cached.get("prev_close", 0),
                    "prev_volume": cached.get("prev_volume", 0),
                    # Change
                    "change": cached.get("change", 0),
                    "change_pct": cached.get("change_pct", 0),
                    # Timestamps
                    "timestamp": cached.get("trade_timestamp") or cached.get("quote_timestamp") or datetime.now().isoformat()
                }

        # If not in cache, try direct fetch (rare case) - with rate limiting
        try:
            self._wait_for_rate_limit()

            request = StockLatestTradeRequest(symbol_or_symbols=symbol)
            trades = self.data_client.get_stock_latest_trade(request)

            if symbol in trades:
                t = trades[symbol]
                self._reset_backoff()
                return {
                    "symbol": symbol,
                    "price": float(t.price) if t.price else 0,
                    "bid": 0,
                    "ask": 0,
                    "bid_size": 0,
                    "ask_size": 0,
                    "volume": int(t.size) if t.size else 0,
                    "timestamp": t.timestamp.isoformat() if t.timestamp else datetime.now().isoformat()
                }
        except Exception as e:
            self._handle_rate_limit_error(e)
            logger.debug(f"Error fetching snapshot for {symbol}: {e}")

        return {}

    def get_batch_snapshots(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get market snapshots for multiple symbols efficiently from cache.

        Args:
            symbols: List of stock symbols

        Returns:
            Dict mapping symbol to snapshot data
        """
        if not symbols:
            return {}

        snapshots = {}
        with self._cache_lock:
            for symbol in symbols:
                cached = self._quote_cache.get(symbol)
                if cached and cached.get("price"):
                    snapshots[symbol] = {
                        "symbol": symbol,
                        "price": cached.get("price", 0),
                        "bid": cached.get("bid", 0),
                        "ask": cached.get("ask", 0),
                        "bid_size": cached.get("bid_size", 0),
                        "ask_size": cached.get("ask_size", 0),
                        "open": cached.get("open", 0),
                        "high": cached.get("high", 0),
                        "low": cached.get("low", 0),
                        "close": cached.get("close", 0),
                        "volume": cached.get("volume", 0),
                        "vwap": cached.get("vwap", 0),
                        "prev_close": cached.get("prev_close", 0),
                        "prev_volume": cached.get("prev_volume", 0),
                        "change": cached.get("change", 0),
                        "change_pct": cached.get("change_pct", 0),
                        "timestamp": cached.get("trade_timestamp") or cached.get("quote_timestamp") or datetime.now().isoformat()
                    }

        return snapshots

    # ==================== Watchlist Management ====================

    def _load_custom_watchlist(self) -> None:
        """Load custom watchlist from disk"""
        try:
            if WATCHLIST_FILE.exists():
                with open(WATCHLIST_FILE, 'r') as f:
                    data = json.load(f)
                    self._custom_symbols = data.get("symbols", [])
                    logger.info(f"Loaded {len(self._custom_symbols)} custom watchlist symbols")
        except Exception as e:
            logger.error(f"Error loading custom watchlist: {e}")
            self._custom_symbols = []

    def _save_custom_watchlist(self) -> None:
        """Save custom watchlist to disk"""
        try:
            WATCHLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(WATCHLIST_FILE, 'w') as f:
                json.dump({
                    "symbols": self._custom_symbols,
                    "updated_at": datetime.now().isoformat()
                }, f, indent=2)
            logger.info(f"Saved {len(self._custom_symbols)} custom watchlist symbols")
        except Exception as e:
            logger.error(f"Error saving custom watchlist: {e}")

    def add_to_watchlist(self, symbols: List[str]) -> Dict[str, Any]:
        """Add symbols to the watchlist"""
        added = []
        already_exists = []

        for symbol in symbols:
            symbol = symbol.upper().strip()
            if not symbol:
                continue

            if symbol in self._universe:
                already_exists.append(symbol)
            else:
                self._universe.append(symbol)
                if symbol not in self._custom_symbols:
                    self._custom_symbols.append(symbol)
                added.append(symbol)

        if added:
            self._save_custom_watchlist()

        return {
            "added": added,
            "already_exists": already_exists,
            "total_symbols": len(self._universe)
        }

    def remove_from_watchlist(self, symbols: List[str]) -> Dict[str, Any]:
        """Remove symbols from the watchlist"""
        removed = []
        not_found = []
        protected = []

        for symbol in symbols:
            symbol = symbol.upper().strip()
            if not symbol:
                continue

            # Can only remove custom symbols, not default universe
            if symbol in self._default_universe:
                protected.append(symbol)
            elif symbol in self._custom_symbols:
                self._custom_symbols.remove(symbol)
                if symbol in self._universe:
                    self._universe.remove(symbol)
                removed.append(symbol)
            else:
                not_found.append(symbol)

        if removed:
            self._save_custom_watchlist()

        return {
            "removed": removed,
            "not_found": not_found,
            "protected": protected,
            "total_symbols": len(self._universe)
        }

    def get_watchlist_info(self) -> Dict[str, Any]:
        """Get detailed watchlist information"""
        return {
            "total_symbols": len(self._universe),
            "default_symbols": len(self._default_universe),
            "custom_symbols": self._custom_symbols.copy(),
            "custom_count": len(self._custom_symbols),
            "universe": self._universe.copy()
        }

    def set_watchlist(self, symbols: List[str]) -> Dict[str, Any]:
        """Set the entire custom watchlist (replaces existing custom symbols)"""
        # Clean and uppercase all symbols
        symbols = [s.upper().strip() for s in symbols if s.strip()]

        # Separate into default and custom
        custom = [s for s in symbols if s not in self._default_universe]

        self._custom_symbols = custom
        self._universe = list(set(self._default_universe + custom))
        self._save_custom_watchlist()

        return {
            "total_symbols": len(self._universe),
            "custom_symbols": self._custom_symbols.copy()
        }
