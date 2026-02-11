from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy
from utils.indicators import ema


class HTFEMAMomentumStrategy(BaseStrategy):
    """
    High-timeframe bias using 100 EMA, trade LTF momentum in that direction.
    Expects data keys: htf_df (DataFrame), df or history for LTF.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.htf_ema_period = int(params.get("htf_ema_period", 100))
        self.momentum_lookback = int(params.get("momentum_lookback", 5))
        self.quantity = int(params.get("quantity", 1))

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        ltf_df = self._to_df(data)
        htf_df = data.get("htf_df")
        if ltf_df is None or htf_df is None:
            return []
        if len(ltf_df) <= self.momentum_lookback or len(htf_df) < self.htf_ema_period:
            return []

        htf_ema = ema(htf_df["close"], self.htf_ema_period).iloc[-1]
        last_close = ltf_df["close"].iloc[-1]
        past_close = ltf_df["close"].iloc[-1 - self.momentum_lookback]
        momentum = last_close - past_close

        if last_close > htf_ema and momentum > 0:
            return [Signal(symbol=symbol, action="BUY", quantity=self.quantity, order_type="MKT")]
        if last_close < htf_ema and momentum < 0:
            return [Signal(symbol=symbol, action="SELL", quantity=self.quantity, order_type="MKT")]
        return []

    def _to_df(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        if "df" in data and isinstance(data["df"], pd.DataFrame):
            return data["df"]
        history = data.get("history")
        if history:
            return pd.DataFrame(history)
        return None
