from __future__ import annotations
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    strategy_name: Mapped[Optional[str]] = mapped_column(String(50))
    action: Mapped[str] = mapped_column(String(4), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_price: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    exit_price: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    stop_loss: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    take_profit: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    pnl: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    pnl_percent: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    commission: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    entry_time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    exit_time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    status: Mapped[Optional[str]] = mapped_column(String(20))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    setup_tag: Mapped[Optional[str]] = mapped_column(String(50))
    catalyst: Mapped[Optional[str]] = mapped_column(String(120))
    stop_method: Mapped[Optional[str]] = mapped_column(String(30))
    risk_mode: Mapped[Optional[str]] = mapped_column(String(20))
    is_paper_trade: Mapped[bool] = mapped_column(Boolean, default=True)

    user = relationship("User", back_populates="trades")
    orders = relationship("Order", back_populates="trade", cascade="all, delete-orphan")
