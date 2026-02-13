from __future__ import annotations

from typing import Any, Dict, List, Optional
import time

import httpx

from market.market_data_provider import MarketDataProvider
from market.universe import get_default_universe


class FreeMarketDataProvider(MarketDataProvider):
    def __init__(self, universe: Optional[List[str]] = None) -> None:
        self._universe = universe or get_default_universe()
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
        payload = self._yahoo_quote([symbol])
        results = payload.get("quoteResponse", {}).get("result", [])
        if not results:
            return {}
        quote = results[0]
        return {
            "symbol": symbol,
            "price": quote.get("regularMarketPrice"),
            "volume": quote.get("regularMarketVolume"),
            "timestamp": quote.get("regularMarketTime"),
        }
