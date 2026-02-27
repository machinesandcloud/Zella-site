from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path
import json
import logging

from core.ibkr_webapi import IBKRWebAPIClient
from market.market_data_provider import MarketDataProvider
from market.universe import get_default_universe

logger = logging.getLogger("webapi_provider")

# Persistent watchlist file
WATCHLIST_FILE = Path("data/custom_watchlist.json")


class IBKRWebAPIProvider(MarketDataProvider):
    def __init__(self, client: IBKRWebAPIClient) -> None:
        self.client = client
        self._default_universe = get_default_universe()
        self._custom_symbols: List[str] = []
        self._load_custom_watchlist()
        self._universe = list(set(self._default_universe + self._custom_symbols))

    def get_universe(self) -> List[str]:
        return self._universe

    def get_historical_bars(self, symbol: str, duration: str, bar_size: str) -> List[Dict[str, Any]]:
        period_map = {
            "1 D": "1d",
            "5 D": "5d",
            "1 W": "5d",
            "1 M": "1m",
            "3 M": "3m",
            "6 M": "6m",
            "1 Y": "1y",
        }
        bar_map = {
            "1 min": "1min",
            "5 mins": "5min",
            "15 mins": "15min",
            "1 hour": "1h",
            "1 day": "1d",
        }
        period = period_map.get(duration, "1d")
        bar = bar_map.get(bar_size, "5min")
        return self.client.get_historical_bars(symbol, period=period, bar=bar)

    def get_latest_bar(self, symbol: str) -> Dict[str, Any]:
        return self.client.get_market_snapshot(symbol)

    def get_market_snapshot(self, symbol: str) -> Dict[str, Any]:
        return self.client.get_market_snapshot(symbol)

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
        symbols = [s.upper().strip() for s in symbols if s.strip()]
        custom = [s for s in symbols if s not in self._default_universe]

        self._custom_symbols = custom
        self._universe = list(set(self._default_universe + custom))
        self._save_custom_watchlist()

        return {
            "total_symbols": len(self._universe),
            "custom_symbols": self._custom_symbols.copy()
        }
