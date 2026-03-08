from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session

from core.db import get_db
from core.alpaca_client import AlpacaClient
from core.risk_manager import RiskManager
from core.risk_validator import PreTradeRiskValidator
from models import Order, User
from api.routes.auth import get_current_user
from utils.validators import validate_price, validate_quantity, validate_symbol

router = APIRouter(prefix="/api/trading", tags=["trading"])
logger = logging.getLogger("trading")


class OrderRequest(BaseModel):
    symbol: str
    action: str
    quantity: int
    order_type: str
    asset_type: str = "STK"
    exchange: str = "SMART"
    currency: str = "USD"
    expiry: Optional[str] = None
    strike: Optional[float] = None
    right: Optional[str] = None
    multiplier: Optional[str] = None
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None


class OrderOut(BaseModel):
    id: int
    symbol: str
    asset_type: Optional[str] = None
    order_type: str
    action: str
    quantity: int
    filled_quantity: Optional[int] = None
    avg_fill_price: Optional[float] = None
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    placed_at: Optional[datetime] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True


class ClosePositionRequest(BaseModel):
    symbol: str


def get_alpaca_client() -> AlpacaClient | None:
    from main import app
    return getattr(app.state, "alpaca_client", None)


def get_risk_manager() -> RiskManager:
    from main import app

    return app.state.risk_manager


def get_risk_validator() -> PreTradeRiskValidator:
    from main import app

    return app.state.risk_validator


def get_alert_manager():
    from main import app

    return app.state.alert_manager


@router.post("/order", response_model=OrderOut)
def place_order(
    order_in: OrderRequest,
    db: Session = Depends(get_db),
    alpaca: AlpacaClient | None = Depends(get_alpaca_client),
    risk_manager: RiskManager = Depends(get_risk_manager),
    risk_validator: PreTradeRiskValidator = Depends(get_risk_validator),
    current_user: User = Depends(get_current_user),
) -> Order:
    symbol = validate_symbol(order_in.symbol.upper())
    quantity = validate_quantity(order_in.quantity)
    action = order_in.action.upper()
    order_type = order_in.order_type.upper()

    if order_type == "LMT" and order_in.limit_price is not None:
        validate_price(order_in.limit_price)
    if order_type == "STP" and order_in.stop_price is not None:
        validate_price(order_in.stop_price)

    if not alpaca or not alpaca.is_connected():
        raise HTTPException(status_code=503, detail="Alpaca not connected")

    account_summary = alpaca.get_account_summary()
    account_value = float(account_summary.get("NetLiquidation", 0) or 0)
    buying_power = float(account_summary.get("BuyingPower", 0) or 0)
    price_for_risk = order_in.limit_price or order_in.stop_price or 0

    if not risk_manager.check_daily_loss_limit():
        raise HTTPException(status_code=403, detail="Daily loss limit exceeded")
    if not risk_manager.check_max_positions():
        raise HTTPException(status_code=403, detail="Max positions reached")
    if price_for_risk and not risk_manager.check_position_size_limit(
        symbol, quantity, price_for_risk, account_value
    ):
        raise HTTPException(status_code=403, detail="Position size limit exceeded")
    if price_for_risk and not risk_manager.check_buying_power(quantity * price_for_risk, buying_power):
        raise HTTPException(status_code=403, detail="Insufficient buying power")

    open_positions = len(alpaca.get_positions())
    risk_validation = risk_validator.validate(
        symbol=symbol,
        quantity=quantity,
        price=price_for_risk or 0,
        account_value=account_value,
        daily_pnl=float(account_summary.get("RealizedPnL", 0) or 0),
        open_positions=open_positions,
        buying_power=buying_power,
        spread_percent=None,
    )
    if not risk_validation.approved:
        get_alert_manager().create(
            "CRITICAL",
            f"Order rejected: {risk_validation.reason}",
            {"symbol": symbol, "user": current_user.username},
        )
        raise HTTPException(status_code=403, detail=risk_validation.reason or "Risk validation failed")
    for warning in risk_validation.warnings:
        get_alert_manager().create(
            "WARNING",
            warning,
            {"symbol": symbol, "user": current_user.username},
        )

    order_id = None
    broker_order_id = None
    try:
        if order_type == "MKT":
            order_id = alpaca.place_market_order(symbol, quantity, action)
        elif order_type == "LMT" and order_in.limit_price is not None:
            order_id = alpaca.place_limit_order(symbol, quantity, action, order_in.limit_price)
        elif order_type == "STP" and order_in.stop_price is not None:
            order_id = alpaca.place_stop_order(symbol, quantity, action, order_in.stop_price)
        elif order_type == "BRACKET" and order_in.take_profit and order_in.stop_loss:
            order_id = alpaca.place_bracket_order(
                symbol,
                quantity,
                action,
                order_in.take_profit,
                order_in.stop_loss,
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid order parameters")
        if isinstance(order_id, dict):
            broker_order_id = order_id.get("orderId")
        elif order_id is not None:
            broker_order_id = str(order_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Broker error placing order for {symbol}: {e}")
        raise HTTPException(status_code=503, detail=f"Broker error: {str(e)}")

    logger.info(
        "order_submitted symbol=%s action=%s qty=%s type=%s order_id=%s user=%s",
        symbol,
        action,
        quantity,
        order_type,
        broker_order_id,
        current_user.username,
    )

    order = Order(
        user_id=current_user.id,
        ibkr_order_id=broker_order_id,
        symbol=symbol,
        asset_type=order_in.asset_type,
        exchange=order_in.exchange,
        currency=order_in.currency,
        expiry=order_in.expiry,
        strike=order_in.strike,
        right=order_in.right,
        multiplier=order_in.multiplier,
        order_type=order_type,
        action=action,
        quantity=quantity,
        limit_price=order_in.limit_price,
        stop_price=order_in.stop_price,
        status="SUBMITTED",
    )
    try:
        db.add(order)
        db.commit()
        db.refresh(order)
    except Exception as e:
        db.rollback()
        logger.error(f"Database error saving order for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save order to database")
    return order


@router.delete("/order/{order_id}")
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    alpaca: AlpacaClient | None = Depends(get_alpaca_client),
    current_user: User = Depends(get_current_user),
) -> dict:
    if not alpaca or not alpaca.is_connected():
        raise HTTPException(status_code=503, detail="Alpaca not connected")
    order = (
        db.query(Order)
        .filter(Order.user_id == current_user.id, Order.id == order_id)
        .first()
    )
    if not order or not order.ibkr_order_id:
        raise HTTPException(status_code=404, detail="Order not found or missing broker order id")
    alpaca.cancel_order(str(order.ibkr_order_id))
    try:
        order.status = "CANCELLED"
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"Failed to update order status in database: {e}")
    return {"status": "cancelled", "order_id": order_id}


