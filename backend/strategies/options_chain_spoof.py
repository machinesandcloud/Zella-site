from typing import Any, Dict, List

from core.signals import Signal
from strategies.base_strategy import BaseStrategy


class OptionsChainSpoofStrategy(BaseStrategy):
    """Use options sweep activity as a directional signal."""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.quantity = int(params.get("quantity", 1))

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        options_flow = data.get("options_flow") or {}
        if options_flow.get("call_sweep"):
            return [Signal(symbol=symbol, action="BUY", quantity=self.quantity, order_type="MKT")]
        if options_flow.get("put_sweep"):
            return [Signal(symbol=symbol, action="SELL", quantity=self.quantity, order_type="MKT")]
        return []
