"""
Scalping Strategy

Formula:
    Tick Change = Current Price - Previous Price
    Spread Analysis = Ask - Bid
    Micro-momentum = Price change over last 1-2 bars

Inputs:
- Target ticks: 3 ticks profit target
- Stop ticks: 2 ticks stop loss (tight risk management)

Conditions:
- BUY: Price momentum up >= target ticks with tight spread
- SELL: Price momentum down <= -stop ticks

Scalping focuses on small, quick profits with very tight stops.
High win rate required due to tight risk/reward.
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy
from utils.indicators import atr


class ScalpingStrategy(BaseStrategy):
    """
    Scalping - Quick in-and-out micro-momentum strategy.

    Designed for very short-term trades capturing small price movements
    with high frequency and tight risk management.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.target_ticks = float(params.get("target_ticks", 3))
        self.stop_ticks = float(params.get("stop_ticks", 2))
        self.quantity = int(params.get("quantity", 1))

    def generate_signals(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Generate scalping signal with full calculation details.

        Formula: BUY when tick change >= target_ticks
                 SELL when tick change <= -stop_ticks
        """
        if df is None or len(df) < 5:
            return None

        last = df.iloc[-1]
        prev = df.iloc[-2]
        current_price = last["close"]
        prev_price = prev["close"]

        # Calculate tick change
        tick_change = current_price - prev_price

        # Calculate micro-momentum (3-bar trend)
        if len(df) >= 5:
            micro_momentum = (current_price - df["close"].iloc[-5]) / df["close"].iloc[-5] * 100
        else:
            micro_momentum = 0

        # Volume spike detection
        vol_avg = df["volume"].tail(10).mean() if len(df) >= 10 else df["volume"].mean()
        volume_ratio = last["volume"] / vol_avg if vol_avg > 0 else 1.0

        # Spread analysis (if available)
        bid = last.get("bid", current_price * 0.9999)
        ask = last.get("ask", current_price * 1.0001)
        spread = ask - bid
        spread_pct = spread / current_price * 100 if current_price > 0 else 0

        # Calculate ATR for context
        atr_val = atr(df, 14).iloc[-1] if len(df) >= 14 else current_price * 0.01

        # BUY Signal: Quick upward momentum
        if tick_change >= self.target_ticks:
            # Confidence based on momentum and volume
            tick_confidence = min(0.3, tick_change / (self.target_ticks * 3))
            momentum_confidence = 0.2 if micro_momentum > 0 else 0
            volume_confidence = min(0.2, (volume_ratio - 1) * 0.1) if volume_ratio > 1 else 0

            confidence = 0.4 + tick_confidence + momentum_confidence + volume_confidence

            return {
                "action": "BUY",
                "confidence": min(0.90, confidence),  # Cap lower for scalping
                "reason": f"Scalp opportunity: +${tick_change:.2f} tick move, {micro_momentum:.2f}% micro-momentum",
                "stop_loss": current_price - (self.stop_ticks * 1.5),
                "take_profit": current_price + (self.target_ticks * 1.5),
                "indicators": {
                    "tick_change": round(tick_change, 2),
                    "micro_momentum_pct": round(micro_momentum, 2),
                    "spread": round(spread, 4),
                    "spread_pct": round(spread_pct, 4),
                    "price": round(current_price, 2),
                    "volume_ratio": round(volume_ratio, 2),
                    "atr": round(atr_val, 2),
                    "target_ticks": self.target_ticks,
                    "stop_ticks": self.stop_ticks,
                }
            }

        # SELL Signal: Quick downward momentum
        if tick_change <= -self.stop_ticks:
            tick_confidence = min(0.3, abs(tick_change) / (self.stop_ticks * 3))
            momentum_confidence = 0.2 if micro_momentum < 0 else 0
            volume_confidence = min(0.2, (volume_ratio - 1) * 0.1) if volume_ratio > 1 else 0

            confidence = 0.4 + tick_confidence + momentum_confidence + volume_confidence

            return {
                "action": "SELL",
                "confidence": min(0.90, confidence),
                "reason": f"Scalp short: ${tick_change:.2f} tick drop, {micro_momentum:.2f}% micro-momentum",
                "stop_loss": current_price + (self.target_ticks * 1.5),
                "take_profit": current_price - (self.stop_ticks * 1.5),
                "indicators": {
                    "tick_change": round(tick_change, 2),
                    "micro_momentum_pct": round(micro_momentum, 2),
                    "spread": round(spread, 4),
                    "spread_pct": round(spread_pct, 4),
                    "price": round(current_price, 2),
                    "volume_ratio": round(volume_ratio, 2),
                    "atr": round(atr_val, 2),
                    "target_ticks": self.target_ticks,
                    "stop_ticks": self.stop_ticks,
                }
            }

        return None

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        df = self._to_df(data)
        if df is None or len(df) < 2:
            return []

        last = df.iloc[-1]
        prev = df.iloc[-2]
        change = last["close"] - prev["close"]

        if change >= self.target_ticks:
            return [Signal(symbol=symbol, action="BUY", quantity=self.quantity, order_type="MKT")]
        if change <= -self.stop_ticks:
            return [Signal(symbol=symbol, action="SELL", quantity=self.quantity, order_type="MKT")]
        return []

    def _to_df(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        if "df" in data and isinstance(data["df"], pd.DataFrame):
            return data["df"]
        history = data.get("history")
        if history:
            return pd.DataFrame(history)
        return None
