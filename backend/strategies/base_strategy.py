import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from core.signals import Signal


class BaseStrategy:
    """
    Base class for all trading strategies.

    Strategies must implement either:
    - on_market_data(symbol, data) -> List[Signal] for StrategyEngine
    - generate_signals(df) -> Dict[str, Any] for AutonomousEngine

    If only on_market_data is implemented, generate_signals will
    automatically wrap it to work with the AutonomousEngine.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self._logs: List[str] = []
        self._performance: Dict[str, Any] = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
        }

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        """
        Process market data and return trading signals.
        Override this method in subclasses.

        Args:
            symbol: Stock symbol
            data: Market data dict containing 'df' or 'history'

        Returns:
            List of Signal objects
        """
        return []

    def generate_signals(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Generate trading signals from a DataFrame.
        Used by the AutonomousEngine for autonomous trading.

        This default implementation wraps on_market_data() for backward compatibility.
        Strategies can override this for more detailed signal output.

        Args:
            df: DataFrame with OHLCV data (columns: open, high, low, close, volume)

        Returns:
            Signal dict with: action, confidence, reason (or None for no signal)
        """
        if df is None or len(df) == 0:
            return None

        # Create data dict for on_market_data compatibility
        data = {"df": df}

        # Get symbol from df index if available, otherwise use placeholder
        symbol = df.index.name if hasattr(df, 'index') and df.index.name else "UNKNOWN"

        try:
            signals = self.on_market_data(symbol, data)

            if signals and len(signals) > 0:
                signal = signals[0]  # Take first signal

                # Extract info from Signal object
                action = signal.action if hasattr(signal, 'action') else "HOLD"

                # Calculate confidence based on strategy-specific logic
                confidence = self._calculate_confidence(df, action)

                # Build reason string
                reason = self._build_reason(df, action)

                return {
                    "action": action,
                    "confidence": confidence,
                    "reason": reason,
                    "stop_loss": getattr(signal, 'stop_loss', None),
                    "take_profit": getattr(signal, 'take_profit', None),
                }

            return None

        except Exception as e:
            self.logger.debug(f"Error in generate_signals: {e}")
            return None

    def _calculate_confidence(self, df: pd.DataFrame, action: str) -> float:
        """
        Calculate signal confidence based on market conditions.
        Override in subclasses for strategy-specific confidence.

        Args:
            df: Market data DataFrame
            action: BUY or SELL

        Returns:
            Confidence score between 0.0 and 1.0
        """
        if df is None or len(df) < 5:
            return 0.5

        try:
            # Volume confirmation (higher volume = higher confidence)
            vol_avg = df["volume"].tail(20).mean() if len(df) >= 20 else df["volume"].mean()
            current_vol = df["volume"].iloc[-1]
            volume_ratio = current_vol / vol_avg if vol_avg > 0 else 1.0
            volume_score = min(1.0, volume_ratio / 2.0)  # Max at 2x avg volume

            # Trend alignment (price movement in signal direction)
            if len(df) >= 5:
                price_change = (df["close"].iloc[-1] - df["close"].iloc[-5]) / df["close"].iloc[-5]
                if action == "BUY":
                    trend_score = 0.5 + min(0.3, price_change * 5)  # Positive change helps
                else:  # SELL
                    trend_score = 0.5 + min(0.3, -price_change * 5)  # Negative change helps
            else:
                trend_score = 0.5

            # Combine scores
            confidence = (volume_score * 0.4) + (trend_score * 0.6)
            return max(0.3, min(0.9, confidence))

        except Exception:
            return 0.5

    def _build_reason(self, df: pd.DataFrame, action: str) -> str:
        """
        Build a reason string for the signal.
        Override in subclasses for strategy-specific reasons.
        """
        strategy_name = self.__class__.__name__.replace("Strategy", "")
        return f"{strategy_name} signal: {action}"

    def get_performance(self) -> Dict[str, Any]:
        return self._performance

    def get_logs(self) -> List[str]:
        return self._logs

    def log(self, message: str) -> None:
        self._logs.append(message)
        self.logger.info(message)
