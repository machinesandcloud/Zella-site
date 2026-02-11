from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy


class RipAndDipStrategy(BaseStrategy):
    """1-min break of premarket high, dip, then reclaim."""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.quantity = int(params.get("quantity", 1))

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        premarket_high = data.get("premarket_high")
        df = self._to_df(data)
        if df is None or len(df) < 2 or premarket_high is None:
            return []

        first = df.iloc[-2]
        second = df.iloc[-1]
        if first["close"] > premarket_high and second["low"] < first["low"] and second["close"] > first["close"]:
            return [Signal(symbol=symbol, action="BUY", quantity=self.quantity, order_type="MKT")]
        return []

    def _to_df(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        if "df" in data and isinstance(data["df"], pd.DataFrame):
            return data["df"]
        history = data.get("history")
        if history:
            return pd.DataFrame(history)
        return None
