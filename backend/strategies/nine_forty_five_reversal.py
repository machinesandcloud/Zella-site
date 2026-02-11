from datetime import datetime, time
from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy


class NineFortyFiveReversalStrategy(BaseStrategy):
    """Reversal around 9:45am after initial retail-driven move."""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.quantity = int(params.get("quantity", 1))
        self.window_minutes = int(params.get("window_minutes", 5))

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        ts = data.get("timestamp")
        if ts is None:
            return []
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)

        target = time(9, 45)
        delta = abs((datetime.combine(ts.date(), ts.time()) - datetime.combine(ts.date(), target)).total_seconds())
        if delta > self.window_minutes * 60:
            return []

        df = self._to_df(data)
        if df is None or len(df) < 2:
            return []

        early_move = data.get("early_move")  # "UP" or "DOWN"
        last = df.iloc[-1]
        if early_move == "UP" and last["close"] < last["open"]:
            return [Signal(symbol=symbol, action="SELL", quantity=self.quantity, order_type="MKT")]
        if early_move == "DOWN" and last["close"] > last["open"]:
            return [Signal(symbol=symbol, action="BUY", quantity=self.quantity, order_type="MKT")]
        return []

    def _to_df(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        if "df" in data and isinstance(data["df"], pd.DataFrame):
            return data["df"]
        history = data.get("history")
        if history:
            return pd.DataFrame(history)
        return None
