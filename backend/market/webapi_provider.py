from __future__ import annotations

from typing import Any, Dict, List

from core.ibkr_webapi import IBKRWebAPIClient
from market.market_data_provider import MarketDataProvider


class IBKRWebAPIProvider(MarketDataProvider):
    def __init__(self, client: IBKRWebAPIClient) -> None:
        self.client = client

    def get_universe(self) -> List[str]:
        return []

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
