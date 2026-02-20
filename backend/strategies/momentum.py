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
        """Generate momentum signal with full calculation details."""
        if df is None or len(df) < self.momentum_lookback + 5:
            return None

        current_price = df["close"].iloc[-1]
        past_price = df["close"].iloc[-1 - self.momentum_lookback]

        if past_price == 0:
            return None

        momentum = ((current_price - past_price) / past_price) * 100

        # Calculate acceleration
        if len(df) >= self.momentum_lookback + 5:
            prev_momentum = ((df["close"].iloc[-2] - df["close"].iloc[-2 - self.momentum_lookback]) /
                           df["close"].iloc[-2 - self.momentum_lookback]) * 100
            acceleration = momentum - prev_momentum
        else:
            acceleration = 0

        # Volume analysis
        vol_avg = df["volume"].tail(20).mean() if len(df) >= 20 else df["volume"].mean()
        volume_ratio = df["volume"].iloc[-1] / vol_avg if vol_avg > 0 else 1.0

        # Calculate ATR
        atr_val = atr(df, 14).iloc[-1] if len(df) >= 14 else current_price * 0.02

        # BUY Signal
        if momentum >= self.min_momentum:
            momentum_confidence = min(0.4, (momentum - self.min_momentum) / 5.0)
            accel_confidence = 0.1 if acceleration > 0 else 0
            volume_confidence = min(0.2, (volume_ratio - 1) * 0.1) if volume_ratio > 1 else 0
            confidence = 0.4 + momentum_confidence + accel_confidence + volume_confidence

            return {
                "action": "BUY",
                "confidence": min(0.95, confidence),
                "reason": f"Strong momentum: +{momentum:.2f}% over {self.momentum_lookback} bars",
                "stop_loss": current_price - (atr_val * 2),
                "take_profit": current_price + (atr_val * 3),
                "indicators": {
                    "momentum_pct": round(momentum, 2),
                    "acceleration": round(acceleration, 2),
                    "price": round(current_price, 2),
                    "volume_ratio": round(volume_ratio, 2),
                    "atr": round(atr_val, 2),
                }
            }

        # SELL Signal
        if momentum <= -self.min_momentum:
            momentum_confidence = min(0.4, (abs(momentum) - self.min_momentum) / 5.0)
            accel_confidence = 0.1 if acceleration < 0 else 0
            volume_confidence = min(0.2, (volume_ratio - 1) * 0.1) if volume_ratio > 1 else 0
            confidence = 0.4 + momentum_confidence + accel_confidence + volume_confidence

            return {
                "action": "SELL",
                "confidence": min(0.95, confidence),
                "reason": f"Strong downward momentum: {momentum:.2f}% over {self.momentum_lookback} bars",
                "stop_loss": current_price + (atr_val * 2),
                "take_profit": current_price - (atr_val * 3),
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
