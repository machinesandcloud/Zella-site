from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy
from utils.indicators import ema


class PullbackStrategy(BaseStrategy):
    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.pullback_percent = float(params.get("pullback_percent", 0.5))
        self.trend_ema = int(params.get("trend_ema", 50))
        self.quantity = int(params.get("quantity", 1))

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        df = self._to_df(data)
        if df is None or len(df) < self.trend_ema:
            return []

        ema_series = ema(df["close"], self.trend_ema)
        last_close = df.iloc[-1]["close"]
        recent_high = df["high"].tail(self.trend_ema).max()

        if last_close > ema_series.iloc[-1]:
            pullback = ((recent_high - last_close) / recent_high) * 100
            if pullback >= self.pullback_percent:
                return [Signal(symbol=symbol, action="BUY", quantity=self.quantity, order_type="MKT")]

        if last_close < ema_series.iloc[-1]:
            pullback = ((last_close - recent_high) / recent_high) * 100
            if pullback <= -self.pullback_percent:
                return [Signal(symbol=symbol, action="SELL", quantity=self.quantity, order_type="MKT")]

        return []

    def _to_df(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        if "df" in data and isinstance(data["df"], pd.DataFrame):
            return data["df"]
        history = data.get("history")
        if history:
            return pd.DataFrame(history)
        return None
