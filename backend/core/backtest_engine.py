"""
Core Backtest Engine for Zella AI Trading

Event-driven simulation that iterates through historical bars,
calls strategy.generate_signals(df), and simulates order execution.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol

import pandas as pd

from core.strategy_engine import STRATEGY_REGISTRY


logger = logging.getLogger(__name__)


class PositionSide(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


@dataclass
class Position:
    """Represents an open position in the backtest."""
    symbol: str
    side: PositionSide
    quantity: int
    entry_price: float
    entry_time: datetime
    entry_reason: str = ""
    entry_confidence: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    commission: float = 0.0
    slippage: float = 0.0


@dataclass
class CompletedTrade:
    """A closed trade with full P&L calculation."""
    symbol: str
    action: str  # BUY or SELL (entry action)
    quantity: int
    entry_time: datetime
    entry_price: float
    entry_reason: str
    entry_confidence: float
    exit_time: datetime
    exit_price: float
    exit_reason: str  # signal / stop_loss / take_profit / end_of_backtest
    pnl: float
    pnl_percent: float
    commission: float
    slippage: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    duration_minutes: int


@dataclass
class EquityPoint:
    """A point on the equity curve."""
    timestamp: datetime
    equity: float
    cash: float
    position_value: float


@dataclass
class BacktestConfig:
    """Configuration for a backtest run."""
    strategy_name: str
    symbol: str
    start_date: datetime
    end_date: datetime
    initial_capital: float = 10000.0
    strategy_parameters: Dict[str, Any] = field(default_factory=dict)

    # Execution modeling
    commission_per_trade: float = 0.0
    slippage_percent: float = 0.1  # 0.1% default

    # Position sizing
    position_size_type: str = "fixed_quantity"  # fixed_quantity / percent_of_equity
    position_size_value: float = 100
    max_position_size_percent: float = 25.0

    # Data settings
    bar_size: str = "5 mins"
    lookback_bars: int = 100

    # Risk management
    use_stop_loss: bool = True
    use_take_profit: bool = True


@dataclass
class BacktestResult:
    """Complete results of a backtest run."""
    config: BacktestConfig
    trades: List[CompletedTrade]
    equity_curve: List[EquityPoint]
    final_equity: float
    total_return: float
    total_return_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    metrics: Dict[str, Any] = field(default_factory=dict)


class ProgressCallback(Protocol):
    """Protocol for progress reporting."""
    def __call__(self, percent: int, message: str) -> None: ...


class BacktestEngine:
    """
    Event-driven backtesting engine.

    Simulates trading by iterating through historical bars,
    feeding data to strategies, and executing simulated orders.
    """

    def __init__(
        self,
        config: BacktestConfig,
        progress_callback: Optional[ProgressCallback] = None
    ) -> None:
        self.config = config
        self.progress_callback = progress_callback

        # State
        self.cash = config.initial_capital
        self.position: Optional[Position] = None
        self.trades: List[CompletedTrade] = []
        self.equity_curve: List[EquityPoint] = []

        # Strategy instance
        self.strategy = None

        logger.info(
            f"BacktestEngine initialized: {config.strategy_name} on {config.symbol} "
            f"from {config.start_date} to {config.end_date}"
        )

    def _report_progress(self, percent: int, message: str) -> None:
        """Report progress to callback if available."""
        if self.progress_callback:
            self.progress_callback(percent, message)

    def _load_strategy(self):
        """Load and instantiate the strategy."""
        if self.config.strategy_name not in STRATEGY_REGISTRY:
            raise ValueError(f"Unknown strategy: {self.config.strategy_name}")

        strategy_class = STRATEGY_REGISTRY[self.config.strategy_name]
        strategy_config = {
            "parameters": self.config.strategy_parameters
        }
        return strategy_class(strategy_config)

    def _calculate_position_size(self, price: float) -> int:
        """Calculate position size based on configuration."""
        equity = self._calculate_equity(price)

        if self.config.position_size_type == "fixed_quantity":
            size = int(self.config.position_size_value)
        elif self.config.position_size_type == "percent_of_equity":
            target_value = equity * (self.config.position_size_value / 100)
            size = int(target_value / price)
        else:
            size = int(self.config.position_size_value)

        # Enforce max position size
        max_value = equity * (self.config.max_position_size_percent / 100)
        max_size = int(max_value / price)
        size = min(size, max_size)

        # Ensure we have enough cash
        required_cash = size * price * (1 + self.config.slippage_percent / 100)
        required_cash += self.config.commission_per_trade
        if required_cash > self.cash:
            size = int(
                (self.cash - self.config.commission_per_trade) /
                (price * (1 + self.config.slippage_percent / 100))
            )

        return max(0, size)

    def _calculate_equity(self, current_price: float) -> float:
        """Calculate current equity including open position value."""
        position_value = 0.0
        if self.position:
            if self.position.side == PositionSide.LONG:
                position_value = self.position.quantity * current_price
            elif self.position.side == PositionSide.SHORT:
                position_value = self.position.quantity * (
                    2 * self.position.entry_price - current_price
                )
        return self.cash + position_value

    def _apply_slippage(self, price: float, is_buy: bool) -> float:
        """Apply slippage to a price."""
        slippage_factor = self.config.slippage_percent / 100
        if is_buy:
            return price * (1 + slippage_factor)
        return price * (1 - slippage_factor)

    def _open_position(
        self,
        timestamp: datetime,
        price: float,
        signal: Dict[str, Any]
    ) -> None:
        """Open a new position based on signal."""
        action = signal.get("action", "").upper()
        if action not in ("BUY", "SELL"):
            return

        quantity = self._calculate_position_size(price)
        if quantity <= 0:
            logger.debug(f"Insufficient capital for position at {timestamp}")
            return

        is_buy = action == "BUY"
        fill_price = self._apply_slippage(price, is_buy)
        commission = self.config.commission_per_trade

        if is_buy:
            cost = quantity * fill_price + commission
            self.cash -= cost
        else:
            proceeds = quantity * fill_price - commission
            self.cash += proceeds

        self.position = Position(
            symbol=self.config.symbol,
            side=PositionSide.LONG if is_buy else PositionSide.SHORT,
            quantity=quantity,
            entry_price=fill_price,
            entry_time=timestamp,
            entry_reason=signal.get("reason", ""),
            entry_confidence=signal.get("confidence", 0.0),
            stop_loss=signal.get("stop_loss") if self.config.use_stop_loss else None,
            take_profit=signal.get("take_profit") if self.config.use_take_profit else None,
            commission=commission,
            slippage=abs(fill_price - price) * quantity
        )

        logger.debug(
            f"Opened {self.position.side.value} position: "
            f"{quantity} @ {fill_price:.2f} at {timestamp}"
        )

    def _close_position(
        self,
        timestamp: datetime,
        price: float,
        reason: str
    ) -> None:
        """Close the current position."""
        if not self.position:
            return

        is_sell = self.position.side == PositionSide.LONG
        fill_price = self._apply_slippage(price, not is_sell)
        commission = self.config.commission_per_trade

        if self.position.side == PositionSide.LONG:
            gross_pnl = (fill_price - self.position.entry_price) * self.position.quantity
            proceeds = self.position.quantity * fill_price - commission
            self.cash += proceeds
        else:
            gross_pnl = (self.position.entry_price - fill_price) * self.position.quantity
            cost = self.position.quantity * fill_price + commission
            self.cash -= cost

        net_pnl = gross_pnl - self.position.commission - commission
        pnl_percent = (net_pnl / (self.position.entry_price * self.position.quantity)) * 100

        duration = int((timestamp - self.position.entry_time).total_seconds() / 60)

        trade = CompletedTrade(
            symbol=self.position.symbol,
            action="BUY" if self.position.side == PositionSide.LONG else "SELL",
            quantity=self.position.quantity,
            entry_time=self.position.entry_time,
            entry_price=self.position.entry_price,
            entry_reason=self.position.entry_reason,
            entry_confidence=self.position.entry_confidence,
            exit_time=timestamp,
            exit_price=fill_price,
            exit_reason=reason,
            pnl=net_pnl,
            pnl_percent=pnl_percent,
            commission=self.position.commission + commission,
            slippage=self.position.slippage + abs(fill_price - price) * self.position.quantity,
            stop_loss=self.position.stop_loss,
            take_profit=self.position.take_profit,
            duration_minutes=duration
        )
        self.trades.append(trade)

        logger.debug(
            f"Closed position: {reason} @ {fill_price:.2f}, "
            f"P&L: ${net_pnl:.2f} ({pnl_percent:.2f}%)"
        )

        self.position = None

    def _check_stop_take_profit(self, bar: Dict[str, Any], timestamp: datetime) -> bool:
        """Check if stop loss or take profit was hit. Returns True if position closed."""
        if not self.position:
            return False

        high = bar.get("high", bar["close"])
        low = bar.get("low", bar["close"])

        # Check stop loss
        if self.position.stop_loss:
            if self.position.side == PositionSide.LONG and low <= self.position.stop_loss:
                self._close_position(timestamp, self.position.stop_loss, "stop_loss")
                return True
            elif self.position.side == PositionSide.SHORT and high >= self.position.stop_loss:
                self._close_position(timestamp, self.position.stop_loss, "stop_loss")
                return True

        # Check take profit
        if self.position.take_profit:
            if self.position.side == PositionSide.LONG and high >= self.position.take_profit:
                self._close_position(timestamp, self.position.take_profit, "take_profit")
                return True
            elif self.position.side == PositionSide.SHORT and low <= self.position.take_profit:
                self._close_position(timestamp, self.position.take_profit, "take_profit")
                return True

        return False

    def _record_equity(self, timestamp: datetime, price: float) -> None:
        """Record a point on the equity curve."""
        position_value = 0.0
        if self.position:
            if self.position.side == PositionSide.LONG:
                position_value = self.position.quantity * price
            else:
                position_value = self.position.quantity * (
                    2 * self.position.entry_price - price
                )

        self.equity_curve.append(EquityPoint(
            timestamp=timestamp,
            equity=self.cash + position_value,
            cash=self.cash,
            position_value=position_value
        ))

    def run(self, historical_bars: List[Dict[str, Any]]) -> BacktestResult:
        """
        Run the backtest on historical data.

        Args:
            historical_bars: List of OHLCV bars from market data provider

        Returns:
            BacktestResult with all trades and metrics
        """
        if not historical_bars:
            raise ValueError("No historical data provided")

        self._report_progress(0, "Initializing backtest")

        # Load strategy
        self.strategy = self._load_strategy()

        # Convert to DataFrame for strategy
        df = pd.DataFrame(historical_bars)

        # Handle date column - could be 'date' or 't' or 'timestamp'
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

        # Ensure required columns
        required_cols = ["open", "high", "low", "close", "volume"]
        for col in required_cols:
            # Handle lowercase/uppercase
            if col not in df.columns:
                upper_col = col.upper()
                lower_col = col.lower()
                if upper_col in df.columns:
                    df[col] = df[upper_col]
                elif lower_col in df.columns:
                    df[col] = df[lower_col]
                elif col == "volume" and "v" in df.columns:
                    df[col] = df["v"]
                elif col == "open" and "o" in df.columns:
                    df[col] = df["o"]
                elif col == "high" and "h" in df.columns:
                    df[col] = df["h"]
                elif col == "low" and "l" in df.columns:
                    df[col] = df["l"]
                elif col == "close" and "c" in df.columns:
                    df[col] = df["c"]
                else:
                    raise ValueError(f"Missing required column: {col}")

        total_bars = len(df)
        lookback = self.config.lookback_bars

        if total_bars <= lookback:
            raise ValueError(
                f"Not enough data: {total_bars} bars, need at least {lookback + 1}"
            )

        self._report_progress(5, f"Processing {total_bars} bars")

        # Main simulation loop
        for i in range(lookback, total_bars):
            current_bar = df.iloc[i].to_dict()
            timestamp = current_bar["date"]
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)

            price = float(current_bar["close"])

            # Get lookback data for strategy
            lookback_df = df.iloc[i - lookback:i + 1].copy()
            lookback_df = lookback_df.reset_index(drop=True)

            # Check stop/take profit on current bar
            if self._check_stop_take_profit(current_bar, timestamp):
                self._record_equity(timestamp, price)
                continue

            # Generate signal from strategy
            try:
                signal = self.strategy.generate_signals(lookback_df)
            except Exception as e:
                logger.warning(f"Strategy error at {timestamp}: {e}")
                signal = None

            # Process signal
            if signal:
                action = signal.get("action", "").upper()

                if action == "BUY":
                    if self.position and self.position.side == PositionSide.SHORT:
                        self._close_position(timestamp, price, "signal")
                    if not self.position:
                        self._open_position(timestamp, price, signal)

                elif action == "SELL":
                    if self.position and self.position.side == PositionSide.LONG:
                        self._close_position(timestamp, price, "signal")
                    if not self.position:
                        self._open_position(timestamp, price, signal)

            # Record equity
            self._record_equity(timestamp, price)

            # Report progress periodically
            progress = int(5 + (i - lookback) / (total_bars - lookback) * 90)
            if i % 100 == 0:
                self._report_progress(progress, f"Processed {i}/{total_bars} bars")

        # Close any open position at end
        if self.position:
            final_price = float(df.iloc[-1]["close"])
            final_time = df.iloc[-1]["date"]
            if isinstance(final_time, str):
                final_time = datetime.fromisoformat(final_time)
            self._close_position(final_time, final_price, "end_of_backtest")

        self._report_progress(95, "Calculating results")

        # Calculate results
        final_equity = self.cash
        total_return = final_equity - self.config.initial_capital
        total_return_pct = (total_return / self.config.initial_capital) * 100

        winning = [t for t in self.trades if t.pnl > 0]
        losing = [t for t in self.trades if t.pnl <= 0]

        result = BacktestResult(
            config=self.config,
            trades=self.trades,
            equity_curve=self.equity_curve,
            final_equity=final_equity,
            total_return=total_return,
            total_return_pct=total_return_pct,
            total_trades=len(self.trades),
            winning_trades=len(winning),
            losing_trades=len(losing)
        )

        self._report_progress(100, "Backtest complete")

        return result
