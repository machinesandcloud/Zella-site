"""
Opening Range Breakout (ORB) Strategy - Key Warrior Trading Pattern

Formula:
    Opening Range High = MAX(High) of first 15-30 minutes
    Opening Range Low = MIN(Low) of first 15-30 minutes

Inputs:
- Opening range period: First 15 minutes (3 x 5-min bars)
- Breakout buffer: $0.05 above/below range

Conditions:
- BUY: Price breaks above Opening Range High + buffer
- SELL: Price breaks below Opening Range Low - buffer

The ORB is one of the most reliable day trading patterns because it
captures the initial institutional activity and direction.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy
from utils.indicators import atr


class ORBStrategy(BaseStrategy):
    """
    Opening Range Breakout - Core Warrior Trading day trading strategy.

    Trades breakouts from the first 15-30 minutes of trading,
    which often sets the tone for the entire day.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.opening_range_minutes = int(params.get("opening_range_minutes", 15))
        self.breakout_buffer = float(params.get("breakout_buffer", 0.05))
        self.quantity = int(params.get("quantity", 1))

    def generate_signals(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Generate ORB signal with full calculation details.

        Formula: BUY when Price > Opening Range High + buffer
                 SELL when Price < Opening Range Low - buffer
        """
        if df is None or len(df) < 4:
            return None

        # Assume 5-minute bars, first 3 bars = 15 minutes opening range
        bar_interval = 5  # Default assumption
        opening_bars = max(int(self.opening_range_minutes / bar_interval), 1)

        if len(df) < opening_bars + 1:
            return None

        # Calculate opening range
        opening_range = df.iloc[:opening_bars]
        range_high = opening_range["high"].max()
        range_low = opening_range["low"].min()
        range_size = range_high - range_low

        # Current price
        last = df.iloc[-1]
        current_price = last["close"]

        # Volume analysis
        opening_volume = opening_range["volume"].sum()
        current_volume = last["volume"]
        vol_avg = df["volume"].mean()
        volume_ratio = current_volume / vol_avg if vol_avg > 0 else 1.0

        # Calculate ATR for stops
        atr_val = atr(df, 14).iloc[-1] if len(df) >= 14 else current_price * 0.02

        # Calculate breakout percentage
        breakout_above = ((current_price - range_high) / range_high * 100) if current_price > range_high else 0
        breakdown_below = ((range_low - current_price) / range_low * 100) if current_price < range_low else 0

        # BUY Signal: Price breaks above opening range high
        if current_price > range_high + self.breakout_buffer:
            # Confidence based on breakout strength and volume
            breakout_confidence = min(0.3, breakout_above / 2.0)  # Up to 2% breakout
            volume_confidence = min(0.3, (volume_ratio - 1) / 2.0) if volume_ratio > 1 else 0
            range_confidence = min(0.2, range_size / current_price * 20)  # Tighter range = better

            confidence = 0.4 + breakout_confidence + volume_confidence + range_confidence

            return {
                "action": "BUY",
                "confidence": min(0.95, confidence),
                "reason": f"ORB Breakout: Price ${current_price:.2f} broke above range high ${range_high:.2f} (+{breakout_above:.1f}%)",
                "stop_loss": range_high - (range_size * 0.5),  # Stop below range high
                "take_profit": current_price + (range_size * 2.0),  # 2x range size target
                "indicators": {
                    "range_high": round(range_high, 2),
                    "range_low": round(range_low, 2),
                    "range_size": round(range_size, 2),
                    "range_size_pct": round(range_size / range_low * 100, 2) if range_low > 0 else 0,
                    "breakout_pct": round(breakout_above, 2),
                    "opening_minutes": self.opening_range_minutes,
                    "price": round(current_price, 2),
                    "volume_ratio": round(volume_ratio, 2),
                    "atr": round(atr_val, 2),
                }
            }

        # SELL Signal: Price breaks below opening range low
        if current_price < range_low - self.breakout_buffer:
            breakout_confidence = min(0.3, breakdown_below / 2.0)
            volume_confidence = min(0.3, (volume_ratio - 1) / 2.0) if volume_ratio > 1 else 0
            range_confidence = min(0.2, range_size / current_price * 20)

            confidence = 0.4 + breakout_confidence + volume_confidence + range_confidence

            return {
                "action": "SELL",
                "confidence": min(0.95, confidence),
                "reason": f"ORB Breakdown: Price ${current_price:.2f} broke below range low ${range_low:.2f} (-{breakdown_below:.1f}%)",
                "stop_loss": range_low + (range_size * 0.5),
                "take_profit": current_price - (range_size * 2.0),
                "indicators": {
                    "range_high": round(range_high, 2),
                    "range_low": round(range_low, 2),
                    "range_size": round(range_size, 2),
                    "range_size_pct": round(range_size / range_low * 100, 2) if range_low > 0 else 0,
                    "breakdown_pct": round(breakdown_below, 2),
                    "opening_minutes": self.opening_range_minutes,
                    "price": round(current_price, 2),
                    "volume_ratio": round(volume_ratio, 2),
                    "atr": round(atr_val, 2),
                }
            }

        return None

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        df = self._to_df(data)
        if df is None or len(df) < 2:
            return []

        bar_interval = int(data.get("bar_interval_minutes", 1))
        opening_bars = max(int(self.opening_range_minutes / bar_interval), 1)
        if len(df) < opening_bars + 1:
            return []

        opening_range = df.iloc[:opening_bars]
        range_high = opening_range["high"].max()
        range_low = opening_range["low"].min()
        last_close = df.iloc[-1]["close"]

        if last_close > range_high + self.breakout_buffer:
            return [Signal(symbol=symbol, action="BUY", quantity=self.quantity, order_type="MKT")]
        if last_close < range_low - self.breakout_buffer:
            return [Signal(symbol=symbol, action="SELL", quantity=self.quantity, order_type="MKT")]
        return []

    def _to_df(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        if "df" in data and isinstance(data["df"], pd.DataFrame):
            return data["df"]
        history = data.get("history")
        if history:
            return pd.DataFrame(history)
        return None
