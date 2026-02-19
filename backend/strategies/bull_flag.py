"""
Bull Flag Breakout Strategy - Warrior Trading Core Pattern

The Bull Flag is one of the most reliable momentum patterns:
1. Strong upward move (flagpole) showing momentum
2. Consolidation period (flag) with decreasing volume
3. Breakout above flag resistance with volume confirmation

Entry: Break above flag high with volume surge
Stop: Below flag low (or ATR-based)
Target: Measured move equal to flagpole height
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy
from utils.indicators import is_bull_flag, atr, atr_stop_loss


class BullFlagStrategy(BaseStrategy):
    """
    Bull Flag Breakout - Primary Warrior Trading momentum pattern

    Looks for:
    - Strong upward move (5%+ gain) forming the flagpole
    - Tight consolidation with declining volume (the flag)
    - Breakout above flag high with volume confirmation
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.lookback = int(params.get("lookback", 20))
        self.consolidation_bars = int(params.get("consolidation_bars", 5))
        self.min_pole_gain = float(params.get("min_pole_gain", 0.05))  # 5% minimum
        self.volume_surge_threshold = float(params.get("volume_surge_threshold", 1.5))
        self.quantity = int(params.get("quantity", 1))
        self.use_atr_stops = bool(params.get("use_atr_stops", True))
        self.atr_multiplier = float(params.get("atr_multiplier", 2.0))

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        df = self._to_df(data)
        if df is None or len(df) < self.lookback + self.consolidation_bars + 5:
            return []

        # Detect bull flag pattern
        pattern = is_bull_flag(df, self.lookback, self.consolidation_bars)

        if not pattern.get("detected"):
            return []

        last = df.iloc[-1]
        prev = df.iloc[-2]
        breakout_level = pattern["breakout_level"]

        # Check for breakout: price crosses above flag high
        if prev["close"] <= breakout_level and last["close"] > breakout_level:
            # Volume confirmation
            avg_volume = df["volume"].tail(20).mean()
            if last["volume"] < avg_volume * self.volume_surge_threshold:
                return []  # No volume confirmation

            # Calculate stops
            if self.use_atr_stops:
                stop_distance = atr_stop_loss(df, self.atr_multiplier)
                stop_price = last["close"] - stop_distance
                # Target: 2:1 risk/reward minimum
                take_profit = last["close"] + (stop_distance * 2)
            else:
                stop_price = pattern["stop_level"]
                pole_height = last["close"] - pattern["stop_level"]
                take_profit = last["close"] + pole_height  # Measured move

            return [Signal(
                symbol=symbol,
                action="BUY",
                quantity=self.quantity,
                order_type="MKT",
                stop_loss=stop_price,
                take_profit=take_profit
            )]

        return []

    def generate_signals(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Generate signal dict for autonomous engine compatibility"""
        if df is None or len(df) < self.lookback + self.consolidation_bars + 5:
            return None

        pattern = is_bull_flag(df, self.lookback, self.consolidation_bars)

        if not pattern.get("detected"):
            return None

        last = df.iloc[-1]
        prev = df.iloc[-2]
        breakout_level = pattern["breakout_level"]

        # Check for breakout
        if prev["close"] <= breakout_level and last["close"] > breakout_level:
            avg_volume = df["volume"].tail(20).mean()
            if last["volume"] >= avg_volume * self.volume_surge_threshold:
                confidence = pattern.get("confidence", 0.7)

                # Calculate ATR-based stops
                atr_val = atr(df, 14).iloc[-1]
                stop_distance = atr_val * self.atr_multiplier
                stop_price = last["close"] - stop_distance
                take_profit = last["close"] + (stop_distance * 2)

                return {
                    "action": "BUY",
                    "confidence": confidence,
                    "reason": f"Bull Flag breakout: {pattern['pole_gain']*100:.1f}% pole, volume surge confirmed",
                    "pattern": "BULL_FLAG",
                    "stop_loss": stop_price,
                    "take_profit": take_profit,
                    "atr": atr_val
                }

        return None

    def _to_df(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        if "df" in data and isinstance(data["df"], pd.DataFrame):
            return data["df"]
        history = data.get("history")
        if history:
            return pd.DataFrame(history)
        return None
