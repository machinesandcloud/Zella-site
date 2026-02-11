from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy
from utils.indicators import rsi


class RangeTradingStrategy(BaseStrategy):
    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.rsi_period = int(params.get("rsi_period", 14))
        self.support_lookback = int(params.get("support_lookback", 20))
        self.resistance_lookback = int(params.get("resistance_lookback", 20))
        self.quantity = int(params.get("quantity", 1))

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        df = self._to_df(data)
        if df is None or len(df) < max(self.support_lookback, self.resistance_lookback):
            return []

        support = df["low"].rolling(self.support_lookback).min().iloc[-1]
        resistance = df["high"].rolling(self.resistance_lookback).max().iloc[-1]
        last_close = df.iloc[-1]["close"]
        rsi_val = rsi(df["close"], self.rsi_period).iloc[-1]

        if last_close <= support and rsi_val <= 30:
            return [Signal(symbol=symbol, action="BUY", quantity=self.quantity, order_type="MKT")]
        if last_close >= resistance and rsi_val >= 70:
            return [Signal(symbol=symbol, action="SELL", quantity=self.quantity, order_type="MKT")]
        return []

    def _to_df(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        if "df" in data and isinstance(data["df"], pd.DataFrame):
            return data["df"]
        history = data.get("history")
        if history:
            return pd.DataFrame(history)
        return None
