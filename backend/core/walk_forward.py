"""
Walk-Forward Validation for Backtesting

Implements rolling window validation to test strategy robustness:
1. Split data into in-sample (training) and out-of-sample (validation) periods
2. Backtest on in-sample, validate on out-of-sample
3. Roll forward and repeat for multiple validation windows
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from core.backtest_engine import BacktestConfig, BacktestEngine, BacktestResult
from core.backtest_metrics import BacktestMetricsCalculator, PerformanceMetrics


logger = logging.getLogger(__name__)


@dataclass
class WalkForwardWindow:
    """A single walk-forward validation window."""
    window_number: int

    # In-sample period (training)
    in_sample_start: datetime
    in_sample_end: datetime
    in_sample_result: Optional[BacktestResult] = None
    in_sample_metrics: Optional[PerformanceMetrics] = None

    # Out-of-sample period (validation)
    out_of_sample_start: datetime
    out_of_sample_end: datetime
    out_of_sample_result: Optional[BacktestResult] = None
    out_of_sample_metrics: Optional[PerformanceMetrics] = None

    # Efficiency ratio: OOS performance / IS performance
    efficiency_ratio: float = 0.0


@dataclass
class WalkForwardConfig:
    """Configuration for walk-forward validation."""
    strategy_name: str
    symbol: str
    start_date: datetime
    end_date: datetime
    initial_capital: float = 10000.0
    strategy_parameters: Dict[str, Any] = field(default_factory=dict)

    # Walk-forward settings
    in_sample_ratio: float = 0.7  # 70% in-sample
    num_windows: int = 3  # Number of rolling windows
    anchored: bool = False  # If True, in-sample always starts from beginning

    # Backtest settings
    commission_per_trade: float = 0.0
    slippage_percent: float = 0.1
    bar_size: str = "5 mins"
    lookback_bars: int = 100


@dataclass
class WalkForwardResult:
    """Complete results of walk-forward validation."""
    config: WalkForwardConfig
    windows: List[WalkForwardWindow]

    # Aggregated metrics
    avg_in_sample_return: float = 0.0
    avg_out_of_sample_return: float = 0.0
    avg_efficiency_ratio: float = 0.0

    # Robustness indicators
    is_robust: bool = False
    consistency_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "config": {
                "strategy_name": self.config.strategy_name,
                "symbol": self.config.symbol,
                "start_date": self.config.start_date.isoformat(),
                "end_date": self.config.end_date.isoformat(),
                "initial_capital": self.config.initial_capital,
                "in_sample_ratio": self.config.in_sample_ratio,
                "num_windows": self.config.num_windows,
            },
            "windows": [
                {
                    "window_number": w.window_number,
                    "in_sample": {
                        "start": w.in_sample_start.isoformat(),
                        "end": w.in_sample_end.isoformat(),
                        "return_pct": w.in_sample_metrics.total_return_pct if w.in_sample_metrics else 0,
                        "sharpe": w.in_sample_metrics.sharpe_ratio if w.in_sample_metrics else 0,
                        "trades": w.in_sample_metrics.total_trades if w.in_sample_metrics else 0,
                    },
                    "out_of_sample": {
                        "start": w.out_of_sample_start.isoformat(),
                        "end": w.out_of_sample_end.isoformat(),
                        "return_pct": w.out_of_sample_metrics.total_return_pct if w.out_of_sample_metrics else 0,
                        "sharpe": w.out_of_sample_metrics.sharpe_ratio if w.out_of_sample_metrics else 0,
                        "trades": w.out_of_sample_metrics.total_trades if w.out_of_sample_metrics else 0,
                    },
                    "efficiency_ratio": w.efficiency_ratio,
                }
                for w in self.windows
            ],
            "summary": {
                "avg_in_sample_return": round(self.avg_in_sample_return, 2),
                "avg_out_of_sample_return": round(self.avg_out_of_sample_return, 2),
                "avg_efficiency_ratio": round(self.avg_efficiency_ratio, 4),
                "is_robust": self.is_robust,
                "consistency_score": round(self.consistency_score, 2),
            }
        }


ProgressCallback = Callable[[int, str], None]


class WalkForwardValidator:
    """
    Walk-Forward Validation Engine.

    Performs rolling window backtests to validate strategy robustness
    by comparing in-sample (optimized) performance with out-of-sample
    (forward) performance.
    """

    def __init__(
        self,
        config: WalkForwardConfig,
        progress_callback: Optional[ProgressCallback] = None
    ) -> None:
        self.config = config
        self.progress_callback = progress_callback
        self.metrics_calculator = BacktestMetricsCalculator()

    def _report_progress(self, percent: int, message: str) -> None:
        """Report progress to callback if available."""
        if self.progress_callback:
            self.progress_callback(percent, message)

    def _create_windows(self) -> List[WalkForwardWindow]:
        """Create walk-forward windows based on configuration."""
        total_days = (self.config.end_date - self.config.start_date).days

        if self.config.anchored:
            return self._create_anchored_windows(total_days)
        else:
            return self._create_rolling_windows(total_days)

    def _create_rolling_windows(self, total_days: int) -> List[WalkForwardWindow]:
        """Create rolling (non-anchored) windows."""
        windows = []

        window_days = total_days // self.config.num_windows
        is_days = int(window_days * self.config.in_sample_ratio)
        oos_days = window_days - is_days

        for i in range(self.config.num_windows):
            is_start = self.config.start_date + timedelta(days=i * window_days)
            is_end = is_start + timedelta(days=is_days)
            oos_start = is_end
            oos_end = oos_start + timedelta(days=oos_days)

            if oos_end > self.config.end_date:
                oos_end = self.config.end_date

            windows.append(WalkForwardWindow(
                window_number=i + 1,
                in_sample_start=is_start,
                in_sample_end=is_end,
                out_of_sample_start=oos_start,
                out_of_sample_end=oos_end,
            ))

        return windows

    def _create_anchored_windows(self, total_days: int) -> List[WalkForwardWindow]:
        """Create anchored windows (IS always starts from beginning)."""
        windows = []

        oos_total_days = int(total_days * (1 - self.config.in_sample_ratio))
        oos_per_window = oos_total_days // self.config.num_windows

        for i in range(self.config.num_windows):
            is_start = self.config.start_date
            oos_days_used = i * oos_per_window
            is_end = self.config.end_date - timedelta(days=oos_total_days - oos_days_used)

            oos_start = is_end
            oos_end = oos_start + timedelta(days=oos_per_window)

            if oos_end > self.config.end_date:
                oos_end = self.config.end_date

            windows.append(WalkForwardWindow(
                window_number=i + 1,
                in_sample_start=is_start,
                in_sample_end=is_end,
                out_of_sample_start=oos_start,
                out_of_sample_end=oos_end,
            ))

        return windows

    def _create_backtest_config(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> BacktestConfig:
        """Create a BacktestConfig for a specific period."""
        return BacktestConfig(
            strategy_name=self.config.strategy_name,
            symbol=self.config.symbol,
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.config.initial_capital,
            strategy_parameters=self.config.strategy_parameters,
            commission_per_trade=self.config.commission_per_trade,
            slippage_percent=self.config.slippage_percent,
            bar_size=self.config.bar_size,
            lookback_bars=self.config.lookback_bars,
        )

    def run(self, historical_bars: List[Dict[str, Any]]) -> WalkForwardResult:
        """
        Run walk-forward validation.

        Args:
            historical_bars: Full historical data covering entire date range

        Returns:
            WalkForwardResult with all windows and aggregated metrics
        """
        self._report_progress(0, "Creating walk-forward windows")

        windows = self._create_windows()

        # Convert bars to DataFrame for slicing
        df = pd.DataFrame(historical_bars)

        # Handle date column
        date_col = None
        for col in ["date", "t", "timestamp"]:
            if col in df.columns:
                date_col = col
                break

        if date_col:
            df["date"] = pd.to_datetime(df[date_col])
        else:
            df["date"] = pd.to_datetime(df.index)

        df = df.sort_values("date").reset_index(drop=True)

        total_windows = len(windows)

        # Run backtests for each window
        for i, window in enumerate(windows):
            window_progress_base = int((i / total_windows) * 80)

            self._report_progress(
                window_progress_base,
                f"Processing window {window.window_number}/{total_windows}"
            )

            # Filter data for in-sample period
            is_mask = (df["date"] >= window.in_sample_start) & (df["date"] <= window.in_sample_end)
            is_bars = df[is_mask].to_dict("records")

            # Run in-sample backtest
            if is_bars and len(is_bars) > self.config.lookback_bars:
                is_config = self._create_backtest_config(
                    window.in_sample_start, window.in_sample_end
                )
                is_engine = BacktestEngine(is_config)
                try:
                    window.in_sample_result = is_engine.run(is_bars)
                    window.in_sample_metrics = self.metrics_calculator.calculate(
                        window.in_sample_result
                    )
                except Exception as e:
                    logger.error(f"In-sample backtest failed for window {i+1}: {e}")

            # Filter data for out-of-sample period
            oos_mask = (df["date"] >= window.out_of_sample_start) & (df["date"] <= window.out_of_sample_end)
            oos_bars = df[oos_mask].to_dict("records")

            # Run out-of-sample backtest
            if oos_bars and len(oos_bars) > self.config.lookback_bars:
                oos_config = self._create_backtest_config(
                    window.out_of_sample_start, window.out_of_sample_end
                )
                oos_engine = BacktestEngine(oos_config)
                try:
                    window.out_of_sample_result = oos_engine.run(oos_bars)
                    window.out_of_sample_metrics = self.metrics_calculator.calculate(
                        window.out_of_sample_result
                    )
                except Exception as e:
                    logger.error(f"Out-of-sample backtest failed for window {i+1}: {e}")

            # Calculate efficiency ratio
            if window.in_sample_metrics and window.out_of_sample_metrics:
                is_return = window.in_sample_metrics.total_return_pct
                oos_return = window.out_of_sample_metrics.total_return_pct
                if is_return != 0:
                    window.efficiency_ratio = oos_return / is_return

        self._report_progress(85, "Calculating summary statistics")

        result = self._calculate_summary(windows)

        self._report_progress(100, "Walk-forward validation complete")

        return result

    def _calculate_summary(self, windows: List[WalkForwardWindow]) -> WalkForwardResult:
        """Calculate aggregated summary metrics."""
        is_returns = []
        oos_returns = []
        efficiency_ratios = []
        positive_oos = 0

        for w in windows:
            if w.in_sample_metrics:
                is_returns.append(w.in_sample_metrics.total_return_pct)
            if w.out_of_sample_metrics:
                oos_returns.append(w.out_of_sample_metrics.total_return_pct)
                if w.out_of_sample_metrics.total_return_pct > 0:
                    positive_oos += 1
            if w.efficiency_ratio != 0:
                efficiency_ratios.append(w.efficiency_ratio)

        avg_is = sum(is_returns) / len(is_returns) if is_returns else 0
        avg_oos = sum(oos_returns) / len(oos_returns) if oos_returns else 0
        avg_eff = sum(efficiency_ratios) / len(efficiency_ratios) if efficiency_ratios else 0

        # Consistency score: % of OOS periods with positive returns
        consistency = (positive_oos / len(oos_returns) * 100) if oos_returns else 0

        # Strategy is robust if:
        # 1. Consistency > 60%
        # 2. Average efficiency ratio > 0.5
        is_robust = consistency >= 60 and avg_eff >= 0.5

        return WalkForwardResult(
            config=self.config,
            windows=windows,
            avg_in_sample_return=avg_is,
            avg_out_of_sample_return=avg_oos,
            avg_efficiency_ratio=avg_eff,
            is_robust=is_robust,
            consistency_score=consistency,
        )
