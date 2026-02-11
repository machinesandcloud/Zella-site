from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy
from utils.indicators import rsi


class RSIExtremeReversalStrategy(BaseStrategy):
    """RSI >= 90 or <= 10 with reversal candle."""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.rsi_period = int(params.get("rsi_period", 14))
        self.overbought = float(params.get("overbought", 90))
        self.oversold = float(params.get("oversold", 10))
        self.quantity = int(params.get("quantity", 1))

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        df = self._to_df(data)
        if df is None or len(df) < self.rsi_period:
            return []

        rsi_series = rsi(df["close"], self.rsi_period)
        last_rsi = rsi_series.iloc[-1]
        last = df.iloc[-1]

        if last_rsi >= self.overbought and last["close"] < last["open"]:
            return [Signal(symbol=symbol, action="SELL", quantity=self.quantity, order_type="MKT")]
        if last_rsi <= self.oversold and last["close"] > last["open"]:
            return [Signal(symbol=symbol, action="BUY", quantity=self.quantity, order_type="MKT")]
        return []

    def _to_df(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        if "df" in data and isinstance(data["df"], pd.DataFrame):
            return data["df"]
        history = data.get("history")
        if history:
            return pd.DataFrame(history)
        return None
