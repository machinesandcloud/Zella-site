from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy
from utils.indicators import ema


class MarketMakerRefillStrategy(BaseStrategy):
    """Volume spike with minimal movement suggests refill; trade with trend."""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.range_threshold = float(params.get("range_threshold", 0.2))
        self.volume_multiplier = float(params.get("volume_multiplier", 2.0))
        self.trend_ema = int(params.get("trend_ema", 50))
        self.quantity = int(params.get("quantity", 1))

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        df = self._to_df(data)
        if df is None or len(df) < self.trend_ema:
            return []

        last = df.iloc[-1]
        avg_volume = df["volume"].tail(self.trend_ema).mean()
        price_range_pct = ((last["high"] - last["low"]) / last["close"]) * 100 if last["close"] else 0

        if last["volume"] >= avg_volume * self.volume_multiplier and price_range_pct <= self.range_threshold:
            trend = ema(df["close"], self.trend_ema).iloc[-1]
            if last["close"] >= trend:
                return [Signal(symbol=symbol, action="BUY", quantity=self.quantity, order_type="MKT")]
            return [Signal(symbol=symbol, action="SELL", quantity=self.quantity, order_type="MKT")]

        return []

    def _to_df(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        if "df" in data and isinstance(data["df"], pd.DataFrame):
            return data["df"]
        history = data.get("history")
        if history:
            return pd.DataFrame(history)
        return None
