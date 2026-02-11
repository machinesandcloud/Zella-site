from typing import Any, Dict, List, Optional

from core.ibkr_client import IBKRClient
from market.market_data_provider import MarketDataProvider


class IBKRMarketDataProvider(MarketDataProvider):
    def __init__(self, ibkr_client: IBKRClient, universe: Optional[List[str]] = None, use_scanner: bool = True) -> None:
        self.ibkr_client = ibkr_client
        self._universe = universe or []
        self.use_scanner = use_scanner

    def get_universe(self) -> List[str]:
        if self._universe:
            return self._universe
        if self.use_scanner and self.ibkr_client.is_connected():
            return self.ibkr_client.scan_top_movers()
        return []

    def get_historical_bars(self, symbol: str, duration: str, bar_size: str) -> List[Dict[str, Any]]:
        if not self.ibkr_client.is_connected():
            return []
        return self.ibkr_client.fetch_historical_data(symbol, duration, bar_size, "TRADES")

    def get_latest_bar(self, symbol: str) -> Dict[str, Any]:
        # Placeholder for latest bar via real-time bars
        return {}

    def get_market_snapshot(self, symbol: str) -> Dict[str, Any]:
        # Placeholder for snapshot data (IBKR reqMktData)
        return {}
