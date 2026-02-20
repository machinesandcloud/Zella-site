"""
RSI Exhaustion Strategy

Formula:
    RSI = 100 - (100 / (1 + RS))
    RS = Average Gain / Average Loss over N periods

Inputs:
- RSI Period: 14 bars (default)
- Overbought threshold: 70
- Oversold threshold: 30

Conditions:
- BUY: RSI <= 30 (oversold exhaustion)
- SELL: RSI >= 70 (overbought exhaustion)

Confidence increases as RSI approaches extremes (0 or 100)
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy
from utils.indicators import rsi, atr


class RSIExhaustionStrategy(BaseStrategy):
    """
    RSI Exhaustion - Mean reversion strategy based on overbought/oversold conditions.

    Uses the Relative Strength Index to identify price exhaustion points
    where reversals are likely to occur.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.rsi_period = int(params.get("rsi_period", 14))
        self.overbought = float(params.get("overbought", 70))
        self.oversold = float(params.get("oversold", 30))
        self.quantity = int(params.get("quantity", 1))

    def generate_signals(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Generate RSI exhaustion signal with full calculation details.

        Formula: RSI = 100 - (100 / (1 + RS)) where RS = Avg Gain / Avg Loss
        """
        if df is None or len(df) < self.rsi_period + 1:
            return None

        # Calculate RSI
        rsi_series = rsi(df["close"], self.rsi_period)
        current_rsi = rsi_series.iloc[-1]
        prev_rsi = rsi_series.iloc[-2] if len(rsi_series) > 1 else current_rsi

        # Get current price data
        last = df.iloc[-1]
        current_price = last["close"]

        # Calculate ATR for stop/target levels
        atr_val = atr(df, 14).iloc[-1] if len(df) >= 14 else current_price * 0.02

        # Calculate volume ratio
        vol_avg = df["volume"].tail(20).mean() if len(df) >= 20 else df["volume"].mean()
        volume_ratio = last["volume"] / vol_avg if vol_avg > 0 else 1.0

        # BUY Signal: RSI is oversold (exhaustion to downside)
        if current_rsi <= self.oversold:
            # Confidence increases as RSI approaches 0
            exhaustion_level = (self.oversold - current_rsi) / self.oversold
            base_confidence = 0.5 + (exhaustion_level * 0.35)

            # Boost if RSI is turning up (momentum shift)
            if current_rsi > prev_rsi:
                base_confidence += 0.1

            # Volume confirmation
            vol_boost = min(0.1, (volume_ratio - 1) * 0.05) if volume_ratio > 1 else 0

            confidence = min(0.95, base_confidence + vol_boost)

            return {
                "action": "BUY",
                "confidence": confidence,
                "reason": f"RSI exhaustion: RSI={current_rsi:.1f} (oversold <{self.oversold}), reversal likely",
                "stop_loss": current_price - (atr_val * 2),
                "take_profit": current_price + (atr_val * 3),
                "indicators": {
                    "rsi": round(current_rsi, 2),
                    "rsi_prev": round(prev_rsi, 2),
                    "rsi_direction": "up" if current_rsi > prev_rsi else "down",
                    "oversold_level": self.oversold,
                    "overbought_level": self.overbought,
                    "price": round(current_price, 2),
                    "volume_ratio": round(volume_ratio, 2),
                    "atr": round(atr_val, 2),
                }
            }

        # SELL Signal: RSI is overbought (exhaustion to upside)
        if current_rsi >= self.overbought:
            # Confidence increases as RSI approaches 100
            exhaustion_level = (current_rsi - self.overbought) / (100 - self.overbought)
            base_confidence = 0.5 + (exhaustion_level * 0.35)

            # Boost if RSI is turning down (momentum shift)
            if current_rsi < prev_rsi:
                base_confidence += 0.1

            # Volume confirmation
            vol_boost = min(0.1, (volume_ratio - 1) * 0.05) if volume_ratio > 1 else 0

            confidence = min(0.95, base_confidence + vol_boost)

            return {
                "action": "SELL",
                "confidence": confidence,
                "reason": f"RSI exhaustion: RSI={current_rsi:.1f} (overbought >{self.overbought}), pullback likely",
                "stop_loss": current_price + (atr_val * 2),
                "take_profit": current_price - (atr_val * 3),
                "indicators": {
                    "rsi": round(current_rsi, 2),
                    "rsi_prev": round(prev_rsi, 2),
                    "rsi_direction": "up" if current_rsi > prev_rsi else "down",
                    "oversold_level": self.oversold,
                    "overbought_level": self.overbought,
                    "price": round(current_price, 2),
                    "volume_ratio": round(volume_ratio, 2),
                    "atr": round(atr_val, 2),
                }
            }

        return None

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        df = self._to_df(data)
        if df is None or len(df) < self.rsi_period:
            return []

        rsi_series = rsi(df["close"], self.rsi_period)
        last_rsi = rsi_series.iloc[-1]

        if last_rsi <= self.oversold:
            return [Signal(symbol=symbol, action="BUY", quantity=self.quantity, order_type="MKT")]
        if last_rsi >= self.overbought:
            return [Signal(symbol=symbol, action="SELL", quantity=self.quantity, order_type="MKT")]
        return []

    def _to_df(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        if "df" in data and isinstance(data["df"], pd.DataFrame):
            return data["df"]
        history = data.get("history")
        if history:
            return pd.DataFrame(history)
        return None
