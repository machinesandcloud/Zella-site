from typing import Any, Dict, List

from core.signals import Signal
from strategies.base_strategy import BaseStrategy


class GammaSqueezeStrategy(BaseStrategy):
    """OTM call sweep activity implies market maker hedging."""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.quantity = int(params.get("quantity", 1))
        self.min_otm_call_volume = float(params.get("min_otm_call_volume", 1000))

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        flow = data.get("options_flow") or {}
        otm_call_volume = flow.get("otm_call_volume")
        if flow.get("otm_call_sweep"):
            return [Signal(symbol=symbol, action="BUY", quantity=self.quantity, order_type="MKT")]
        if otm_call_volume is not None and otm_call_volume >= self.min_otm_call_volume:
            return [Signal(symbol=symbol, action="BUY", quantity=self.quantity, order_type="MKT")]
        return []
