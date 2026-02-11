from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy


class ClosingBellLiquidityGrabStrategy(BaseStrategy):
    """Late-day selloff then last-minute rip."""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.quantity = int(params.get("quantity", 1))
        self.minutes_to_close = int(params.get("minutes_to_close", 2))

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        time_to_close = data.get("time_to_close_minutes")
        df = self._to_df(data)
        if time_to_close is None or df is None or len(df) < 3:
            return []
        if time_to_close > self.minutes_to_close:
            return []

        last = df.iloc[-1]
        prev = df.iloc[-2]
        earlier = df.iloc[-3]
        if earlier["close"] > prev["close"] and last["close"] > prev["close"]:
            return [Signal(symbol=symbol, action="BUY", quantity=self.quantity, order_type="MKT")]
        return []

    def _to_df(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        if "df" in data and isinstance(data["df"], pd.DataFrame):
            return data["df"]
        history = data.get("history")
        if history:
            return pd.DataFrame(history)
        return None
