"""
Momentum Strategy

Formula:
    Momentum = ((Current Price - Past Price) / Past Price) × 100
    ROC (Rate of Change) = Momentum over N periods

Inputs:
- Lookback period: 10 bars
- Minimum momentum threshold: 1.5%

Conditions:
- BUY: Momentum >= +1.5% (strong upward momentum)
- SELL: Momentum <= -1.5% (strong downward momentum)
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy
from utils.indicators import atr


class MomentumStrategy(BaseStrategy):
    """
    Momentum - Trend continuation strategy based on price momentum.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.momentum_lookback = int(params.get("momentum_lookback", 10))
        self.min_momentum = float(params.get("min_momentum", 1.5))
        self.quantity = int(params.get("quantity", 1))

    def generate_signals(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Generate momentum signal - ride strong moves with tight stops.

        Day trading approach: Jump on strong moves, exit fast if momentum fades.
        """
        if df is None or len(df) < self.momentum_lookback + 5:
            return None

        current_price = df["close"].iloc[-1]
        past_price = df["close"].iloc[-1 - self.momentum_lookback]

        if past_price == 0:
            return None

        momentum = ((current_price - past_price) / past_price) * 100

        # Calculate acceleration (momentum of momentum)
        if len(df) >= self.momentum_lookback + 5:
            prev_momentum = ((df["close"].iloc[-2] - df["close"].iloc[-2 - self.momentum_lookback]) /
                           df["close"].iloc[-2 - self.momentum_lookback]) * 100
            acceleration = momentum - prev_momentum
        else:
            acceleration = 0

        # Volume analysis — 1.5x ideal; 1.2x hard minimum; below that skip
        vol_avg = df["volume"].tail(20).mean() if len(df) >= 20 else df["volume"].mean()
        volume_ratio = df["volume"].iloc[-1] / vol_avg if vol_avg > 0 else 1.0

        # Volume gate: below 1.2x is a trap — penalise 1.2-1.5x via lower confidence
        if volume_ratio < 1.2:
            return None

        # Calculate ATR for tight stops
        atr_val = atr(df, 14).iloc[-1] if len(df) >= 14 else current_price * 0.02

        # Use configured minimum momentum (default 1.5%)
        min_mom = self.min_momentum

        # BUY Signal - strong upward momentum
        if momentum >= min_mom:
            # Higher base + bonuses
            momentum_bonus = min(0.20, (momentum - min_mom) / 4.0)
            accel_bonus = min(0.10, acceleration / 1.0) if acceleration > 0 else 0
            volume_bonus = min(0.10, (volume_ratio - 1.0) / 2.0) if volume_ratio > 1.0 else 0
            confidence = 0.50 + momentum_bonus + accel_bonus + volume_bonus

            # ATR-based stops: 1.5x stop, 3.75x target = 2.5:1 R/R (research minimum is 2:1)
            stop_loss = current_price - (atr_val * 1.5)
            take_profit = current_price + (atr_val * 3.75)

            return {
                "action": "BUY",
                "confidence": min(0.85, confidence),
                "reason": f"Momentum +{momentum:.1f}% (accel {acceleration:+.1f}%)",
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "indicators": {
                    "momentum_pct": round(momentum, 2),
                    "acceleration": round(acceleration, 2),
                    "price": round(current_price, 2),
                    "volume_ratio": round(volume_ratio, 2),
                    "atr": round(atr_val, 2),
                }
            }

        # SELL Signal - strong downward momentum
        if momentum <= -min_mom:
            momentum_bonus = min(0.20, (abs(momentum) - min_mom) / 4.0)
            accel_bonus = min(0.10, abs(acceleration) / 1.0) if acceleration < 0 else 0
            volume_bonus = min(0.10, (volume_ratio - 1.0) / 2.0) if volume_ratio > 1.0 else 0
            confidence = 0.50 + momentum_bonus + accel_bonus + volume_bonus

            stop_loss = current_price + (atr_val * 1.5)
            take_profit = current_price - (atr_val * 2.5)

            return {
                "action": "SELL",
                "confidence": min(0.85, confidence),
                "reason": f"Momentum {momentum:.1f}% (accel {acceleration:+.1f}%)",
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "indicators": {
                    "momentum_pct": round(momentum, 2),
                    "acceleration": round(acceleration, 2),
                    "price": round(current_price, 2),
                    "volume_ratio": round(volume_ratio, 2),
                    "atr": round(atr_val, 2),
                }
            }

        return None

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        df = self._to_df(data)
        if df is None or len(df) < self.momentum_lookback + 1:
            return []

        recent = df["close"].iloc[-1]
        past = df["close"].iloc[-1 - self.momentum_lookback]
        if past == 0:
            return []
        momentum = ((recent - past) / past) * 100

        if momentum >= self.min_momentum:
            return [Signal(symbol=symbol, action="BUY", quantity=self.quantity, order_type="MKT")]
        if momentum <= -self.min_momentum:
            return [Signal(symbol=symbol, action="SELL", quantity=self.quantity, order_type="MKT")]
        return []

    def _to_df(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        if "df" in data and isinstance(data["df"], pd.DataFrame):
            return data["df"]
        history = data.get("history")
        if history:
            return pd.DataFrame(history)
        return None
