from datetime import datetime
from typing import Any, Dict, List

from core.signals import Signal
from strategies.base_strategy import BaseStrategy


class MaxPainFadeStrategy(BaseStrategy):
    """Fade towards max pain on options expiration Friday."""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.quantity = int(params.get("quantity", 1))
        self.tolerance = float(params.get("tolerance", 0.2))

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        ts = data.get("timestamp")
        max_pain = data.get("max_pain_price")
        last_price = data.get("last_price")
        if ts is None or max_pain is None or last_price is None:
            return []
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        if ts.weekday() != 4:  # Friday
            return []
        if abs(last_price - max_pain) <= self.tolerance:
            return []
        action = "SELL" if last_price > max_pain else "BUY"
        return [Signal(symbol=symbol, action=action, quantity=self.quantity, order_type="MKT")]