@router.put("/order/{order_id}")
def modify_order(
    order_id: int,
    new_params: OrderRequest,
    db: Session = Depends(get_db),
    alpaca: AlpacaClient | None = Depends(get_alpaca_client),
    current_user: User = Depends(get_current_user),
) -> dict:
    raise HTTPException(status_code=400, detail="Modify not supported for Alpaca orders (cancel & re-place)")


@router.get("/orders", response_model=List[OrderOut])
def list_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Order]:
    return (
        db.query(Order)
        .filter(Order.user_id == current_user.id)
        .order_by(Order.placed_at.desc())
        .all()
    )


@router.get("/orders/open")
def open_orders(
    alpaca: AlpacaClient | None = Depends(get_alpaca_client),
    current_user: User = Depends(get_current_user),
) -> dict:
    if not alpaca or not alpaca.is_connected():
        raise HTTPException(status_code=503, detail="Alpaca not connected")
    return {"orders": alpaca.get_orders(status="open")}


@router.post("/positions/close")
def close_position(
    body: ClosePositionRequest,
    alpaca: AlpacaClient | None = Depends(get_alpaca_client),
    current_user: User = Depends(get_current_user),
) -> dict:
    symbol = validate_symbol(body.symbol.upper())
    if not alpaca or not alpaca.is_connected():
        raise HTTPException(status_code=503, detail="Alpaca not connected")
    alpaca.close_position(symbol)
    logger.info("position_close_requested symbol=%s user=%s", symbol, current_user.username)
    return {"status": "closing", "symbol": symbol}


@router.post("/kill-switch")
def kill_switch(
    alpaca: AlpacaClient | None = Depends(get_alpaca_client),
    risk_manager: RiskManager = Depends(get_risk_manager),
    current_user: User = Depends(get_current_user),
) -> dict:
    risk_manager.trigger_emergency_stop()
    if alpaca and alpaca.is_connected():
        alpaca.cancel_all_orders()
    logger.critical("kill_switch_triggered user=%s", current_user.username)
    return {"status": "triggered"}
