from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy
from utils.indicators import vwap


class VWAPBounceStrategy(BaseStrategy):
    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.vwap_period = int(params.get("vwap_period", 20))
        self.volume_threshold = float(params.get("volume_threshold", 1.5))
        self.min_wick_percent = float(params.get("min_wick_percent", 2))
        self.quantity = int(params.get("quantity", 1))

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        df = self._to_df(data)
        if df is None or len(df) < self.vwap_period:
            return []

        df = df.tail(self.vwap_period)
        vw = vwap(df)
        last = df.iloc[-1]
        prev = df.iloc[-2]

        vol_avg = df["volume"].rolling(self.vwap_period).mean().iloc[-1]
        wick_percent = self._wick_percent(last)

        if (
            prev["close"] < vw.iloc[-2]
            and last["close"] > vw.iloc[-1]
            and last["volume"] >= vol_avg * self.volume_threshold
            and wick_percent >= self.min_wick_percent
        ):
            return [Signal(symbol=symbol, action="BUY", quantity=self.quantity, order_type="MKT")]

        if (
            prev["close"] > vw.iloc[-2]
            and last["close"] < vw.iloc[-1]
            and last["volume"] >= vol_avg * self.volume_threshold
            and wick_percent >= self.min_wick_percent
        ):
            return [Signal(symbol=symbol, action="SELL", quantity=self.quantity, order_type="MKT")]

        return []

    def _wick_percent(self, bar: pd.Series) -> float:
        high = bar["high"]
        low = bar["low"]
        close = bar["close"]
        if close == 0:
            return 0.0
        wick = max(high - close, close - low)
        return (wick / close) * 100

    def _to_df(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        if "df" in data and isinstance(data["df"], pd.DataFrame):
            return data["df"]
        history = data.get("history")
        if history:
            return pd.DataFrame(history)
        return None
