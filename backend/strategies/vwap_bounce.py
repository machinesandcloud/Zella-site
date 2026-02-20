"""
VWAP Bounce Strategy

Formula: BUY when Price crosses ABOVE VWAP with volume confirmation
         SELL when Price crosses BELOW VWAP with volume confirmation

Inputs:
- VWAP = Σ(Price × Volume) / Σ(Volume)
- Volume Ratio = Current Volume / 20-bar Average Volume
- Wick Percent = (max(High-Close, Close-Low) / Close) × 100

Conditions:
- BUY: (Prev Close < Prev VWAP) AND (Close > VWAP) AND (Volume > 1.5× Avg) AND (Wick > 2%)
- SELL: (Prev Close > Prev VWAP) AND (Close < VWAP) AND (Volume > 1.5× Avg) AND (Wick > 2%)
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy
from utils.indicators import vwap, atr


class VWAPBounceStrategy(BaseStrategy):
    """
    VWAP Bounce - Mean reversion strategy using Volume Weighted Average Price.

    This strategy identifies when price crosses the VWAP with strong volume,
    suggesting institutional buying/selling pressure.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.vwap_period = int(params.get("vwap_period", 20))
        self.volume_threshold = float(params.get("volume_threshold", 1.5))
        self.min_wick_percent = float(params.get("min_wick_percent", 2))
        self.quantity = int(params.get("quantity", 1))

    def generate_signals(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Generate VWAP bounce signal with full calculation details.

        Formula: BUY when (Prev Close < Prev VWAP) AND (Close > VWAP) AND (Vol > 1.5x Avg)
        """
        if df is None or len(df) < self.vwap_period:
            return None

        # Calculate VWAP
        recent_df = df.tail(self.vwap_period).copy()
        vw = vwap(recent_df)
        last = recent_df.iloc[-1]
        prev = recent_df.iloc[-2]

        # Calculate key metrics
        current_vwap = vw.iloc[-1]
        prev_vwap = vw.iloc[-2]
        vol_avg = recent_df["volume"].mean()
        current_vol = last["volume"]
        volume_ratio = current_vol / vol_avg if vol_avg > 0 else 0
        wick_percent = self._wick_percent(last)

        # Calculate price distance from VWAP
        vwap_distance = ((last["close"] - current_vwap) / current_vwap * 100) if current_vwap > 0 else 0

        # Calculate ATR for stop loss
        atr_val = atr(df, 14).iloc[-1] if len(df) >= 14 else last["close"] * 0.02

        # BUY Signal: Price crosses above VWAP
        if (
            prev["close"] < prev_vwap
            and last["close"] > current_vwap
            and volume_ratio >= self.volume_threshold
            and wick_percent >= self.min_wick_percent
        ):
            # Confidence based on volume strength and VWAP distance
            vol_confidence = min(1.0, volume_ratio / 3.0)  # Max confidence at 3x volume
            cross_confidence = min(1.0, abs(vwap_distance) / 1.0)  # Distance from VWAP
            confidence = 0.5 + (vol_confidence * 0.3) + (cross_confidence * 0.2)

            return {
                "action": "BUY",
                "confidence": min(0.95, confidence),
                "reason": f"VWAP bounce: Price ${last['close']:.2f} crossed above VWAP ${current_vwap:.2f}, Volume {volume_ratio:.1f}x avg",
                "stop_loss": last["close"] - (atr_val * 2),
                "take_profit": last["close"] + (atr_val * 3),
                "indicators": {
                    "vwap": round(current_vwap, 2),
                    "price": round(last["close"], 2),
                    "vwap_distance_pct": round(vwap_distance, 2),
                    "volume_ratio": round(volume_ratio, 2),
                    "wick_percent": round(wick_percent, 2),
                    "atr": round(atr_val, 2),
                }
            }

        # SELL Signal: Price crosses below VWAP
        if (
            prev["close"] > prev_vwap
            and last["close"] < current_vwap
            and volume_ratio >= self.volume_threshold
            and wick_percent >= self.min_wick_percent
        ):
            vol_confidence = min(1.0, volume_ratio / 3.0)
            cross_confidence = min(1.0, abs(vwap_distance) / 1.0)
            confidence = 0.5 + (vol_confidence * 0.3) + (cross_confidence * 0.2)

            return {
                "action": "SELL",
                "confidence": min(0.95, confidence),
                "reason": f"VWAP breakdown: Price ${last['close']:.2f} crossed below VWAP ${current_vwap:.2f}, Volume {volume_ratio:.1f}x avg",
                "stop_loss": last["close"] + (atr_val * 2),
                "take_profit": last["close"] - (atr_val * 3),
                "indicators": {
                    "vwap": round(current_vwap, 2),
                    "price": round(last["close"], 2),
                    "vwap_distance_pct": round(vwap_distance, 2),
                    "volume_ratio": round(volume_ratio, 2),
                    "wick_percent": round(wick_percent, 2),
                    "atr": round(atr_val, 2),
                }
            }

        return None

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        df = self._to_df(data)
        if df is None or len(df) < self.vwap_period:
            return []

        df = df.tail(self.vwap_period)
        vw = vwap(df)
        last = df.iloc[-1]
        prev = df.iloc[-2]

        vol_avg = df["volume"].rolling(self.vwap_period).mean().iloc[-1]
        wick_percent = self._wick_percent(last)

        if (
            prev["close"] < vw.iloc[-2]
            and last["close"] > vw.iloc[-1]
            and last["volume"] >= vol_avg * self.volume_threshold
            and wick_percent >= self.min_wick_percent
        ):
            return [Signal(symbol=symbol, action="BUY", quantity=self.quantity, order_type="MKT")]

        if (
            prev["close"] > vw.iloc[-2]
            and last["close"] < vw.iloc[-1]
            and last["volume"] >= vol_avg * self.volume_threshold
            and wick_percent >= self.min_wick_percent
        ):
            return [Signal(symbol=symbol, action="SELL", quantity=self.quantity, order_type="MKT")]

        return []

    def _wick_percent(self, bar: pd.Series) -> float:
        high = bar["high"]
        low = bar["low"]
        close = bar["close"]
        if close == 0:
            return 0.0
        wick = max(high - close, close - low)
        return (wick / close) * 100

    def _to_df(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        if "df" in data and isinstance(data["df"], pd.DataFrame):
            return data["df"]
        history = data.get("history")
        if history:
            return pd.DataFrame(history)
        return None
