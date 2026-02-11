from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy


class DarkPoolFootprintsStrategy(BaseStrategy):
    """Trade near dark pool levels with supplied bias."""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.tolerance = float(params.get("tolerance", 0.1))
        self.quantity = int(params.get("quantity", 1))

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        levels = data.get("dark_pool_levels") or []
        bias = data.get("dark_pool_bias")
        df = self._to_df(data)
        if df is None or not levels or bias not in {"BUY", "SELL"}:
            return []

        last_close = df["close"].iloc[-1]
        for level in levels:
            if abs(last_close - level) <= self.tolerance:
                return [Signal(symbol=symbol, action=bias, quantity=self.quantity, order_type="MKT")]
        return []

    def _to_df(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        if "df" in data and isinstance(data["df"], pd.DataFrame):
            return data["df"]
        history = data.get("history")
        if history:
            return pd.DataFrame(history)
        return None
