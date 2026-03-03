"""
Dynamic Universe Manager - Auto-updates daily with most liquid stocks

Fetches the most actively traded stocks from market data sources
and updates the trading universe automatically every business day
after market open (9:30 AM ET).
"""

import json
import logging
import os
from datetime import datetime, timedelta, time
from pathlib import Path
from typing import List, Dict, Any, Optional
import threading
import pytz

logger = logging.getLogger("dynamic_universe")

# File to store the dynamic universe
DYNAMIC_UNIVERSE_FILE = Path("data/dynamic_universe.json")
UNIVERSE_VERSION = 3

# Update settings
UPDATE_AFTER_MARKET_OPEN = time(9, 35)  # 9:35 AM ET (5 mins after open)
ET_TIMEZONE = pytz.timezone("America/New_York")

# Fallback core stocks (always included, never removed)
CORE_STOCKS = [
    # Mega cap tech - always liquid
    "AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "META", "GOOGL", "AMD", "NFLX",
    # Key ETFs
    "SPY", "QQQ", "IWM", "DIA",
    # Leveraged ETFs (day trading favorites)
    "TQQQ", "SQQQ", "SOXL", "SOXS", "UVXY",
]


class DynamicUniverseManager:
    """
    Manages a dynamically updated stock universe based on liquidity.

    Updates weekly by fetching the most actively traded stocks.
    Falls back to a static list if updates fail.
    """

    def __init__(self, alpaca_api_key: Optional[str] = None, alpaca_secret_key: Optional[str] = None):
        self.api_key = alpaca_api_key
        self.secret_key = alpaca_secret_key
        self._universe: List[str] = []
        self._last_update: Optional[datetime] = None
        self._file_version = UNIVERSE_VERSION
        self._lock = threading.Lock()

        # Load existing universe or initialize
        self._load_universe()

        # Check if update needed
        if self._needs_update():
            # Run update in background to not block startup
            threading.Thread(target=self._update_universe_background, daemon=True).start()

    def _load_universe(self) -> None:
        """Load universe from file or use defaults"""
        try:
            if DYNAMIC_UNIVERSE_FILE.exists():
                with open(DYNAMIC_UNIVERSE_FILE, 'r') as f:
                    data = json.load(f)
                    self._universe = data.get("symbols", [])
                    self._file_version = data.get("version", 1)
                    last_update_str = data.get("last_update")
                    if last_update_str:
                        self._last_update = datetime.fromisoformat(last_update_str)
                    logger.info(f"Loaded dynamic universe: {len(self._universe)} symbols, last update: {self._last_update}")
            else:
                # Use static fallback
                self._universe = self._get_static_fallback()
                logger.info(f"No dynamic universe file, using static fallback: {len(self._universe)} symbols")
        except Exception as e:
            logger.error(f"Error loading dynamic universe: {e}")
            self._universe = self._get_static_fallback()

    def _save_universe(self) -> None:
        """Save universe to file"""
        try:
            DYNAMIC_UNIVERSE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(DYNAMIC_UNIVERSE_FILE, 'w') as f:
                json.dump({
                    "symbols": self._universe,
                    "last_update": self._last_update.isoformat() if self._last_update else None,
                    "count": len(self._universe),
                    "version": UNIVERSE_VERSION,
                }, f, indent=2)
            logger.info(f"Saved dynamic universe: {len(self._universe)} symbols")
        except Exception as e:
            logger.error(f"Error saving dynamic universe: {e}")

    def _needs_update(self) -> bool:
        """
        Check if universe needs updating.

        Updates daily after market open (9:35 AM ET) on business days.
        """
        if not self._last_update:
            return True
        if getattr(self, "_file_version", UNIVERSE_VERSION) != UNIVERSE_VERSION:
            return True

        now_et = datetime.now(ET_TIMEZONE)
        today = now_et.date()

        # Only update on business days (Monday=0 through Friday=4)
        if now_et.weekday() > 4:  # Saturday or Sunday
            return False

        # Only update after market open (9:35 AM ET)
        if now_et.time() < UPDATE_AFTER_MARKET_OPEN:
            return False

        # Check if we already updated today
        last_update_date = self._last_update.date() if self._last_update else None

        # Need update if we haven't updated today
        return last_update_date != today

    def _get_static_fallback(self) -> List[str]:
        """Get static fallback universe"""
        from market.universe import get_day_trading_universe
        return get_day_trading_universe()

    def _update_universe_background(self) -> None:
        """Update universe in background thread"""
        try:
            logger.info("Starting weekly universe update...")
            new_universe = self._fetch_most_liquid_stocks()

            if new_universe and len(new_universe) >= 50:
                with self._lock:
                    self._universe = new_universe
                    self._last_update = datetime.now()
                    self._save_universe()
                logger.info(f"Universe updated successfully: {len(new_universe)} symbols")
            else:
                logger.warning(f"Update returned too few stocks ({len(new_universe) if new_universe else 0}), keeping existing universe")
        except Exception as e:
            logger.error(f"Failed to update universe: {e}")

    def _fetch_most_liquid_stocks(self) -> List[str]:
        """
        Fetch the most liquid stocks from market data.

        Strategy:
        1. Use historical daily liquidity + screener criteria to build a high-quality list
        2. Fallback to Alpaca tradeable/shortable list
        3. Fallback to Yahoo most-active list
        4. Fallback to curated list
        5. Combine with core stocks and return top 100
        """
        most_active = []

        # Method 1: Historical liquidity + criteria from Alpaca daily bars
        if self.api_key and self.secret_key:
            try:
                most_active = self._fetch_from_alpaca_history()
                if most_active:
                    logger.info(f"Got {len(most_active)} stocks from Alpaca historical liquidity")
            except Exception as e:
                logger.warning(f"Alpaca historical fetch failed: {e}")

        # Method 2: Try Alpaca API (tradeable/shortable)
        if not most_active and self.api_key and self.secret_key:
            try:
                most_active = self._fetch_from_alpaca()
                if most_active:
                    logger.info(f"Got {len(most_active)} stocks from Alpaca")
            except Exception as e:
                logger.warning(f"Alpaca fetch failed: {e}")

        # Method 3: Try free Yahoo Finance screener
        if not most_active:
            try:
                most_active = self._fetch_from_yahoo()
                if most_active:
                    logger.info(f"Got {len(most_active)} stocks from Yahoo")
            except Exception as e:
                logger.warning(f"Yahoo fetch failed: {e}")

        # Method 4: Use curated list based on known high-volume stocks
        if not most_active:
            most_active = self._get_curated_high_volume()
            logger.info(f"Using curated high-volume list: {len(most_active)} stocks")

        # Always include core stocks first, then fill with highest-liquidity list
        final_universe = self._dedupe_preserve_order(CORE_STOCKS + most_active)

        # Limit to 100 stocks
        return final_universe[:100]

    @staticmethod
    def _dedupe_preserve_order(symbols: List[str]) -> List[str]:
        seen = set()
        ordered = []
        for symbol in symbols:
            if symbol in seen:
                continue
            seen.add(symbol)
            ordered.append(symbol)
        return ordered

    @staticmethod
    def _extract_bar_value(bar: Any, field: str) -> Optional[float]:
        if isinstance(bar, dict):
            return bar.get(field)
        return getattr(bar, field, None)

    @staticmethod
    def _normalize_bars(bars: Any) -> List[Any]:
        if bars is None:
            return []
        if isinstance(bars, list):
            return bars
        try:
            import pandas as pd
            if isinstance(bars, pd.DataFrame):
                if bars.empty:
                    return []
                return bars.sort_index().to_dict("records")
        except Exception:
            pass
        try:
            return list(bars)
        except Exception:
            return []

    def _fetch_from_alpaca_history(self) -> List[str]:
        """
        Build universe using historical daily liquidity and screener criteria.
        Uses 20-day averages to approximate "historically high volume" names.
        """
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame
        from market.universe import get_full_500_universe
        from config.settings import settings

        symbols = get_full_500_universe()
        if not symbols:
            return []

        client = StockHistoricalDataClient(self.api_key, self.secret_key)
        end = datetime.now()
        start = end - timedelta(days=90)

        results: List[Dict[str, Any]] = []
        liquidity_pool: List[Dict[str, Any]] = []
        evaluated = 0

        batch_size = 200
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            request = StockBarsRequest(
                symbol_or_symbols=batch,
                timeframe=TimeFrame.Day,
                start=start,
                end=end,
                feed=settings.alpaca_data_feed,
            )
            bars_response = client.get_stock_bars(request)
            if hasattr(bars_response, "data"):
                bars_data = bars_response.data
                items_iter = bars_data.items()
            elif hasattr(bars_response, "df"):
                bars_data = bars_response.df
                items_iter = bars_data.groupby(level=0)
            else:
                bars_data = bars_response
                items_iter = bars_data.items() if hasattr(bars_data, "items") else []

            for symbol, bars in items_iter:
                normalized = self._normalize_bars(bars)
                if len(normalized) < 20:
                    continue

                evaluated += 1

                recent = normalized[-20:]
                volume_sum = 0.0
                dollar_sum = 0.0
                range_sum = 0.0
                valid_count = 0
                range_count = 0

                for bar in recent:
                    close = self._extract_bar_value(bar, "close")
                    volume = self._extract_bar_value(bar, "volume")
                    high = self._extract_bar_value(bar, "high")
                    low = self._extract_bar_value(bar, "low")
                    if close is None or close == 0 or volume is None:
                        continue
                    valid_count += 1
                    volume_sum += float(volume)
                    dollar_sum += float(volume) * float(close)
                    if high is not None and low is not None:
                        range_sum += (float(high) - float(low)) / float(close)
                        range_count += 1

                if valid_count < 10:
                    continue

                avg_volume = volume_sum / valid_count
                avg_dollar_volume = dollar_sum / valid_count
                avg_range_pct = (range_sum / range_count) if range_count else 0.0

                last_close = None
                for bar in reversed(normalized):
                    close = self._extract_bar_value(bar, "close")
                    if close is not None and close != 0:
                        last_close = float(close)
                        break
                if last_close is None:
                    continue

                # SMA20/50 trend check
                closes = [
                    float(self._extract_bar_value(bar, "close"))
                    for bar in normalized
                    if self._extract_bar_value(bar, "close")
                ]
                if len(closes) >= 50:
                    sma20 = sum(closes[-20:]) / 20
                    sma50 = sum(closes[-50:]) / 50
                    trend_ok = last_close >= sma20 >= sma50
                else:
                    trend_ok = False

                entry = {
                    "symbol": symbol,
                    "avg_volume": avg_volume,
                    "avg_dollar_volume": avg_dollar_volume,
                    "last_close": last_close,
                }
                liquidity_pool.append(entry)

                # Apply screener-style criteria
                if avg_volume < settings.screener_min_avg_volume:
                    continue
                if not (settings.screener_min_price <= last_close <= settings.screener_max_price):
                    continue
                if avg_range_pct < settings.screener_min_volatility:
                    continue
                if settings.screener_require_daily_trend and not trend_ok:
                    continue

                results.append(entry)

        # Sort by dollar volume first, then volume
        results.sort(key=lambda r: (r["avg_dollar_volume"], r["avg_volume"]), reverse=True)
        liquidity_pool.sort(key=lambda r: (r["avg_dollar_volume"], r["avg_volume"]), reverse=True)

        logger.info(
            "Historical universe filter: %d/%d symbols passed criteria",
            len(results),
            evaluated,
        )

        target = 150
        if len(results) < target and liquidity_pool:
            seen = {r["symbol"] for r in results}
            backfill = []
            for entry in liquidity_pool:
                if entry["symbol"] in seen:
                    continue
                backfill.append(entry)
                if len(results) + len(backfill) >= target:
                    break
            if backfill:
                logger.info(
                    "Backfilled %d high-liquidity symbols to reach %d target",
                    len(backfill),
                    target,
                )
            results.extend(backfill)

        return [r["symbol"] for r in results[:target]]

    def _fetch_from_alpaca(self) -> List[str]:
        """Fetch most active stocks from Alpaca"""
        try:
            from alpaca.data.historical import StockHistoricalDataClient
            from alpaca.trading.client import TradingClient
            from alpaca.trading.requests import GetAssetsRequest
            from alpaca.trading.enums import AssetClass, AssetStatus

            # Get tradeable assets
            trading_client = TradingClient(self.api_key, self.secret_key, paper=True)

            request = GetAssetsRequest(
                asset_class=AssetClass.US_EQUITY,
                status=AssetStatus.ACTIVE
            )

            assets = trading_client.get_all_assets(request)

            # Filter for tradeable, shortable stocks (indicates liquidity)
            tradeable = [
                a.symbol for a in assets
                if a.tradable and a.shortable and a.easy_to_borrow
                and not a.symbol.endswith('.') # No special classes
                and len(a.symbol) <= 5  # No weird symbols
            ]

            logger.info(f"Found {len(tradeable)} tradeable/shortable stocks from Alpaca")

            # We don't have volume data directly, so we'll use the shortable/easy_to_borrow
            # as a proxy for liquidity (Alpaca marks liquid stocks as easy to borrow)
            # Sort by symbol length (shorter symbols tend to be more established)
            tradeable.sort(key=lambda x: (len(x), x))

            return tradeable[:150]  # Get top 150, will combine with core

        except Exception as e:
            logger.error(f"Alpaca fetch error: {e}")
            return []

    def _fetch_from_yahoo(self) -> List[str]:
        """Fetch most active stocks from Yahoo Finance"""
        try:
            import urllib.request
            import re

            # Yahoo Finance most active page
            url = "https://finance.yahoo.com/most-active"
            headers = {'User-Agent': 'Mozilla/5.0'}

            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8')

            # Extract symbols from the page (simple regex approach)
            # Yahoo uses data-symbol="AAPL" format
            symbols = re.findall(r'data-symbol="([A-Z]{1,5})"', html)

            # Deduplicate and clean
            unique_symbols = list(dict.fromkeys(symbols))

            # Filter out ETFs that might be in there (keep only stocks)
            # Actually we want some ETFs, so just return as-is
            return unique_symbols[:100]

        except Exception as e:
            logger.error(f"Yahoo fetch error: {e}")
            return []

    def _get_curated_high_volume(self) -> List[str]:
        """
        Curated list of consistently high-volume stocks.
        Updated manually but reliable.
        """
        return [
            # Mega caps (always high volume)
            "AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "META", "GOOGL", "GOOG",
            "AMD", "NFLX", "AVGO", "INTC", "QCOM", "MU", "ORCL",

            # Popular momentum / meme stocks
            "GME", "AMC", "PLTR", "NIO", "RIVN", "LCID", "COIN", "HOOD",
            "SOFI", "UPST", "AFRM", "IONQ", "MARA", "RIOT", "CLSK",

            # High volume financials
            "JPM", "BAC", "WFC", "C", "GS", "MS", "SCHW",

            # Popular biotechs
            "MRNA", "BNTX", "NVAX", "CRSP", "EDIT",

            # EV / Clean energy
            "XPEV", "LI", "PLUG", "FCEL", "ENPH", "BLNK", "CHPT",

            # Tech growth
            "SNOW", "DDOG", "NET", "CRWD", "ZS", "S", "PATH",
            "SQ", "PYPL", "SHOP", "SPOT", "UBER", "ABNB", "DASH",

            # Social / Internet
            "SNAP", "PINS", "ROKU", "DKNG", "RDDT",

            # Key ETFs
            "SPY", "QQQ", "IWM", "DIA", "XLF", "XLE", "XLK", "SMH", "XBI",

            # Leveraged ETFs
            "TQQQ", "SQQQ", "SOXL", "SOXS", "LABU", "LABD", "TNA", "TZA",
            "UVXY", "VXX", "SPXU", "UPRO",

            # Chinese ADRs (high volume)
            "BABA", "JD", "PDD", "NIO", "XPEV", "LI", "BIDU",

            # Semis
            "TSM", "ASML", "NXPI", "ON", "MCHP",
        ]

    def get_universe(self) -> List[str]:
        """Get the current universe"""
        with self._lock:
            return self._universe.copy()

    def force_update(self) -> Dict[str, Any]:
        """Force an immediate update of the universe"""
        try:
            new_universe = self._fetch_most_liquid_stocks()

            if new_universe and len(new_universe) >= 50:
                with self._lock:
                    old_count = len(self._universe)
                    self._universe = new_universe
                    self._last_update = datetime.now()
                    self._save_universe()

                return {
                    "success": True,
                    "old_count": old_count,
                    "new_count": len(new_universe),
                    "updated_at": self._last_update.isoformat()
                }
            else:
                return {
                    "success": False,
                    "reason": f"Too few stocks returned: {len(new_universe) if new_universe else 0}"
                }
        except Exception as e:
            return {
                "success": False,
                "reason": str(e)
            }

    def get_status(self) -> Dict[str, Any]:
        """Get status of the dynamic universe"""
        with self._lock:
            # Calculate next update time (next business day at 9:35 AM ET)
            next_update = "pending"
            if self._last_update:
                now_et = datetime.now(ET_TIMEZONE)
                # If we already updated today, next update is tomorrow (or Monday if Friday)
                next_day = now_et.date() + timedelta(days=1)
                # Skip weekends
                while next_day.weekday() > 4:
                    next_day += timedelta(days=1)
                next_update_dt = datetime.combine(next_day, UPDATE_AFTER_MARKET_OPEN)
                next_update = ET_TIMEZONE.localize(next_update_dt).isoformat()

            return {
                "symbol_count": len(self._universe),
                "last_update": self._last_update.isoformat() if self._last_update else None,
                "next_update": next_update,
                "update_schedule": "Daily at 9:35 AM ET (business days)",
                "needs_update": self._needs_update(),
                "sample_symbols": self._universe[:20] if self._universe else []
            }


# Singleton instance
_manager: Optional[DynamicUniverseManager] = None


def get_dynamic_universe_manager(api_key: Optional[str] = None, secret_key: Optional[str] = None) -> DynamicUniverseManager:
    """Get or create the dynamic universe manager"""
    global _manager
    if _manager is None:
        _manager = DynamicUniverseManager(api_key, secret_key)
    return _manager


def get_dynamic_universe() -> List[str]:
    """Get the current dynamic universe"""
    manager = get_dynamic_universe_manager()
    return manager.get_universe()
