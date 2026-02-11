from typing import Any, Dict, List

from core.signals import Signal
from strategies.base_strategy import BaseStrategy


class MergerArbStrategy(BaseStrategy):
    """Short when price trades above announced deal price."""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.buffer = float(params.get("buffer", 0.05))
        self.quantity = int(params.get("quantity", 1))

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        deal_price = data.get("deal_price")
        last_price = data.get("last_price")
        if deal_price is None or last_price is None:
            return []
        if last_price > deal_price + self.buffer:
            return [Signal(symbol=symbol, action="SELL", quantity=self.quantity, order_type="MKT")]
        return []
