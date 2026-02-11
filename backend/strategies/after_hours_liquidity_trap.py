from typing import Any, Dict, List

from core.signals import Signal
from strategies.base_strategy import BaseStrategy


class AfterHoursLiquidityTrapStrategy(BaseStrategy):
    """After-hours pump with fading volume -> fade."""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.quantity = int(params.get("quantity", 1))
        self.spike_pct = float(params.get("spike_pct", 3.0))

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        if not data.get("after_hours"):
            return []
        volume_drop = data.get("volume_drop")
        spike_pct = data.get("price_spike_pct")
        if volume_drop and spike_pct and spike_pct >= self.spike_pct:
            return [Signal(symbol=symbol, action="SELL", quantity=self.quantity, order_type="MKT")]
        return []
