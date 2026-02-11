from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy
from utils.indicators import ema


class EMACrossStrategy(BaseStrategy):
    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.fast_ema = int(params.get("fast_ema", 20))
        self.slow_ema = int(params.get("slow_ema", 50))
        self.quantity = int(params.get("quantity", 1))
        self._last_signal = None

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        df = self._to_df(data)
        if df is None or len(df) < self.slow_ema:
            return []

        fast = ema(df["close"], self.fast_ema)
        slow = ema(df["close"], self.slow_ema)

        if fast.iloc[-2] <= slow.iloc[-2] and fast.iloc[-1] > slow.iloc[-1]:
            if self._last_signal != "BUY":
                self._last_signal = "BUY"
                return [Signal(symbol=symbol, action="BUY", quantity=self.quantity, order_type="MKT")]

        if fast.iloc[-2] >= slow.iloc[-2] and fast.iloc[-1] < slow.iloc[-1]:
            if self._last_signal != "SELL":
                self._last_signal = "SELL"
                return [Signal(symbol=symbol, action="SELL", quantity=self.quantity, order_type="MKT")]

        return []

    def _to_df(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        if "df" in data and isinstance(data["df"], pd.DataFrame):
            return data["df"]
        history = data.get("history")
        if history:
            return pd.DataFrame(history)
        return None
