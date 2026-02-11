from typing import Any, Dict, List, Protocol


class MarketDataProvider(Protocol):
    def get_universe(self) -> List[str]:
        ...

    def get_historical_bars(self, symbol: str, duration: str, bar_size: str) -> List[Dict[str, Any]]:
        ...

    def get_latest_bar(self, symbol: str) -> Dict[str, Any]:
        ...

    def get_market_snapshot(self, symbol: str) -> Dict[str, Any]:
        ...
