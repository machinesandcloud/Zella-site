from __future__ import annotations
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    trade_id: Mapped[Optional[int]] = mapped_column(ForeignKey("trades.id"))
    ibkr_order_id: Mapped[Optional[int]] = mapped_column(Integer)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    asset_type: Mapped[Optional[str]] = mapped_column(String(10), default="STK")
    exchange: Mapped[Optional[str]] = mapped_column(String(20))
    currency: Mapped[Optional[str]] = mapped_column(String(10))
    expiry: Mapped[Optional[str]] = mapped_column(String(20))
    strike: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    right: Mapped[Optional[str]] = mapped_column(String(4))
    multiplier: Mapped[Optional[str]] = mapped_column(String(10))
    order_type: Mapped[str] = mapped_column(String(20), nullable=False)
    action: Mapped[str] = mapped_column(String(4), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    limit_price: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    stop_price: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    filled_quantity: Mapped[int] = mapped_column(Integer, default=0)
    avg_fill_price: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    status: Mapped[Optional[str]] = mapped_column(String(20))
    placed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    filled_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    user = relationship("User", back_populates="orders")
    trade = relationship("Trade", back_populates="orders")
