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
        self.volume_threshold = float(params.get("volume_threshold", 1.0))  # Was 1.5x — IEX feed shows ~3% of real volume so ratio comparisons are noisy; screener already passed RVol > 1.5x upstream
        self.min_wick_percent = float(params.get("min_wick_percent", 0.5))
        self.quantity = int(params.get("quantity", 1))
        # Bars above/below VWAP required for trend mode (research: sustained trend > crossover)
        self.trend_bars_required = int(params.get("trend_bars_required", 3))

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

        # Calculate ATR for stop loss / take profit
        atr_val = atr(df, 14).iloc[-1] if len(df) >= 14 else last["close"] * 0.02

        # --- TREND MODE: sustained position above/below VWAP (Zarattini 2024 approach) ---
        # Count consecutive bars on same side of VWAP — trend is stronger than one crossover
        n = min(self.trend_bars_required, len(recent_df) - 1)
        bars_above = all(
            recent_df["close"].iloc[-i - 1] > vw.iloc[-i - 1]
            for i in range(n)
        )
        bars_below = all(
            recent_df["close"].iloc[-i - 1] < vw.iloc[-i - 1]
            for i in range(n)
        )

        # --- CROSSOVER MODE: classic VWAP bounce ---
        crossover_buy = (
            prev["close"] < prev_vwap
            and last["close"] > current_vwap
            and volume_ratio >= self.volume_threshold
            and wick_percent >= self.min_wick_percent
        )
        crossover_sell = (
            prev["close"] > prev_vwap
            and last["close"] < current_vwap
            and volume_ratio >= self.volume_threshold
            and wick_percent >= self.min_wick_percent
        )

        # BUY Signal: crossover OR sustained trend above VWAP with volume
        if crossover_buy or (bars_above and volume_ratio >= self.volume_threshold):
            # Proximity: tighter to VWAP = cleaner bounce (reward <0.5% distance)
            proximity_score = 0.20 if abs(vwap_distance) < 0.5 else 0.10 if abs(vwap_distance) < 1.0 else 0.03
            # Wick: large rejection wick signals institutional support
            wick_score = min(0.20, wick_percent / 5.0)
            # Volume: reward 1.5x-3x range; diminishing above 3x (climactic, not sustainable)
            vol_score = min(0.20, (volume_ratio - 1.5) / 1.5) if volume_ratio >= 1.5 else 0
            # Trend bonus only for multi-bar sustained trend above VWAP
            trend_bonus = 0.10 if bars_above and not crossover_buy else 0
            confidence = 0.40 + proximity_score + wick_score + vol_score + trend_bonus

            mode = "Trend" if bars_above and not crossover_buy else "Bounce"
            return {
                "action": "BUY",
                "confidence": min(0.88, confidence),
                "reason": f"VWAP {mode}: ${last['close']:.2f} > VWAP ${current_vwap:.2f} ({volume_ratio:.1f}x vol)",
                "stop_loss": last["close"] - (atr_val * 1.5),
                "take_profit": last["close"] + (atr_val * 3.75),  # 2.5:1 R/R (was 1.67:1)
                "indicators": {
                    "vwap": round(current_vwap, 2),
                    "price": round(last["close"], 2),
                    "vwap_distance_pct": round(vwap_distance, 2),
                    "volume_ratio": round(volume_ratio, 2),
                    "wick_percent": round(wick_percent, 2),
                    "atr": round(atr_val, 2),
                    "mode": mode,
                }
            }

        # SELL Signal: crossover OR sustained trend below VWAP with volume
        if crossover_sell or (bars_below and volume_ratio >= self.volume_threshold):
            proximity_score = 0.20 if abs(vwap_distance) < 0.5 else 0.10 if abs(vwap_distance) < 1.0 else 0.03
            wick_score = min(0.20, wick_percent / 5.0)
            vol_score = min(0.20, (volume_ratio - 1.5) / 1.5) if volume_ratio >= 1.5 else 0
            trend_bonus = 0.10 if bars_below and not crossover_sell else 0
            confidence = 0.40 + proximity_score + wick_score + vol_score + trend_bonus

            mode = "Trend" if bars_below and not crossover_sell else "Break"
            return {
                "action": "SELL",
                "confidence": min(0.88, confidence),
                "reason": f"VWAP {mode}: ${last['close']:.2f} < VWAP ${current_vwap:.2f} ({volume_ratio:.1f}x vol)",
                "stop_loss": last["close"] + (atr_val * 1.5),
                "take_profit": last["close"] - (atr_val * 3.75),  # 2.5:1 R/R (was 1.67:1)
                "indicators": {
                    "vwap": round(current_vwap, 2),
                    "price": round(last["close"], 2),
                    "vwap_distance_pct": round(vwap_distance, 2),
                    "volume_ratio": round(volume_ratio, 2),
                    "wick_percent": round(wick_percent, 2),
                    "atr": round(atr_val, 2),
                    "mode": mode,
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
