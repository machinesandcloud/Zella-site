from typing import Any, Dict, List

from core.signals import Signal
from strategies.base_strategy import BaseStrategy


class OpenInterestFakeoutStrategy(BaseStrategy):
    """Breaks a heavy OI strike then fails; trade the reversal."""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.quantity = int(params.get("quantity", 1))

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        oi_break = data.get("oi_break")
        failed_break = data.get("failed_break")
        break_direction = data.get("break_direction")  # "UP" or "DOWN"
        if not oi_break or not failed_break or break_direction is None:
            return []

        action = "SELL" if break_direction == "UP" else "BUY"
        return [Signal(symbol=symbol, action=action, quantity=self.quantity, order_type="MKT")]
