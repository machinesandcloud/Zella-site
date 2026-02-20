"""
Trend Following Strategy

Formula:
    Fast EMA = EMA(Close, 20)
    Slow EMA = EMA(Close, 50)
    Trend = Fast EMA - Slow EMA

Inputs:
- Fast EMA period: 20 bars
- Slow EMA period: 50 bars

Conditions:
- BUY: Fast EMA > Slow EMA (uptrend)
- SELL: Fast EMA < Slow EMA (downtrend)

Unlike EMA Cross which trades crossovers, Trend Follow stays with the trend
as long as Fast EMA remains above/below Slow EMA.
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy
from utils.indicators import ema, atr


class TrendFollowStrategy(BaseStrategy):
    """
    Trend Following - Ride the trend strategy based on EMA alignment.

    Stays in the direction of the prevailing trend as indicated by
    the relationship between fast and slow EMAs.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.fast_ema = int(params.get("fast_ema", 20))
        self.slow_ema = int(params.get("slow_ema", 50))
        self.quantity = int(params.get("quantity", 1))

    def generate_signals(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Generate trend follow signal with full calculation details.

        Formula: BUY when Fast EMA(20) > Slow EMA(50)
                 SELL when Fast EMA(20) < Slow EMA(50)
        """
        if df is None or len(df) < self.slow_ema + 5:
            return None

        # Calculate EMAs
        fast = ema(df["close"], self.fast_ema)
        slow = ema(df["close"], self.slow_ema)

        current_fast = fast.iloc[-1]
        current_slow = slow.iloc[-1]

        # Calculate EMA spread and trend strength
        ema_spread = ((current_fast - current_slow) / current_slow * 100) if current_slow > 0 else 0
        ema_spread_abs = abs(ema_spread)

        # Calculate trend duration (how many bars in this trend)
        trend_direction = "up" if current_fast > current_slow else "down"
        trend_bars = 0
        for i in range(1, min(50, len(fast))):
            if trend_direction == "up" and fast.iloc[-i] > slow.iloc[-i]:
                trend_bars += 1
            elif trend_direction == "down" and fast.iloc[-i] < slow.iloc[-i]:
                trend_bars += 1
            else:
                break

        # Current price
        current_price = df["close"].iloc[-1]

        # Volume analysis
        vol_avg = df["volume"].tail(20).mean() if len(df) >= 20 else df["volume"].mean()
        volume_ratio = df["volume"].iloc[-1] / vol_avg if vol_avg > 0 else 1.0

        # Calculate ATR
        atr_val = atr(df, 14).iloc[-1] if len(df) >= 14 else current_price * 0.02

        # BUY Signal: Uptrend (Fast EMA > Slow EMA)
        if current_fast > current_slow:
            # Confidence based on trend strength
            spread_confidence = min(0.3, ema_spread_abs / 3.0)  # Stronger spread = better
            duration_confidence = min(0.3, trend_bars / 20.0)  # Longer trend = better
            volume_confidence = min(0.2, (volume_ratio - 1) * 0.1) if volume_ratio > 1 else 0

            confidence = 0.3 + spread_confidence + duration_confidence + volume_confidence

            return {
                "action": "BUY",
                "confidence": min(0.95, confidence),
                "reason": f"Uptrend: Fast EMA ${current_fast:.2f} > Slow EMA ${current_slow:.2f} (+{ema_spread:.2f}%), {trend_bars} bars",
                "stop_loss": current_slow - (atr_val * 1),  # Stop below slow EMA
                "take_profit": current_price + (atr_val * 3),
                "indicators": {
                    "fast_ema": round(current_fast, 2),
                    "slow_ema": round(current_slow, 2),
                    "ema_spread_pct": round(ema_spread, 2),
                    "trend_direction": trend_direction,
                    "trend_bars": trend_bars,
                    "price": round(current_price, 2),
                    "volume_ratio": round(volume_ratio, 2),
                    "atr": round(atr_val, 2),
                }
            }

        # SELL Signal: Downtrend (Fast EMA < Slow EMA)
        if current_fast < current_slow:
            spread_confidence = min(0.3, ema_spread_abs / 3.0)
            duration_confidence = min(0.3, trend_bars / 20.0)
            volume_confidence = min(0.2, (volume_ratio - 1) * 0.1) if volume_ratio > 1 else 0

            confidence = 0.3 + spread_confidence + duration_confidence + volume_confidence

            return {
                "action": "SELL",
                "confidence": min(0.95, confidence),
                "reason": f"Downtrend: Fast EMA ${current_fast:.2f} < Slow EMA ${current_slow:.2f} ({ema_spread:.2f}%), {trend_bars} bars",
                "stop_loss": current_slow + (atr_val * 1),
                "take_profit": current_price - (atr_val * 3),
                "indicators": {
                    "fast_ema": round(current_fast, 2),
                    "slow_ema": round(current_slow, 2),
                    "ema_spread_pct": round(ema_spread, 2),
                    "trend_direction": trend_direction,
                    "trend_bars": trend_bars,
                    "price": round(current_price, 2),
                    "volume_ratio": round(volume_ratio, 2),
                    "atr": round(atr_val, 2),
                }
            }

        return None

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        df = self._to_df(data)
        if df is None or len(df) < self.slow_ema:
            return []
        fast = ema(df["close"], self.fast_ema)
        slow = ema(df["close"], self.slow_ema)
        if fast.iloc[-1] > slow.iloc[-1]:
            return [Signal(symbol=symbol, action="BUY", quantity=self.quantity, order_type="MKT")]
        if fast.iloc[-1] < slow.iloc[-1]:
            return [Signal(symbol=symbol, action="SELL", quantity=self.quantity, order_type="MKT")]
        return []

    def _to_df(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        if "df" in data and isinstance(data["df"], pd.DataFrame):
            return data["df"]
        history = data.get("history")
        if history:
            return pd.DataFrame(history)
        return None
