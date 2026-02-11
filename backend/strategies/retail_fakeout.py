from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy


class RetailFakeoutStrategy(BaseStrategy):
    """Breakdown below support then quick reclaim = long (or inverse)."""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.support_level = params.get("support_level")
        self.resistance_level = params.get("resistance_level")
        self.quantity = int(params.get("quantity", 1))

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        df = self._to_df(data)
        support = data.get("support_level", self.support_level)
        resistance = data.get("resistance_level", self.resistance_level)
        if df is None or len(df) < 2:
            return []

        prev = df.iloc[-2]
        last = df.iloc[-1]

        if support is not None:
            fake_break = prev["close"] < support and last["close"] > support
            if fake_break:
                return [Signal(symbol=symbol, action="BUY", quantity=self.quantity, order_type="MKT")]

        if resistance is not None:
            fake_break = prev["close"] > resistance and last["close"] < resistance
            if fake_break:
                return [Signal(symbol=symbol, action="SELL", quantity=self.quantity, order_type="MKT")]

        return []

    def _to_df(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        if "df" in data and isinstance(data["df"], pd.DataFrame):
            return data["df"]
        history = data.get("history")
        if history:
            return pd.DataFrame(history)
        return None
