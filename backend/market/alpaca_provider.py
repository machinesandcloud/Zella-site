"""Alpaca Market Data Provider for day trading universe"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import logging

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
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
    - No mock data - 100% real market information
    """

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        universe: Optional[List[str]] = None
    ) -> None:
        """
        Initialize Alpaca market data provider.

        Args:
            api_key: Alpaca API key
            secret_key: Alpaca secret key
            universe: Optional custom universe (defaults to day trading universe)
        """
        self.api_key = api_key
        self.secret_key = secret_key

        # Use day trading universe by default
        self._universe = universe or get_default_universe()

        # Alpaca market data client
        self.data_client = StockHistoricalDataClient(
            api_key=api_key,
            secret_key=secret_key
        )

        logger.info(f"Alpaca Market Data Provider initialized with {len(self._universe)} symbols")

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
        Get market snapshot for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Snapshot dict with price, volume, etc.
        """
        try:
            request = StockLatestQuoteRequest(
                symbol_or_symbols=symbol
            )

            quote = self.data_client.get_stock_latest_quote(request)

            if symbol not in quote:
                return {}

            q = quote[symbol]
            mid_price = (q.bid_price + q.ask_price) / 2

            return {
                "symbol": symbol,
                "price": float(mid_price),
                "bid": float(q.bid_price),
                "ask": float(q.ask_price),
                "bid_size": int(q.bid_size),
                "ask_size": int(q.ask_size),
                "volume": int(q.bid_size + q.ask_size),
                "timestamp": q.timestamp.isoformat()
            }

        except Exception as e:
            logger.error(f"Error fetching snapshot for {symbol}: {e}")
            return {}
