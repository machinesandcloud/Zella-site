"""
Backtest Models

Database models for storing backtest runs and simulated trades.
"""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class BacktestStatus(enum.Enum):
    """Status of a backtest run."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BacktestRun(Base):
    """
    Stores metadata and results for a single backtest execution.
    """
    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # Configuration
    strategy_name: Mapped[str] = mapped_column(String(50), nullable=False)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    initial_capital: Mapped[float] = mapped_column(Float, default=10000.0)
    parameters: Mapped[Optional[dict]] = mapped_column(JSON)

    # Execution settings
    commission_per_trade: Mapped[float] = mapped_column(Float, default=0.0)
    slippage_percent: Mapped[float] = mapped_column(Float, default=0.0)
    bar_size: Mapped[str] = mapped_column(String(20), default="5 mins")

    # Status tracking
    status: Mapped[str] = mapped_column(String(20), default=BacktestStatus.PENDING.value)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Performance Metrics
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0)
    losing_trades: Mapped[int] = mapped_column(Integer, default=0)
    total_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    total_return_pct: Mapped[float] = mapped_column(Float, default=0.0)
    ending_equity: Mapped[float] = mapped_column(Float, default=0.0)

    # Risk metrics
    max_drawdown: Mapped[Optional[float]] = mapped_column(Float)
    max_drawdown_pct: Mapped[Optional[float]] = mapped_column(Float)
    sharpe_ratio: Mapped[Optional[float]] = mapped_column(Float)
    sortino_ratio: Mapped[Optional[float]] = mapped_column(Float)
    calmar_ratio: Mapped[Optional[float]] = mapped_column(Float)

    # Trade statistics
    win_rate: Mapped[Optional[float]] = mapped_column(Float)
    profit_factor: Mapped[Optional[float]] = mapped_column(Float)
    avg_win: Mapped[Optional[float]] = mapped_column(Float)
    avg_loss: Mapped[Optional[float]] = mapped_column(Float)
    avg_trade_duration_minutes: Mapped[Optional[float]] = mapped_column(Float)
    max_consecutive_wins: Mapped[int] = mapped_column(Integer, default=0)
    max_consecutive_losses: Mapped[int] = mapped_column(Integer, default=0)

    # Equity curve stored as JSON array
    equity_curve: Mapped[Optional[list]] = mapped_column(JSON)

    # Relationships
    user = relationship("User", back_populates="backtest_runs")
    trades = relationship(
        "BacktestTrade",
        back_populates="backtest_run",
        cascade="all, delete-orphan"
    )


class BacktestTrade(Base):
    """
    Individual simulated trade within a backtest run.
    """
    __tablename__ = "backtest_trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    backtest_run_id: Mapped[int] = mapped_column(
        ForeignKey("backtest_runs.id", ondelete="CASCADE")
    )

    # Trade details
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    action: Mapped[str] = mapped_column(String(10), nullable=False)  # BUY/SELL
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # Entry
    entry_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    entry_price: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    entry_reason: Mapped[Optional[str]] = mapped_column(Text)
    entry_confidence: Mapped[Optional[float]] = mapped_column(Float)

    # Exit
    exit_time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    exit_price: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    exit_reason: Mapped[Optional[str]] = mapped_column(String(50))

    # P&L
    pnl: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    pnl_percent: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    commission: Mapped[float] = mapped_column(Float, default=0.0)
    slippage: Mapped[float] = mapped_column(Float, default=0.0)

    # Stop/Target levels
    stop_loss: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    take_profit: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))

    # Duration
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer)

    # Relationship
    backtest_run = relationship("BacktestRun", back_populates="trades")
