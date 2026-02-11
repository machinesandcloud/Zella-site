from typing import Any, Dict, List

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy
from utils.indicators import vwap


class PremarketVWAPReclaimStrategy(BaseStrategy):
    """Premarket dip below VWAP then reclaim with volume."""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.quantity = int(params.get("quantity", 1))
        self.volume_multiplier = float(params.get("volume_multiplier", 1.5))

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        pre_df = data.get("premarket_df")
        if pre_df is None or not isinstance(pre_df, pd.DataFrame) or len(pre_df) < 2:
            return []

        vw = vwap(pre_df)
        prev = pre_df.iloc[-2]
        last = pre_df.iloc[-1]
        avg_volume = pre_df["volume"].mean()

        if prev["close"] < vw.iloc[-2] and last["close"] > vw.iloc[-1] and last["volume"] >= avg_volume * self.volume_multiplier:
            return [Signal(symbol=symbol, action="BUY", quantity=self.quantity, order_type="MKT")]
        return []
