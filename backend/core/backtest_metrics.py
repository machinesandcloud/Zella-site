"""
Performance Metrics Calculator for Backtesting

Calculates comprehensive risk-adjusted performance metrics including:
- Sharpe Ratio
- Sortino Ratio
- Max Drawdown
- Calmar Ratio
- Win Rate, Profit Factor, etc.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import numpy as np

from core.backtest_engine import BacktestResult, CompletedTrade, EquityPoint


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics."""
    # Return metrics
    total_return: float
    total_return_pct: float
    annualized_return_pct: float

    # Risk metrics
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    calmar_ratio: float
    volatility_annualized: float

    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    avg_win_loss_ratio: float
    expectancy: float

    # Consecutive stats
    max_consecutive_wins: int
    max_consecutive_losses: int

    # Duration stats
    avg_trade_duration_minutes: float
    avg_winning_duration_minutes: float
    avg_losing_duration_minutes: float

    # Equity curve stats
    peak_equity: float
    trough_equity: float
    recovery_factor: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_return": round(self.total_return, 2),
            "total_return_pct": round(self.total_return_pct, 2),
            "annualized_return_pct": round(self.annualized_return_pct, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 4),
            "sortino_ratio": round(self.sortino_ratio, 4),
            "max_drawdown": round(self.max_drawdown, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "calmar_ratio": round(self.calmar_ratio, 4),
            "volatility_annualized": round(self.volatility_annualized, 4),
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": round(self.win_rate, 2),
            "profit_factor": round(self.profit_factor, 4),
            "avg_win": round(self.avg_win, 2),
            "avg_loss": round(self.avg_loss, 2),
            "avg_win_loss_ratio": round(self.avg_win_loss_ratio, 4),
            "expectancy": round(self.expectancy, 2),
            "max_consecutive_wins": self.max_consecutive_wins,
            "max_consecutive_losses": self.max_consecutive_losses,
            "avg_trade_duration_minutes": round(self.avg_trade_duration_minutes, 1),
            "avg_winning_duration_minutes": round(self.avg_winning_duration_minutes, 1),
            "avg_losing_duration_minutes": round(self.avg_losing_duration_minutes, 1),
            "peak_equity": round(self.peak_equity, 2),
            "trough_equity": round(self.trough_equity, 2),
            "recovery_factor": round(self.recovery_factor, 4),
        }


