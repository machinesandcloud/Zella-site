from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy


class FirstHourTrendStrategy(BaseStrategy):
    """
    Locks in the first-hour direction and trades with it.
    Expects data key: first_hour_df (DataFrame of first hour candles) or session_open/close.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.quantity = int(params.get("quantity", 1))
        self.locked_direction: Optional[str] = None

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        if self.locked_direction is None:
            first_hour_df = data.get("first_hour_df")
            if first_hour_df is not None and isinstance(first_hour_df, pd.DataFrame):
                open_price = first_hour_df.iloc[0]["open"]
                close_price = first_hour_df.iloc[-1]["close"]
                self.locked_direction = "BUY" if close_price >= open_price else "SELL"
            else:
                session_open = data.get("session_open")
                session_close = data.get("session_close")
                if session_open and session_close:
                    self.locked_direction = "BUY" if session_close >= session_open else "SELL"

        if self.locked_direction:
            return [Signal(symbol=symbol, action=self.locked_direction, quantity=self.quantity, order_type="MKT")]
        return []
