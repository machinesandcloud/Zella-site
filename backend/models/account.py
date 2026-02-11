from __future__ import annotations
from datetime import datetime, date
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class StrategyPerformance(Base):
    __tablename__ = "strategy_performance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    strategy_name: Mapped[str] = mapped_column(String(50), nullable=False)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0)
    losing_trades: Mapped[int] = mapped_column(Integer, default=0)
    total_pnl: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    max_drawdown: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    sharpe_ratio: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    date: Mapped[date] = mapped_column(Date, default=date.today)

    user = relationship("User", back_populates="strategy_performance")


class AccountSnapshot(Base):
    __tablename__ = "account_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    account_value: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))
    cash_balance: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))
    buying_power: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))
    daily_pnl: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    snapshot_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_paper_account: Mapped[Optional[bool]] = mapped_column(Boolean)

    user = relationship("User", back_populates="account_snapshots")
