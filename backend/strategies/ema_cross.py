"""
EMA Crossover Strategy

Formula:
    EMA = Price × K + EMA_prev × (1 - K)
    K = 2 / (N + 1) where N = period

Inputs:
- Fast EMA: 20 periods (short-term trend)
- Slow EMA: 50 periods (medium-term trend)

Conditions:
- BUY (Golden Cross): Fast EMA crosses ABOVE Slow EMA
- SELL (Death Cross): Fast EMA crosses BELOW Slow EMA

Confidence based on:
- Angle/slope of the crossover (steeper = stronger trend)
- Distance between EMAs after cross
- Volume confirmation
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy
from utils.indicators import ema, atr


class EMACrossStrategy(BaseStrategy):
    """
    EMA Crossover - Classic trend-following strategy.

    Uses exponential moving average crossovers to identify trend changes.
    Golden Cross (bullish) and Death Cross (bearish) are the main signals.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.fast_ema = int(params.get("fast_ema", 20))
        self.slow_ema = int(params.get("slow_ema", 50))
        self.quantity = int(params.get("quantity", 1))
        self._last_signal = None

    def generate_signals(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Generate EMA crossover signal with full calculation details.

        Formula: BUY when Fast EMA(20) crosses above Slow EMA(50)
                 SELL when Fast EMA(20) crosses below Slow EMA(50)
        """
        if df is None or len(df) < self.slow_ema + 2:
            return None

        # Calculate EMAs
        fast = ema(df["close"], self.fast_ema)
        slow = ema(df["close"], self.slow_ema)

        current_fast = fast.iloc[-1]
        current_slow = slow.iloc[-1]
        prev_fast = fast.iloc[-2]
        prev_slow = slow.iloc[-2]

        # Calculate EMA spread (distance between fast and slow)
        ema_spread = ((current_fast - current_slow) / current_slow * 100) if current_slow > 0 else 0

        # Calculate EMA slopes (momentum)
        fast_slope = ((current_fast - fast.iloc[-5]) / fast.iloc[-5] * 100) if len(fast) >= 5 else 0
        slow_slope = ((current_slow - slow.iloc[-5]) / slow.iloc[-5] * 100) if len(slow) >= 5 else 0

        # Get current price data
        last = df.iloc[-1]
        current_price = last["close"]

        # Calculate ATR for stops
        atr_val = atr(df, 14).iloc[-1] if len(df) >= 14 else current_price * 0.02

        # Volume analysis
        vol_avg = df["volume"].tail(20).mean() if len(df) >= 20 else df["volume"].mean()
        volume_ratio = last["volume"] / vol_avg if vol_avg > 0 else 1.0

        # BUY Signal: Golden Cross (fast crosses above slow)
        if prev_fast <= prev_slow and current_fast > current_slow:
            # Confidence based on crossover strength
            spread_confidence = min(0.3, abs(ema_spread) / 3.0)  # Stronger spread = more confident
            slope_confidence = min(0.3, max(0, fast_slope) / 2.0)  # Upward slope helps
            vol_confidence = min(0.2, (volume_ratio - 1) * 0.1) if volume_ratio > 1 else 0

            confidence = 0.4 + spread_confidence + slope_confidence + vol_confidence

            self._last_signal = "BUY"
            return {
                "action": "BUY",
                "confidence": min(0.95, confidence),
                "reason": f"Golden Cross: EMA{self.fast_ema} (${current_fast:.2f}) crossed above EMA{self.slow_ema} (${current_slow:.2f})",
                "stop_loss": current_price - (atr_val * 2),
                "take_profit": current_price + (atr_val * 3),
                "indicators": {
                    "fast_ema": round(current_fast, 2),
                    "slow_ema": round(current_slow, 2),
                    "ema_spread_pct": round(ema_spread, 2),
                    "fast_slope_pct": round(fast_slope, 2),
                    "slow_slope_pct": round(slow_slope, 2),
                    "price": round(current_price, 2),
                    "volume_ratio": round(volume_ratio, 2),
                    "atr": round(atr_val, 2),
                    "signal_type": "Golden Cross"
                }
            }

        # SELL Signal: Death Cross (fast crosses below slow)
        if prev_fast >= prev_slow and current_fast < current_slow:
            spread_confidence = min(0.3, abs(ema_spread) / 3.0)
            slope_confidence = min(0.3, max(0, -fast_slope) / 2.0)  # Downward slope helps
            vol_confidence = min(0.2, (volume_ratio - 1) * 0.1) if volume_ratio > 1 else 0

            confidence = 0.4 + spread_confidence + slope_confidence + vol_confidence

            self._last_signal = "SELL"
            return {
                "action": "SELL",
                "confidence": min(0.95, confidence),
                "reason": f"Death Cross: EMA{self.fast_ema} (${current_fast:.2f}) crossed below EMA{self.slow_ema} (${current_slow:.2f})",
                "stop_loss": current_price + (atr_val * 2),
                "take_profit": current_price - (atr_val * 3),
                "indicators": {
                    "fast_ema": round(current_fast, 2),
                    "slow_ema": round(current_slow, 2),
                    "ema_spread_pct": round(ema_spread, 2),
                    "fast_slope_pct": round(fast_slope, 2),
                    "slow_slope_pct": round(slow_slope, 2),
                    "price": round(current_price, 2),
                    "volume_ratio": round(volume_ratio, 2),
                    "atr": round(atr_val, 2),
                    "signal_type": "Death Cross"
                }
            }

        return None

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        df = self._to_df(data)
        if df is None or len(df) < self.slow_ema:
            return []

        fast = ema(df["close"], self.fast_ema)
        slow = ema(df["close"], self.slow_ema)

        if fast.iloc[-2] <= slow.iloc[-2] and fast.iloc[-1] > slow.iloc[-1]:
            if self._last_signal != "BUY":
                self._last_signal = "BUY"
                return [Signal(symbol=symbol, action="BUY", quantity=self.quantity, order_type="MKT")]

        if fast.iloc[-2] >= slow.iloc[-2] and fast.iloc[-1] < slow.iloc[-1]:
            if self._last_signal != "SELL":
                self._last_signal = "SELL"
                return [Signal(symbol=symbol, action="SELL", quantity=self.quantity, order_type="MKT")]

        return []

    def _to_df(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        if "df" in data and isinstance(data["df"], pd.DataFrame):
            return data["df"]
        history = data.get("history")
        if history:
            return pd.DataFrame(history)
        return None
