from typing import Any, Dict, List

from core.signals import Signal
from strategies.base_strategy import BaseStrategy


class EarningsOverreactionStrategy(BaseStrategy):
    """Fade the initial earnings move if it is extreme."""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.move_threshold = float(params.get("move_threshold", 5.0))
        self.quantity = int(params.get("quantity", 1))

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        if data.get("event") != "EARNINGS":
            return []
        move = data.get("first_move_pct")
        if move is None or abs(move) < self.move_threshold:
            return []
        action = "SELL" if move > 0 else "BUY"
        return [Signal(symbol=symbol, action=action, quantity=self.quantity, order_type="MKT")]
