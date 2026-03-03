"""
ABCD Pattern Strategy - Core day trading setup

Detects ABCD bullish/bearish patterns and triggers on the D leg breakout.
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy
from utils.indicators import is_abcd_pattern, atr


class ABCDPatternStrategy(BaseStrategy):
    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.lookback = int(params.get("lookback", 40))
        self.min_leg_pct = float(params.get("min_leg_pct", 0.03))
        self.retrace_min = float(params.get("retrace_min", 0.3))
        self.retrace_max = float(params.get("retrace_max", 0.7))
        self.extension_min = float(params.get("extension_min", 0.8))
        self.extension_max = float(params.get("extension_max", 1.3))
        self.quantity = int(params.get("quantity", 1))
        self.use_atr_stops = bool(params.get("use_atr_stops", True))
        self.atr_multiplier = float(params.get("atr_multiplier", 2.0))

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        df = self._to_df(data)
        if df is None or len(df) < self.lookback:
            return []

        pattern = is_abcd_pattern(
            df,
            lookback=self.lookback,
            min_leg_pct=self.min_leg_pct,
            retrace_min=self.retrace_min,
            retrace_max=self.retrace_max,
            extension_min=self.extension_min,
            extension_max=self.extension_max,
        )
        if not pattern.get("detected"):
            return []

        last = df.iloc[-1]
        prev = df.iloc[-2]
        entry_level = pattern["entry_level"]

        if pattern["pattern"] == "ABCD_BULL":
            if prev["close"] <= entry_level and last["close"] > entry_level:
                stop_price, take_profit = self._stops(last["close"], df, pattern["stop_level"], bullish=True)
                return [Signal(
                    symbol=symbol,
                    action="BUY",
                    quantity=self.quantity,
                    order_type="MKT",
                    stop_loss=stop_price,
                    take_profit=take_profit,
                )]

        if pattern["pattern"] == "ABCD_BEAR":
            if prev["close"] >= entry_level and last["close"] < entry_level:
                stop_price, take_profit = self._stops(last["close"], df, pattern["stop_level"], bullish=False)
                return [Signal(
                    symbol=symbol,
                    action="SELL",
                    quantity=self.quantity,
                    order_type="MKT",
                    stop_loss=stop_price,
                    take_profit=take_profit,
                )]

        return []

    def generate_signals(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        if df is None or len(df) < self.lookback:
            return None

        pattern = is_abcd_pattern(
            df,
            lookback=self.lookback,
            min_leg_pct=self.min_leg_pct,
            retrace_min=self.retrace_min,
            retrace_max=self.retrace_max,
            extension_min=self.extension_min,
            extension_max=self.extension_max,
        )
        if not pattern.get("detected"):
            return None

        last = df.iloc[-1]
        prev = df.iloc[-2]
        entry_level = pattern["entry_level"]
        confidence = pattern.get("confidence", 0.6)

        if pattern["pattern"] == "ABCD_BULL" and prev["close"] <= entry_level and last["close"] > entry_level:
            stop_price, take_profit = self._stops(last["close"], df, pattern["stop_level"], bullish=True)
            return {
                "action": "BUY",
                "confidence": confidence,
                "reason": "ABCD bullish continuation breakout",
                "pattern": "ABCD_BULL",
                "stop_loss": stop_price,
                "take_profit": take_profit,
            }

        if pattern["pattern"] == "ABCD_BEAR" and prev["close"] >= entry_level and last["close"] < entry_level:
            stop_price, take_profit = self._stops(last["close"], df, pattern["stop_level"], bullish=False)
            return {
                "action": "SELL",
                "confidence": confidence,
                "reason": "ABCD bearish continuation breakdown",
                "pattern": "ABCD_BEAR",
                "stop_loss": stop_price,
                "take_profit": take_profit,
            }

        return None

    def _stops(self, last_close: float, df: pd.DataFrame, fallback_stop: float, bullish: bool) -> tuple[float, float]:
        if self.use_atr_stops:
            atr_val = atr(df, 14).iloc[-1]
            stop_distance = atr_val * self.atr_multiplier
            stop_price = last_close - stop_distance if bullish else last_close + stop_distance
        else:
            stop_price = fallback_stop
            stop_distance = abs(last_close - stop_price)

        take_profit = last_close + (stop_distance * 2) if bullish else last_close - (stop_distance * 2)
        return stop_price, take_profit

    def _to_df(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        if "df" in data and isinstance(data["df"], pd.DataFrame):
            return data["df"]
        history = data.get("history")
        if history:
            return pd.DataFrame(history)
        return None
