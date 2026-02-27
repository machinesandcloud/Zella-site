from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path
import time
import json
import logging

import httpx

from market.market_data_provider import MarketDataProvider
from market.universe import get_default_universe

logger = logging.getLogger("free_provider")

# Persistent watchlist file
WATCHLIST_FILE = Path("data/custom_watchlist.json")


class FreeMarketDataProvider(MarketDataProvider):
    def __init__(self, universe: Optional[List[str]] = None) -> None:
        self._default_universe = get_default_universe()
        self._custom_symbols: List[str] = []
        self._load_custom_watchlist()

        # Use provided universe or build from default + custom
        if universe:
            self._universe = universe
        elif self._custom_symbols:
            self._universe = list(set(self._default_universe + self._custom_symbols))
        else:
            self._universe = self._default_universe

        self._client = httpx.Client(timeout=10.0, headers={"User-Agent": "ZellaAI/1.0"})

    def get_universe(self) -> List[str]:
        return self._universe

    def _yahoo_chart(self, symbol: str, interval: str, range_param: str) -> Dict[str, Any]:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {"interval": interval, "range": range_param}
        response = self._client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def _yahoo_quote(self, symbols: List[str]) -> Dict[str, Any]:
        url = "https://query1.finance.yahoo.com/v7/finance/quote"
        params = {"symbols": ",".join(symbols)}
        response = self._client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_historical_bars(self, symbol: str, duration: str, bar_size: str) -> List[Dict[str, Any]]:
        interval_map = {
            "1 min": "1m",
            "5 mins": "5m",
            "15 mins": "15m",
            "1 hour": "1h",
            "1 day": "1d",
        }
        range_map = {
            "1 D": "1d",
            "5 D": "5d",
            "1 W": "5d",
            "1 M": "1mo",
            "3 M": "3mo",
            "6 M": "6mo",
            "1 Y": "1y",
        }
        interval = interval_map.get(bar_size, "5m")
        range_param = range_map.get(duration, "1mo")
        payload = self._yahoo_chart(symbol, interval, range_param)
        result = payload.get("chart", {}).get("result", [])
        if not result:
            return []
        series = result[0]
        timestamps = series.get("timestamp") or []
        indicators = series.get("indicators", {}).get("quote", [{}])[0]
        opens = indicators.get("open") or []
        highs = indicators.get("high") or []
        lows = indicators.get("low") or []
        closes = indicators.get("close") or []
        volumes = indicators.get("volume") or []
        bars = []
        for idx, ts in enumerate(timestamps):
            if idx >= len(closes):
                continue
            close = closes[idx]
            if close is None:
                continue
            bars.append(
                {
                    "date": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(ts)),
                    "open": opens[idx] if idx < len(opens) else close,
                    "high": highs[idx] if idx < len(highs) else close,
                    "low": lows[idx] if idx < len(lows) else close,
                    "close": close,
                    "volume": volumes[idx] if idx < len(volumes) else 0,
                }
            )
        return bars

    def get_latest_bar(self, symbol: str) -> Dict[str, Any]:
        payload = self._yahoo_quote([symbol])
        results = payload.get("quoteResponse", {}).get("result", [])
        if not results:
            return {}
        quote = results[0]
        price = quote.get("regularMarketPrice")
        timestamp = quote.get("regularMarketTime")
        if price is None or timestamp is None:
            return {}
        return {
            "date": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(timestamp)),
            "open": quote.get("regularMarketOpen", price),
            "high": quote.get("regularMarketDayHigh", price),
            "low": quote.get("regularMarketDayLow", price),
            "close": price,
            "volume": quote.get("regularMarketVolume", 0),
        }

    def get_market_snapshot(self, symbol: str) -> Dict[str, Any]:
        """
        Get comprehensive market snapshot with all fields needed for trading decisions.
        Yahoo Finance provides rich data including OHLCV, bid/ask, and change data.
        """
        payload = self._yahoo_quote([symbol])
        results = payload.get("quoteResponse", {}).get("result", [])
        if not results:
            return {}
        quote = results[0]

        # Current price
        price = quote.get("regularMarketPrice", 0)

        # Previous close for day change calculation
        prev_close = quote.get("regularMarketPreviousClose", 0)

        # Day change (Yahoo provides these directly)
        change = quote.get("regularMarketChange", 0)
        change_pct = quote.get("regularMarketChangePercent", 0)

        # If change not provided, calculate from price and prev_close
        if change == 0 and prev_close > 0 and price > 0:
            change = price - prev_close
            change_pct = (change / prev_close) * 100

        return {
            "symbol": symbol,
            "price": price,
            # Today's OHLCV
            "open": quote.get("regularMarketOpen", 0),
            "high": quote.get("regularMarketDayHigh", 0),
            "low": quote.get("regularMarketDayLow", 0),
            "close": price,  # Current price is the running close
            "volume": quote.get("regularMarketVolume", 0),
            # Previous day
            "prev_close": prev_close,
            "prev_volume": quote.get("averageDailyVolume10Day", 0),  # Use 10-day avg as proxy
            # Day change
            "change": round(change, 2) if change else 0,
            "change_pct": round(change_pct, 2) if change_pct else 0,
            # Bid/Ask (Yahoo provides these for real-time quotes)
            "bid": quote.get("bid", 0),
            "ask": quote.get("ask", 0),
            "bid_size": quote.get("bidSize", 0),
            "ask_size": quote.get("askSize", 0),
            # Additional useful metrics
            "vwap": 0,  # Yahoo doesn't provide VWAP directly
            "avg_volume": quote.get("averageDailyVolume10Day", 0),
            "market_cap": quote.get("marketCap", 0),
            "fifty_two_week_high": quote.get("fiftyTwoWeekHigh", 0),
            "fifty_two_week_low": quote.get("fiftyTwoWeekLow", 0),
            # Timestamp
            "timestamp": quote.get("regularMarketTime", 0),
        }

    def get_batch_snapshots(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get market snapshots for multiple symbols in a single API call.
        Much faster than calling get_market_snapshot for each symbol individually.
        """
        if not symbols:
            return {}

        try:
            payload = self._yahoo_quote(symbols)
            results = payload.get("quoteResponse", {}).get("result", [])
            if not results:
                return {}

            snapshots = {}
            for quote in results:
                symbol = quote.get("symbol")
                if not symbol:
                    continue

                price = quote.get("regularMarketPrice", 0)
                prev_close = quote.get("regularMarketPreviousClose", 0)
                change = quote.get("regularMarketChange", 0)
                change_pct = quote.get("regularMarketChangePercent", 0)

                if change == 0 and prev_close > 0 and price > 0:
                    change = price - prev_close
                    change_pct = (change / prev_close) * 100

                snapshots[symbol] = {
                    "symbol": symbol,
                    "price": price,
                    "open": quote.get("regularMarketOpen", 0),
                    "high": quote.get("regularMarketDayHigh", 0),
                    "low": quote.get("regularMarketDayLow", 0),
                    "close": price,
                    "volume": quote.get("regularMarketVolume", 0),
                    "prev_close": prev_close,
                    "prev_volume": quote.get("averageDailyVolume10Day", 0),
                    "change": round(change, 2) if change else 0,
                    "change_pct": round(change_pct, 2) if change_pct else 0,
                    "bid": quote.get("bid", 0),
                    "ask": quote.get("ask", 0),
                    "bid_size": quote.get("bidSize", 0),
                    "ask_size": quote.get("askSize", 0),
                    "vwap": 0,
                    "avg_volume": quote.get("averageDailyVolume10Day", 0),
                    "market_cap": quote.get("marketCap", 0),
                    "timestamp": quote.get("regularMarketTime", 0),
                }

            return snapshots
        except Exception as e:
            return {}

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
