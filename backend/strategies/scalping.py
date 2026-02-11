from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy


class ScalpingStrategy(BaseStrategy):
    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.target_ticks = float(params.get("target_ticks", 3))
        self.stop_ticks = float(params.get("stop_ticks", 2))
        self.quantity = int(params.get("quantity", 1))

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        df = self._to_df(data)
        if df is None or len(df) < 2:
            return []

        last = df.iloc[-1]
        prev = df.iloc[-2]
        change = last["close"] - prev["close"]

        if change >= self.target_ticks:
            return [Signal(symbol=symbol, action="BUY", quantity=self.quantity, order_type="MKT")]
        if change <= -self.stop_ticks:
            return [Signal(symbol=symbol, action="SELL", quantity=self.quantity, order_type="MKT")]
        return []

    def _to_df(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        if "df" in data and isinstance(data["df"], pd.DataFrame):
            return data["df"]
        history = data.get("history")
        if history:
            return pd.DataFrame(history)
        return None
