from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy


class BagholderBounceStrategy(BaseStrategy):
    """Gap down big, flush, then bounce."""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.gap_down_pct = float(params.get("gap_down_pct", 20.0))
        self.quantity = int(params.get("quantity", 1))

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        gap_pct = data.get("gap_pct")
        df = self._to_df(data)
        if df is None or len(df) < 2 or gap_pct is None:
            return []
        if gap_pct > -self.gap_down_pct:
            return []

        prev = df.iloc[-2]
        last = df.iloc[-1]
        flushed = prev["close"] < prev["open"] and last["close"] > last["open"]
        if flushed:
            return [Signal(symbol=symbol, action="BUY", quantity=self.quantity, order_type="MKT")]
        return []

    def _to_df(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        if "df" in data and isinstance(data["df"], pd.DataFrame):
            return data["df"]
        history = data.get("history")
        if history:
            return pd.DataFrame(history)
        return None
