"""Alpaca Market Data Provider for day trading universe - HIGH PERFORMANCE VERSION"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import threading
import asyncio
import time

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.live import StockDataStream
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest, StockSnapshotRequest, StockLatestTradeRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from market.market_data_provider import MarketDataProvider
from market.universe import get_default_universe
from pathlib import Path
import json

logger = logging.getLogger("alpaca_provider")

# Persistent watchlist file
WATCHLIST_FILE = Path("data/custom_watchlist.json")

# Performance configuration - SPEED IS EVERYTHING
MAX_BACKOFF_SECONDS = 30  # Reduced from 60 - recover faster
INITIAL_BACKOFF_SECONDS = 1  # Start smaller for faster recovery
BATCH_SIZE = 100  # Alpaca max - fewer requests = faster total refresh


class AlpacaMarketDataProvider(MarketDataProvider):
    """
    HIGH-PERFORMANCE market data provider using Alpaca API.

    Architecture for MAXIMUM SPEED:
    - WebSocket streaming for instant real-time quotes (sub-100ms latency)
    - Aggressive parallel batch fetching for initial data load
    - Smart caching with fast refresh cycles
    - Only back off when actually rate limited (no preemptive delays)
    """

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        universe: Optional[List[str]] = None,
        cache_ttl: float = 1.5  # Fast refresh cycle (1.5s) - speed is everything
    ) -> None:
        """
        Initialize high-performance Alpaca market data provider.

        Args:
            api_key: Alpaca API key
            secret_key: Alpaca secret key
            universe: Optional custom universe (defaults to day trading universe)
            cache_ttl: How long between refresh cycles (seconds)
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

        # Alpaca market data client (REST API for historical/batch data)
        self.data_client = StockHistoricalDataClient(
            api_key=api_key,
            secret_key=secret_key
        )

        # Quote cache for fast lookups - INSTANT ACCESS
        self._quote_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamp: float = 0
        self._cache_lock = threading.Lock()

        # Historical bars cache with short TTL for freshness
        self._bars_cache: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
        self._bars_cache_ttl = 30.0  # 30 seconds - balance between speed and freshness
        self._bars_cache_lock = threading.Lock()

        # Rate limiting - ONLY on actual 429 errors, no preemptive delays
        self._backoff_until: float = 0
        self._current_backoff: float = INITIAL_BACKOFF_SECONDS
        self._backoff_lock = threading.Lock()

        # WebSocket streaming state
        self._stream_client: Optional[StockDataStream] = None
        self._stream_thread: Optional[threading.Thread] = None
        self._streaming_active = False

        # Thread pool for parallel operations
        self._executor = ThreadPoolExecutor(max_workers=4)

        # Start background refresh thread (fallback when streaming unavailable)
        self._refresh_thread = threading.Thread(target=self._background_refresh, daemon=True)
        self._refresh_thread.start()

        # Try to start WebSocket streaming for real-time updates
        self._start_streaming()

        logger.info(f"Alpaca HIGH-PERFORMANCE Provider initialized: {len(self._universe)} symbols, cache_ttl={cache_ttl}s")

    # ==================== WebSocket Streaming (INSTANT DATA) ====================

    def _start_streaming(self) -> None:
        """Start WebSocket streaming for real-time quote updates"""
        try:
            self._stream_client = StockDataStream(
                api_key=self.api_key,
                secret_key=self.secret_key
            )

            # Subscribe to trades for all universe symbols (instant price updates)
            async def handle_trade(data):
                symbol = data.symbol
                with self._cache_lock:
                    if symbol not in self._quote_cache:
                        self._quote_cache[symbol] = {}
                    self._quote_cache[symbol]["price"] = float(data.price)
                    self._quote_cache[symbol]["last_trade"] = float(data.price)
                    self._quote_cache[symbol]["trade_size"] = int(data.size)
                    self._quote_cache[symbol]["trade_timestamp"] = data.timestamp.isoformat()
                    # Recalculate change if we have prev_close
                    if self._quote_cache[symbol].get("prev_close"):
                        prev = self._quote_cache[symbol]["prev_close"]
                        curr = float(data.price)
                        self._quote_cache[symbol]["change"] = round(curr - prev, 2)
                        self._quote_cache[symbol]["change_pct"] = round((curr - prev) / prev * 100, 2) if prev else 0

            # Subscribe to quotes for bid/ask spread
            async def handle_quote(data):
                symbol = data.symbol
                with self._cache_lock:
                    if symbol not in self._quote_cache:
                        self._quote_cache[symbol] = {}
                    self._quote_cache[symbol]["bid"] = float(data.bid_price) if data.bid_price else 0
                    self._quote_cache[symbol]["ask"] = float(data.ask_price) if data.ask_price else 0
                    self._quote_cache[symbol]["bid_size"] = int(data.bid_size) if data.bid_size else 0
                    self._quote_cache[symbol]["ask_size"] = int(data.ask_size) if data.ask_size else 0
                    self._quote_cache[symbol]["quote_timestamp"] = data.timestamp.isoformat()

            self._stream_client.subscribe_trades(handle_trade, *self._universe[:100])  # Alpaca limit
            self._stream_client.subscribe_quotes(handle_quote, *self._universe[:100])

            # Run stream in background thread
            def run_stream():
                try:
                    self._streaming_active = True
                    self._stream_client.run()
                except Exception as e:
                    logger.warning(f"WebSocket stream error: {e}")
                    self._streaming_active = False

            self._stream_thread = threading.Thread(target=run_stream, daemon=True)
            self._stream_thread.start()
            logger.info("WebSocket streaming started for real-time quotes")

        except Exception as e:
            logger.warning(f"Could not start WebSocket streaming: {e}. Falling back to polling.")
            self._streaming_active = False

    # ==================== Rate Limiting (REACTIVE ONLY) ====================

    def _is_rate_limited(self) -> bool:
        """Check if we're currently in backoff period"""
        return time.time() < self._backoff_until

    def _handle_rate_limit_error(self, error: Exception) -> None:
        """Handle 429 rate limit errors with fast exponential backoff"""
        error_str = str(error).lower()
        if "429" in error_str or "too many requests" in error_str or "rate limit" in error_str:
            with self._backoff_lock:
                self._backoff_until = time.time() + self._current_backoff
                logger.warning(f"Rate limited! Backing off {self._current_backoff}s (will recover)")
                self._current_backoff = min(self._current_backoff * 2, MAX_BACKOFF_SECONDS)

    def _reset_backoff(self) -> None:
        """Reset backoff after successful request"""
        with self._backoff_lock:
            self._current_backoff = INITIAL_BACKOFF_SECONDS

    # ==================== Background Refresh ====================

    def _background_refresh(self) -> None:
        """Background thread for periodic data refresh (supplements streaming)"""
        # Initial delay to let streaming start first
        time.sleep(2)

        while True:
            try:
                # Skip if rate limited
                if self._is_rate_limited():
                    wait_time = self._backoff_until - time.time()
                    time.sleep(max(wait_time, 0.5))
                    continue

                # If streaming is active, do less frequent full refreshes
                refresh_interval = self.cache_ttl * 3 if self._streaming_active else self.cache_ttl

                self._refresh_all_quotes()
                self._reset_backoff()

                time.sleep(refresh_interval)

            except Exception as e:
                self._handle_rate_limit_error(e)
                logger.debug(f"Background refresh error: {e}")
                time.sleep(self.cache_ttl)

    def _fetch_batch(self, batch: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch a single batch of snapshots - used for parallel execution"""
        quotes = {}
        try:
            request = StockSnapshotRequest(symbol_or_symbols=batch)
            snapshots = self.data_client.get_stock_snapshot(request)

            for symbol in batch:
                if symbol not in snapshots:
                    continue

                snap = snapshots[symbol]
                quote_data = {}

                if snap.latest_quote:
                    q = snap.latest_quote
                    quote_data["bid"] = float(q.bid_price) if q.bid_price else 0
                    quote_data["ask"] = float(q.ask_price) if q.ask_price else 0
                    quote_data["bid_size"] = int(q.bid_size) if q.bid_size else 0
                    quote_data["ask_size"] = int(q.ask_size) if q.ask_size else 0
                    quote_data["quote_timestamp"] = q.timestamp.isoformat() if q.timestamp else None

                if snap.latest_trade:
                    t = snap.latest_trade
                    quote_data["price"] = float(t.price) if t.price else 0
                    quote_data["last_trade"] = float(t.price) if t.price else 0
                    quote_data["trade_size"] = int(t.size) if t.size else 0
                    quote_data["trade_timestamp"] = t.timestamp.isoformat() if t.timestamp else None

                if snap.daily_bar:
                    db = snap.daily_bar
                    quote_data["open"] = float(db.open) if db.open else 0
                    quote_data["high"] = float(db.high) if db.high else 0
                    quote_data["low"] = float(db.low) if db.low else 0
                    quote_data["close"] = float(db.close) if db.close else 0
                    quote_data["volume"] = int(db.volume) if db.volume else 0
                    quote_data["vwap"] = float(db.vwap) if db.vwap else 0

                if snap.previous_daily_bar:
                    pdb = snap.previous_daily_bar
                    quote_data["prev_close"] = float(pdb.close) if pdb.close else 0
                    quote_data["prev_volume"] = int(pdb.volume) if pdb.volume else 0

                if quote_data.get("price") and quote_data.get("prev_close"):
                    prev = quote_data["prev_close"]
                    curr = quote_data["price"]
                    quote_data["change"] = round(curr - prev, 2)
                    quote_data["change_pct"] = round((curr - prev) / prev * 100, 2) if prev else 0

                if quote_data.get("price"):
                    quotes[symbol] = quote_data

        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "too many requests" in error_str:
                raise  # Re-raise rate limit errors
            logger.debug(f"Batch fetch error: {e}")

        return quotes

    def _refresh_all_quotes(self) -> None:
        """Fetch snapshots for all universe symbols - FAST with max batch size"""
        try:
            # Use maximum batch size (100) for fewest API calls
            batches = [
                self._universe[i:i + BATCH_SIZE]
                for i in range(0, len(self._universe), BATCH_SIZE)
            ]

            all_quotes = {}

            # Sequential fetching (parallel can cause rate limits)
            for batch in batches:
                if self._is_rate_limited():
                    break  # Stop if we hit rate limit

                try:
                    batch_quotes = self._fetch_batch(batch)
                    all_quotes.update(batch_quotes)
                except Exception as e:
                    self._handle_rate_limit_error(e)
                    break

            # Update cache atomically
            if all_quotes:
                with self._cache_lock:
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
        Get historical bars from Alpaca - FAST with caching.

        Args:
            symbol: Stock symbol
            duration: Time period (e.g., "1 D", "5 D", "1 M")
            bar_size: Bar size (e.g., "1 min", "5 mins", "1 hour")

        Returns:
            List of bar dictionaries with OHLCV data
        """
        # Check cache first - INSTANT
        cache_key = self._get_bars_cache_key(symbol, duration, bar_size)
        cached = self._get_cached_bars(cache_key)
        if cached is not None:
            return cached

        # If rate limited, return empty (don't block)
        if self._is_rate_limited():
            logger.debug(f"Rate limited, skipping bars fetch for {symbol}")
            return []

        try:
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

            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=timeframe,
                start=start_date,
                end=end_date
            )

            bars_response = self.data_client.get_stock_bars(request)
            bars_data = bars_response.data if hasattr(bars_response, 'data') else bars_response

            if symbol not in bars_data:
                return []

            bars = [
                {
                    "date": bar.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "open": float(bar.open),
                    "high": float(bar.high),
                    "low": float(bar.low),
                    "close": float(bar.close),
                    "volume": int(bar.volume)
                }
                for bar in bars_data[symbol]
            ]

            # Cache the results
            if bars:
                self._set_cached_bars(cache_key, bars)
                self._reset_backoff()

            return bars

        except Exception as e:
            self._handle_rate_limit_error(e)
            logger.debug(f"Error fetching bars for {symbol}: {e}")
            return []

    def get_latest_bar(self, symbol: str) -> Dict[str, Any]:
        """
        Get latest bar for a symbol - INSTANT from cache, fallback to API.

        Args:
            symbol: Stock symbol

        Returns:
            Latest bar dict or empty dict if error
        """
        # Try cache first - INSTANT, no API call
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

        # If rate limited, return empty (don't block)
        if self._is_rate_limited():
            return {}

        # Fallback to API call only if not in cache
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quote = self.data_client.get_stock_latest_quote(request)

            if symbol not in quote:
                return {}

            q = quote[symbol]
            self._reset_backoff()

            return {
                "date": q.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "open": float(q.bid_price),
                "high": float(q.ask_price),
                "low": float(q.bid_price),
                "close": float((q.bid_price + q.ask_price) / 2),
                "volume": int(q.bid_size + q.ask_size)
            }

        except Exception as e:
            self._handle_rate_limit_error(e)
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

        # If rate limited or not in cache, return empty (don't block)
        if self._is_rate_limited():
            return {}

        # Try direct fetch (rare case - most data comes from cache/streaming)
        try:
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
