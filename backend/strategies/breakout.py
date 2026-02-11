from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy


class BreakoutStrategy(BaseStrategy):
    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.breakout_lookback = int(params.get("breakout_lookback", 20))
        self.volume_threshold = float(params.get("volume_threshold", 1.5))
        self.quantity = int(params.get("quantity", 1))

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        df = self._to_df(data)
        if df is None or len(df) < self.breakout_lookback + 1:
            return []

        recent = df.tail(self.breakout_lookback)
        high = recent["high"].max()
        low = recent["low"].min()
        last = df.iloc[-1]
        vol_avg = recent["volume"].mean()

        if last["close"] > high and last["volume"] >= vol_avg * self.volume_threshold:
            return [Signal(symbol=symbol, action="BUY", quantity=self.quantity, order_type="MKT")]
        if last["close"] < low and last["volume"] >= vol_avg * self.volume_threshold:
            return [Signal(symbol=symbol, action="SELL", quantity=self.quantity, order_type="MKT")]
        return []

    def _to_df(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        if "df" in data and isinstance(data["df"], pd.DataFrame):
            return data["df"]
        history = data.get("history")
        if history:
            return pd.DataFrame(history)
        return None
