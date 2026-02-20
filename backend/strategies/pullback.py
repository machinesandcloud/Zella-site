"""
Pullback Strategy

Formula:
    Pullback % = ((Recent High - Current Price) / Recent High) × 100
    Trend Filter = Price > EMA(50)

Inputs:
- Pullback threshold: 0.5% minimum pullback
- Trend EMA period: 50 bars

Conditions:
- BUY: In uptrend (Price > EMA) AND pullback from high >= 0.5%
- SELL: In downtrend (Price < EMA) AND rally from low >= 0.5%

This strategy buys dips in uptrends and sells rallies in downtrends.
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal
from strategies.base_strategy import BaseStrategy
from utils.indicators import ema, atr


class PullbackStrategy(BaseStrategy):
    """
    Pullback - Buy the dip / Sell the rally in trending markets.

    Identifies temporary retracements within larger trends
    as opportunities to enter at better prices.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        params = config.get("parameters", {})
        self.pullback_percent = float(params.get("pullback_percent", 0.5))
        self.trend_ema = int(params.get("trend_ema", 50))
        self.quantity = int(params.get("quantity", 1))

    def generate_signals(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Generate pullback signal with full calculation details.

        Formula: BUY when (Price > EMA50) AND (Pullback >= 0.5%)
                 SELL when (Price < EMA50) AND (Rally >= 0.5%)
        """
        if df is None or len(df) < self.trend_ema + 5:
            return None

        # Calculate trend EMA
        ema_series = ema(df["close"], self.trend_ema)
        current_ema = ema_series.iloc[-1]

        # Current price
        current_price = df["close"].iloc[-1]

        # Calculate recent high and low
        recent_high = df["high"].tail(self.trend_ema).max()
        recent_low = df["low"].tail(self.trend_ema).min()

        # Volume analysis
        vol_avg = df["volume"].tail(20).mean() if len(df) >= 20 else df["volume"].mean()
        volume_ratio = df["volume"].iloc[-1] / vol_avg if vol_avg > 0 else 1.0

        # Calculate ATR
        atr_val = atr(df, 14).iloc[-1] if len(df) >= 14 else current_price * 0.02

        # BUY Signal: Uptrend with pullback
        if current_price > current_ema:
            pullback_pct = ((recent_high - current_price) / recent_high) * 100

            if pullback_pct >= self.pullback_percent:
                # Confidence based on pullback depth and trend strength
                pullback_confidence = min(0.3, pullback_pct / 5.0)  # Deeper pullback = higher confidence up to 5%
                trend_strength = (current_price - current_ema) / current_ema * 100
                trend_confidence = min(0.3, trend_strength / 3.0)
                volume_confidence = min(0.2, (volume_ratio - 1) * 0.1) if volume_ratio > 1 else 0

                confidence = 0.4 + pullback_confidence + trend_confidence + volume_confidence

                return {
                    "action": "BUY",
                    "confidence": min(0.95, confidence),
                    "reason": f"Pullback buy: {pullback_pct:.2f}% dip from ${recent_high:.2f}, in uptrend above EMA{self.trend_ema}",
                    "stop_loss": current_ema - (atr_val * 1),  # Stop below EMA
                    "take_profit": recent_high + (atr_val * 1),  # Target above recent high
                    "indicators": {
                        "trend_ema": round(current_ema, 2),
                        "recent_high": round(recent_high, 2),
                        "recent_low": round(recent_low, 2),
                        "pullback_pct": round(pullback_pct, 2),
                        "trend_strength_pct": round((current_price - current_ema) / current_ema * 100, 2),
                        "price": round(current_price, 2),
                        "volume_ratio": round(volume_ratio, 2),
                        "atr": round(atr_val, 2),
                    }
                }

        # SELL Signal: Downtrend with rally
        if current_price < current_ema:
            rally_pct = ((current_price - recent_low) / recent_low) * 100

            if rally_pct >= self.pullback_percent:
                rally_confidence = min(0.3, rally_pct / 5.0)
                trend_strength = abs((current_price - current_ema) / current_ema * 100)
                trend_confidence = min(0.3, trend_strength / 3.0)
                volume_confidence = min(0.2, (volume_ratio - 1) * 0.1) if volume_ratio > 1 else 0

                confidence = 0.4 + rally_confidence + trend_confidence + volume_confidence

                return {
                    "action": "SELL",
                    "confidence": min(0.95, confidence),
                    "reason": f"Rally fade: {rally_pct:.2f}% bounce from ${recent_low:.2f}, in downtrend below EMA{self.trend_ema}",
                    "stop_loss": current_ema + (atr_val * 1),
                    "take_profit": recent_low - (atr_val * 1),
                    "indicators": {
                        "trend_ema": round(current_ema, 2),
                        "recent_high": round(recent_high, 2),
                        "recent_low": round(recent_low, 2),
                        "rally_pct": round(rally_pct, 2),
                        "trend_strength_pct": round((current_ema - current_price) / current_ema * 100, 2),
                        "price": round(current_price, 2),
                        "volume_ratio": round(volume_ratio, 2),
                        "atr": round(atr_val, 2),
                    }
                }

        return None

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        df = self._to_df(data)
        if df is None or len(df) < self.trend_ema:
            return []

        ema_series = ema(df["close"], self.trend_ema)
        last_close = df.iloc[-1]["close"]
        recent_high = df["high"].tail(self.trend_ema).max()

        if last_close > ema_series.iloc[-1]:
            pullback = ((recent_high - last_close) / recent_high) * 100
            if pullback >= self.pullback_percent:
                return [Signal(symbol=symbol, action="BUY", quantity=self.quantity, order_type="MKT")]

        if last_close < ema_series.iloc[-1]:
            pullback = ((last_close - recent_high) / recent_high) * 100
            if pullback <= -self.pullback_percent:
                return [Signal(symbol=symbol, action="SELL", quantity=self.quantity, order_type="MKT")]

        return []

    def _to_df(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        if "df" in data and isinstance(data["df"], pd.DataFrame):
            return data["df"]
        history = data.get("history")
        if history:
            return pd.DataFrame(history)
        return None
