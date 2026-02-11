from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy


class BrokenParabolicShortStrategy(BaseStrategy):
    """Short after a parabolic run of green candles and first red engulfing."""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.green_count = int(params.get("green_count", 5))
        self.quantity = int(params.get("quantity", 1))

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        df = self._to_df(data)
        if df is None or len(df) < self.green_count + 1:
            return []

        recent = df.tail(self.green_count + 1)
        greens = recent.iloc[:-1]
        last = recent.iloc[-1]
        if not all(row["close"] > row["open"] for _, row in greens.iterrows()):
            return []

        prev = greens.iloc[-1]
        red_engulfing = last["close"] < last["open"] and last["open"] > prev["close"] and last["close"] < prev["open"]
        if red_engulfing:
            return [Signal(symbol=symbol, action="SELL", quantity=self.quantity, order_type="MKT")]
        return []

    def _to_df(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        if "df" in data and isinstance(data["df"], pd.DataFrame):
            return data["df"]
        history = data.get("history")
        if history:
            return pd.DataFrame(history)
        return None
