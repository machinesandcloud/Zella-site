from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy


class ORBStrategy(BaseStrategy):
    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.opening_range_minutes = int(params.get("opening_range_minutes", 15))
        self.breakout_buffer = float(params.get("breakout_buffer", 0.05))
        self.quantity = int(params.get("quantity", 1))

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        df = self._to_df(data)
        if df is None or len(df) < 2:
            return []

        bar_interval = int(data.get("bar_interval_minutes", 1))
        opening_bars = max(int(self.opening_range_minutes / bar_interval), 1)
        if len(df) < opening_bars + 1:
            return []

        opening_range = df.iloc[:opening_bars]
        range_high = opening_range["high"].max()
        range_low = opening_range["low"].min()
        last_close = df.iloc[-1]["close"]

        if last_close > range_high + self.breakout_buffer:
            return [Signal(symbol=symbol, action="BUY", quantity=self.quantity, order_type="MKT")]
        if last_close < range_low - self.breakout_buffer:
            return [Signal(symbol=symbol, action="SELL", quantity=self.quantity, order_type="MKT")]
        return []

    def _to_df(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        if "df" in data and isinstance(data["df"], pd.DataFrame):
            return data["df"]
        history = data.get("history")
        if history:
            return pd.DataFrame(history)
        return None
