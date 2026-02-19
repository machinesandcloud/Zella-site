"""
Flat Top Breakout Strategy - Warrior Trading Core Pattern

The Flat Top Breakout identifies strong resistance levels being tested multiple times:
1. Price tests same resistance level 2+ times (flat top)
2. Each test shows buying pressure (accumulation)
3. Breakout above resistance with volume surge triggers entry

Entry: Break above flat resistance with volume
Stop: Below the consolidation low (or ATR-based)
Target: Risk/reward of at least 2:1
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy
from utils.indicators import is_flat_top_breakout, atr, atr_stop_loss


class FlatTopBreakoutStrategy(BaseStrategy):
    """
    Flat Top Breakout - Key Warrior Trading resistance breakout pattern

    Looks for:
    - Multiple tests of same resistance level (2+ touches)
    - Price consolidating just below resistance
    - Volume surge on breakout attempt
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.lookback = int(params.get("lookback", 10))
        self.tolerance = float(params.get("tolerance", 0.005))  # 0.5% tolerance
        self.min_touches = int(params.get("min_touches", 2))
        self.volume_surge_threshold = float(params.get("volume_surge_threshold", 1.5))
        self.quantity = int(params.get("quantity", 1))
        self.use_atr_stops = bool(params.get("use_atr_stops", True))
        self.atr_multiplier = float(params.get("atr_multiplier", 2.0))

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        df = self._to_df(data)
        if df is None or len(df) < self.lookback + 5:
            return []

        # Detect flat top pattern
        pattern = is_flat_top_breakout(df, self.lookback, self.tolerance)

        if not pattern.get("detected"):
            return []

        last = df.iloc[-1]
        prev = df.iloc[-2]
        breakout_level = pattern["breakout_level"]

        # Check for breakout: price crosses above flat top resistance
        if prev["close"] <= breakout_level and last["close"] > breakout_level:
            # Volume confirmation
            avg_volume = df["volume"].tail(20).mean()
            if last["volume"] < avg_volume * self.volume_surge_threshold:
                return []  # No volume confirmation

            # Calculate stops
            if self.use_atr_stops:
                stop_distance = atr_stop_loss(df, self.atr_multiplier)
                stop_price = last["close"] - stop_distance
                take_profit = last["close"] + (stop_distance * 2)
            else:
                stop_price = pattern["stop_level"]
                risk = last["close"] - stop_price
                take_profit = last["close"] + (risk * 2)

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
        if df is None or len(df) < self.lookback + 5:
            return None

        pattern = is_flat_top_breakout(df, self.lookback, self.tolerance)

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
                touches = pattern.get("touches", 2)

                # Calculate ATR-based stops
                atr_val = atr(df, 14).iloc[-1]
                stop_distance = atr_val * self.atr_multiplier
                stop_price = last["close"] - stop_distance
                take_profit = last["close"] + (stop_distance * 2)

                return {
                    "action": "BUY",
                    "confidence": confidence,
                    "reason": f"Flat Top breakout: {touches} resistance touches, volume confirmed",
                    "pattern": "FLAT_TOP",
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