class BacktestMetricsCalculator:
    """
    Calculates comprehensive performance metrics from backtest results.

    Formulas:
    - Sharpe Ratio: (avg_return - risk_free_rate) / std_return * sqrt(252)
    - Sortino Ratio: (avg_return - risk_free_rate) / downside_deviation * sqrt(252)
    - Max Drawdown: max(peak - current) / peak
    - Calmar Ratio: annualized_return / max_drawdown
    - Profit Factor: gross_profit / gross_loss
    """

    TRADING_DAYS_PER_YEAR = 252

    def __init__(self, risk_free_rate: float = 0.02) -> None:
        """
        Initialize calculator.

        Args:
            risk_free_rate: Annual risk-free rate (default 2%)
        """
        self.risk_free_rate = risk_free_rate

    def calculate(self, result: BacktestResult) -> PerformanceMetrics:
        """Calculate all performance metrics from backtest result."""
        equity_values = [ep.equity for ep in result.equity_curve]
        trades = result.trades
        initial_capital = result.config.initial_capital

        if not equity_values:
            return self._empty_metrics(initial_capital)

        # Calculate returns
        returns = self._calculate_returns(equity_values)

        # Calculate drawdown series
        max_dd, max_dd_pct, peak, trough = self._calculate_drawdown(
            equity_values, initial_capital
        )

        # Calculate trading days for annualization
        if len(result.equity_curve) >= 2:
            first_date = result.equity_curve[0].timestamp
            last_date = result.equity_curve[-1].timestamp
            days = (last_date - first_date).days
            trading_days = max(1, days * 252 / 365)
        else:
            trading_days = 1

        # Annualized return
        total_return_factor = result.final_equity / initial_capital
        years = trading_days / self.TRADING_DAYS_PER_YEAR
        if years > 0 and total_return_factor > 0:
            annualized_return_pct = (total_return_factor ** (1 / years) - 1) * 100
        else:
            annualized_return_pct = 0

        # Risk metrics
        sharpe = self._calculate_sharpe_ratio(returns)
        sortino = self._calculate_sortino_ratio(returns)
        volatility = self._calculate_annualized_volatility(returns)
        calmar = self._calculate_calmar_ratio(annualized_return_pct / 100, max_dd_pct / 100)

        # Trade statistics
        trade_stats = self._calculate_trade_statistics(trades)

        # Recovery factor
        recovery_factor = result.total_return / max_dd if max_dd > 0 else 0

        return PerformanceMetrics(
            total_return=result.total_return,
            total_return_pct=result.total_return_pct,
            annualized_return_pct=annualized_return_pct,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=max_dd,
            max_drawdown_pct=max_dd_pct,
            calmar_ratio=calmar,
            volatility_annualized=volatility,
            **trade_stats,
            peak_equity=peak,
            trough_equity=trough,
            recovery_factor=recovery_factor,
        )

    def _empty_metrics(self, initial_capital: float) -> PerformanceMetrics:
        """Return empty metrics when no data available."""
        return PerformanceMetrics(
            total_return=0, total_return_pct=0, annualized_return_pct=0,
            sharpe_ratio=0, sortino_ratio=0, max_drawdown=0, max_drawdown_pct=0,
            calmar_ratio=0, volatility_annualized=0, total_trades=0,
            winning_trades=0, losing_trades=0, win_rate=0, profit_factor=0,
            avg_win=0, avg_loss=0, avg_win_loss_ratio=0, expectancy=0,
            max_consecutive_wins=0, max_consecutive_losses=0,
            avg_trade_duration_minutes=0, avg_winning_duration_minutes=0,
            avg_losing_duration_minutes=0, peak_equity=initial_capital,
            trough_equity=initial_capital, recovery_factor=0
        )

    def _calculate_returns(self, equity_values: List[float]) -> np.ndarray:
        """Calculate period-over-period returns."""
        equity = np.array(equity_values)
        # Avoid division by zero
        equity = np.where(equity == 0, 1e-10, equity)
        returns = np.diff(equity) / equity[:-1]
        return returns

    def _calculate_drawdown(
        self,
        equity_values: List[float],
        initial_capital: float
    ) -> tuple:
        """
        Calculate max drawdown.

        Returns:
            (max_drawdown, max_drawdown_pct, peak, trough)
        """
        equity = np.array(equity_values)
        running_max = np.maximum.accumulate(equity)
        drawdowns = running_max - equity
        drawdown_pct = np.where(running_max > 0, (drawdowns / running_max) * 100, 0)

        max_dd = float(np.max(drawdowns))
        max_dd_pct = float(np.max(drawdown_pct))

        peak = float(np.max(equity))
        trough = float(np.min(equity))

        return max_dd, max_dd_pct, peak, trough

    def _calculate_sharpe_ratio(self, returns: np.ndarray) -> float:
        """
        Calculate Sharpe Ratio.

        Formula: (avg_return - risk_free_daily) / std_return * sqrt(252)
        """
        if len(returns) < 2:
            return 0.0

        risk_free_daily = self.risk_free_rate / self.TRADING_DAYS_PER_YEAR

        avg_return = np.mean(returns)
        std_return = np.std(returns, ddof=1)

        if std_return == 0 or np.isnan(std_return):
            return 0.0

        sharpe = (avg_return - risk_free_daily) / std_return
        return float(sharpe * np.sqrt(self.TRADING_DAYS_PER_YEAR))

    def _calculate_sortino_ratio(self, returns: np.ndarray) -> float:
        """
        Calculate Sortino Ratio.

        Formula: (avg_return - risk_free_daily) / downside_deviation * sqrt(252)
        Only considers negative returns for volatility.
        """
        if len(returns) < 2:
            return 0.0

        risk_free_daily = self.risk_free_rate / self.TRADING_DAYS_PER_YEAR

        avg_return = np.mean(returns)

        # Downside deviation: std of returns below target
        downside_returns = returns[returns < risk_free_daily]
        if len(downside_returns) < 2:
            return 0.0

        downside_dev = np.std(downside_returns, ddof=1)

        if downside_dev == 0 or np.isnan(downside_dev):
            return 0.0

        sortino = (avg_return - risk_free_daily) / downside_dev
        return float(sortino * np.sqrt(self.TRADING_DAYS_PER_YEAR))

    def _calculate_calmar_ratio(
        self,
        annualized_return: float,
        max_drawdown_pct: float
    ) -> float:
        """
        Calculate Calmar Ratio.

        Formula: annualized_return / max_drawdown
        """
        if max_drawdown_pct == 0:
            return 0.0
        return annualized_return / max_drawdown_pct

    def _calculate_annualized_volatility(self, returns: np.ndarray) -> float:
        """Calculate annualized volatility (standard deviation)."""
        if len(returns) < 2:
            return 0.0
        std = np.std(returns, ddof=1)
        if np.isnan(std):
            return 0.0
        return float(std * np.sqrt(self.TRADING_DAYS_PER_YEAR))

    def _calculate_trade_statistics(self, trades: List[CompletedTrade]) -> Dict[str, Any]:
        """Calculate trade-level statistics."""
        total = len(trades)

        if total == 0:
            return {
                "total_trades": 0, "winning_trades": 0, "losing_trades": 0,
                "win_rate": 0, "profit_factor": 0, "avg_win": 0, "avg_loss": 0,
                "avg_win_loss_ratio": 0, "expectancy": 0,
                "max_consecutive_wins": 0, "max_consecutive_losses": 0,
                "avg_trade_duration_minutes": 0,
                "avg_winning_duration_minutes": 0,
                "avg_losing_duration_minutes": 0,
            }

        winners = [t for t in trades if t.pnl > 0]
        losers = [t for t in trades if t.pnl <= 0]

        win_count = len(winners)
        loss_count = len(losers)

        # Win rate
        win_rate = (win_count / total) * 100

        # Gross profit/loss
        gross_profit = sum(t.pnl for t in winners) if winners else 0
        gross_loss = abs(sum(t.pnl for t in losers)) if losers else 0

        # Profit factor
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        # Average win/loss
        avg_win = gross_profit / win_count if win_count > 0 else 0
        avg_loss = gross_loss / loss_count if loss_count > 0 else 0

        # Win/loss ratio
        avg_win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0

        # Expectancy
        expectancy = (win_rate / 100 * avg_win) - ((1 - win_rate / 100) * avg_loss)

        # Consecutive wins/losses
        max_consec_wins, max_consec_losses = self._calculate_consecutive_stats(trades)

        # Durations
        all_durations = [t.duration_minutes for t in trades if t.duration_minutes]
        win_durations = [t.duration_minutes for t in winners if t.duration_minutes]
        loss_durations = [t.duration_minutes for t in losers if t.duration_minutes]

        avg_duration = sum(all_durations) / len(all_durations) if all_durations else 0
        avg_win_duration = sum(win_durations) / len(win_durations) if win_durations else 0
        avg_loss_duration = sum(loss_durations) / len(loss_durations) if loss_durations else 0

        return {
            "total_trades": total,
            "winning_trades": win_count,
            "losing_trades": loss_count,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "avg_win_loss_ratio": avg_win_loss_ratio,
            "expectancy": expectancy,
            "max_consecutive_wins": max_consec_wins,
            "max_consecutive_losses": max_consec_losses,
            "avg_trade_duration_minutes": avg_duration,
            "avg_winning_duration_minutes": avg_win_duration,
            "avg_losing_duration_minutes": avg_loss_duration,
        }

    def _calculate_consecutive_stats(
        self,
        trades: List[CompletedTrade]
    ) -> tuple:
        """Calculate max consecutive wins and losses."""
        if not trades:
            return 0, 0

        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0

        for trade in trades:
            if trade.pnl > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)

        return max_wins, max_losses
