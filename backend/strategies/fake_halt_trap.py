from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy


class FakeHaltTrapStrategy(BaseStrategy):
    """Short a spike that fails to halt (requires halt flags in data)."""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.spike_pct = float(params.get("spike_pct", 5.0))
        self.quantity = int(params.get("quantity", 1))

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        halted = bool(data.get("halted", False))
        df = self._to_df(data)
        if df is None or len(df) < 2:
            return []

        last = df.iloc[-1]
        prev = df.iloc[-2]
        pct_move = ((last["close"] - prev["close"]) / prev["close"]) * 100 if prev["close"] else 0

        if pct_move >= self.spike_pct and not halted:
            return [Signal(symbol=symbol, action="SELL", quantity=self.quantity, order_type="MKT")]
        return []

    def _to_df(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        if "df" in data and isinstance(data["df"], pd.DataFrame):
            return data["df"]
        history = data.get("history")
        if history:
            return pd.DataFrame(history)
        return None
