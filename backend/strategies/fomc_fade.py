from typing import Any, Dict, List

from core.signals import Signal
from strategies.base_strategy import BaseStrategy


class FOMCFadeStrategy(BaseStrategy):
    """Fade the initial move after FOMC minutes."""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.move_threshold = float(params.get("move_threshold", 1.0))
        self.quantity = int(params.get("quantity", 1))

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        if data.get("event") != "FOMC":
            return []
        move = data.get("initial_move_pct")
        if move is None or abs(move) < self.move_threshold:
            return []
        action = "SELL" if move > 0 else "BUY"
        return [Signal(symbol=symbol, action=action, quantity=self.quantity, order_type="MKT")]
