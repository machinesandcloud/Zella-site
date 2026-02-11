from typing import Any, Dict, List

from core.signals import Signal
from strategies.base_strategy import BaseStrategy


class BigBidScalpStrategy(BaseStrategy):
    """Scalp when a large bid appears on level 2."""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.min_bid_size = float(params.get("min_bid_size", 10000))
        self.price_tolerance = float(params.get("price_tolerance", 0.05))
        self.quantity = int(params.get("quantity", 1))

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        bid_size = data.get("bid_size")
        bid_price = data.get("bid_price")
        last_price = data.get("last_price")
        if bid_size is None or bid_price is None or last_price is None:
            return []

        if bid_size >= self.min_bid_size and last_price <= bid_price + self.price_tolerance:
            return [Signal(symbol=symbol, action="BUY", quantity=self.quantity, order_type="MKT")]
        return []
