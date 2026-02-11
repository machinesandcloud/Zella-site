from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy


class StopHuntReversalStrategy(BaseStrategy):
    """Reversal after pushing past previous day high/low."""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.quantity = int(params.get("quantity", 1))

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        prev_high = data.get("prev_day_high")
        prev_low = data.get("prev_day_low")
        df = self._to_df(data)
        if df is None or len(df) < 1 or prev_high is None or prev_low is None:
            return []

        last = df.iloc[-1]
        if last["high"] > prev_high and last["close"] < prev_high:
            return [Signal(symbol=symbol, action="SELL", quantity=self.quantity, order_type="MKT")]
        if last["low"] < prev_low and last["close"] > prev_low:
            return [Signal(symbol=symbol, action="BUY", quantity=self.quantity, order_type="MKT")]
        return []

    def _to_df(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        if "df" in data and isinstance(data["df"], pd.DataFrame):
            return data["df"]
        history = data.get("history")
        if history:
            return pd.DataFrame(history)
        return None
