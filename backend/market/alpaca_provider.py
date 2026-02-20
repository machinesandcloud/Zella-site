"""Alpaca Market Data Provider for day trading universe"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import logging
import threading
import time

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest, StockSnapshotRequest, StockLatestTradeRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from market.market_data_provider import MarketDataProvider
from market.universe import get_default_universe

logger = logging.getLogger("alpaca_provider")


class AlpacaMarketDataProvider(MarketDataProvider):
    """
    Market data provider using Alpaca's free market data API.

    Provides:
    - Day trading universe (90+ high volume stocks)
    - Real-time and historical data via Alpaca
    - Batch quote fetching for efficiency
    - Caching to avoid rate limits
    """

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        universe: Optional[List[str]] = None,
        cache_ttl: float = 0.5  # Cache TTL in seconds (500ms for day trading)
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

        # Use day trading universe by default
        self._universe = universe or get_default_universe()

        # Alpaca market data client
        self.data_client = StockHistoricalDataClient(
            api_key=api_key,
            secret_key=secret_key
        )

        # Quote cache for fast lookups
        self._quote_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamp: float = 0
        self._cache_lock = threading.Lock()

        # Start background refresh thread
        self._refresh_thread = threading.Thread(target=self._background_refresh, daemon=True)
        self._refresh_thread.start()

        logger.info(f"Alpaca Market Data Provider initialized with {len(self._universe)} symbols")

    def _background_refresh(self) -> None:
        """Background thread to continuously refresh quotes"""
        while True:
            try:
                self._refresh_all_quotes()
            except Exception as e:
                logger.debug(f"Background refresh error: {e}")
            time.sleep(self.cache_ttl)

    def _refresh_all_quotes(self) -> None:
        """Fetch snapshots for all universe symbols in batches using Snapshot API"""
        try:
            # Batch symbols (Alpaca allows up to 100 per request)
            batch_size = 50
            all_quotes = {}

            for i in range(0, len(self._universe), batch_size):
                batch = self._universe[i:i + batch_size]
                try:
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
                    logger.debug(f"Error fetching snapshot batch {i}-{i+batch_size}: {e}")

            # Update cache atomically
            with self._cache_lock:
                self._quote_cache = all_quotes
                self._cache_timestamp = time.time()

            logger.debug(f"Refreshed {len(all_quotes)} snapshots")

        except Exception as e:
            logger.error(f"Error refreshing snapshots: {e}")

    def get_universe(self) -> List[str]:
        """Get the trading universe (90+ day trading stocks)"""
        return self._universe

    def get_historical_bars(
        self,
        symbol: str,
        duration: str,
        bar_size: str
    ) -> List[Dict[str, Any]]:
        """
        Get historical bars from Alpaca.

        Args:
            symbol: Stock symbol
            duration: Time period (e.g., "1 D", "5 D", "1 M")
            bar_size: Bar size (e.g., "1 min", "5 mins", "1 hour")

        Returns:
            List of bar dictionaries with OHLCV data
        """
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

            logger.debug(f"Retrieved {len(bars)} bars for {symbol}")
            return bars

        except Exception as e:
            logger.error(f"Error fetching bars for {symbol}: {e}")
            return []

    def get_latest_bar(self, symbol: str) -> Dict[str, Any]:
        """
        Get latest bar for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Latest bar dict or empty dict if error
        """
        try:
            request = StockLatestQuoteRequest(
                symbol_or_symbols=symbol
            )

            quote = self.data_client.get_stock_latest_quote(request)

            if symbol not in quote:
                return {}

            q = quote[symbol]

            return {
                "date": q.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "open": float(q.bid_price),  # Use bid as proxy for open
                "high": float(q.ask_price),  # Use ask as proxy for high
                "low": float(q.bid_price),   # Use bid as proxy for low
                "close": float((q.bid_price + q.ask_price) / 2),  # Mid price
                "volume": int(q.bid_size + q.ask_size)
            }

        except Exception as e:
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

        # If not in cache, try direct fetch (rare case)
        try:
            request = StockLatestTradeRequest(symbol_or_symbols=symbol)
            trades = self.data_client.get_stock_latest_trade(request)

            if symbol in trades:
                t = trades[symbol]
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
            logger.debug(f"Error fetching snapshot for {symbol}: {e}")

        return {}
