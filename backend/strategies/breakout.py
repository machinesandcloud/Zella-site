"""
Breakout Strategy

Formula:
    Resistance = MAX(High) over N periods
    Support = MIN(Low) over N periods

Inputs:
- Lookback period: 20 bars
- Volume threshold: 1.5× average

Conditions:
- BUY (Breakout): Close > Resistance AND Volume > 1.5× Avg
- SELL (Breakdown): Close < Support AND Volume > 1.5× Avg

Confidence based on:
- Breakout magnitude (how far above/below level)
- Volume strength
- Time since level was established
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy
from utils.indicators import atr


class BreakoutStrategy(BaseStrategy):
    """
    Breakout - Momentum strategy for trading range breakouts.

    Identifies when price breaks above resistance or below support
    with volume confirmation, signaling a potential trend continuation.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.breakout_lookback = int(params.get("breakout_lookback", 20))
        self.volume_threshold = float(params.get("volume_threshold", 1.5))
        self.quantity = int(params.get("quantity", 1))

    def generate_signals(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Generate breakout signal with full calculation details.

        Formula: BUY when Close > 20-bar High AND Volume > 1.5× Avg
                 SELL when Close < 20-bar Low AND Volume > 1.5× Avg
        """
        if df is None or len(df) < self.breakout_lookback + 2:
            return None

        # Calculate resistance and support levels
        recent = df.iloc[-(self.breakout_lookback + 1):-1]  # Exclude current bar for level calc
        resistance = recent["high"].max()
        support = recent["low"].min()
        range_size = resistance - support

        # Current bar
        last = df.iloc[-1]
        current_price = last["close"]

        # Volume analysis
        vol_avg = recent["volume"].mean()
        volume_ratio = last["volume"] / vol_avg if vol_avg > 0 else 1.0

        # Calculate ATR for stops
        atr_val = atr(df, 14).iloc[-1] if len(df) >= 14 else current_price * 0.02

        # Calculate breakout magnitude
        breakout_above = (current_price - resistance) / resistance * 100 if current_price > resistance else 0
        breakdown_below = (support - current_price) / support * 100 if current_price < support else 0

        # BUY Signal: Price breaks above resistance with volume
        if current_price > resistance and volume_ratio >= self.volume_threshold:
            # Confidence based on breakout strength
            magnitude_confidence = min(0.3, breakout_above / 3.0)  # Up to 3% breakout
            volume_confidence = min(0.3, (volume_ratio - 1) / 3.0)  # Up to 4x volume
            base_confidence = 0.4

            confidence = base_confidence + magnitude_confidence + volume_confidence

            return {
                "action": "BUY",
                "confidence": min(0.95, confidence),
                "reason": f"Breakout: Price ${current_price:.2f} broke above resistance ${resistance:.2f} (+{breakout_above:.1f}%), Vol {volume_ratio:.1f}x",
                "stop_loss": resistance - (atr_val * 0.5),  # Stop just below breakout level
                "take_profit": current_price + (range_size * 1.0),  # Target = range size
                "indicators": {
                    "resistance": round(resistance, 2),
                    "support": round(support, 2),
                    "range_size": round(range_size, 2),
                    "breakout_pct": round(breakout_above, 2),
                    "price": round(current_price, 2),
                    "volume_ratio": round(volume_ratio, 2),
                    "atr": round(atr_val, 2),
                    "lookback_periods": self.breakout_lookback,
                }
            }

        # SELL Signal: Price breaks below support with volume
        if current_price < support and volume_ratio >= self.volume_threshold:
            magnitude_confidence = min(0.3, breakdown_below / 3.0)
            volume_confidence = min(0.3, (volume_ratio - 1) / 3.0)
            base_confidence = 0.4

            confidence = base_confidence + magnitude_confidence + volume_confidence

            return {
                "action": "SELL",
                "confidence": min(0.95, confidence),
                "reason": f"Breakdown: Price ${current_price:.2f} broke below support ${support:.2f} (-{breakdown_below:.1f}%), Vol {volume_ratio:.1f}x",
                "stop_loss": support + (atr_val * 0.5),
                "take_profit": current_price - (range_size * 1.0),
                "indicators": {
                    "resistance": round(resistance, 2),
                    "support": round(support, 2),
                    "range_size": round(range_size, 2),
                    "breakdown_pct": round(breakdown_below, 2),
                    "price": round(current_price, 2),
                    "volume_ratio": round(volume_ratio, 2),
                    "atr": round(atr_val, 2),
                    "lookback_periods": self.breakout_lookback,
                }
            }

        return None

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        df = self._to_df(data)
        if df is None or len(df) < self.breakout_lookback + 1:
            return []

        recent = df.tail(self.breakout_lookback)
        high = recent["high"].max()
        low = recent["low"].min()
        last = df.iloc[-1]
        vol_avg = recent["volume"].mean()

        if last["close"] > high and last["volume"] >= vol_avg * self.volume_threshold:
            return [Signal(symbol=symbol, action="BUY", quantity=self.quantity, order_type="MKT")]
        if last["close"] < low and last["volume"] >= vol_avg * self.volume_threshold:
            return [Signal(symbol=symbol, action="SELL", quantity=self.quantity, order_type="MKT")]
        return []

    def _to_df(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        if "df" in data and isinstance(data["df"], pd.DataFrame):
            return data["df"]
        history = data.get("history")
        if history:
            return pd.DataFrame(history)
        return None
