import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.db import get_db
from core.ibkr_client import IBKRClient
from core.risk_manager import RiskManager
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
    status: Optional[str] = None

    class Config:
        from_attributes = True


def get_ibkr_client() -> IBKRClient:
    from main import app

    return app.state.ibkr_client


def get_risk_manager() -> RiskManager:
    from main import app

    return app.state.risk_manager


@router.post("/order", response_model=OrderOut)
def place_order(
    order_in: OrderRequest,
    db: Session = Depends(get_db),
    ibkr: IBKRClient = Depends(get_ibkr_client),
    risk_manager: RiskManager = Depends(get_risk_manager),
    current_user: User = Depends(get_current_user),
) -> Order:
    symbol = validate_symbol(order_in.symbol.upper())
    quantity = validate_quantity(order_in.quantity)
    action = order_in.action.upper()
    order_type = order_in.order_type.upper()
    contract_params = {
        "sec_type": order_in.asset_type.upper(),
        "exchange": order_in.exchange,
        "currency": order_in.currency,
        "expiry": order_in.expiry,
        "strike": order_in.strike,
        "right": order_in.right,
        "multiplier": order_in.multiplier,
    }

    if order_type == "LMT" and order_in.limit_price is not None:
        validate_price(order_in.limit_price)
    if order_type == "STP" and order_in.stop_price is not None:
        validate_price(order_in.stop_price)

    if not ibkr.is_connected():
        raise HTTPException(status_code=503, detail="IBKR not connected")

    account_summary = ibkr.get_account_summary()
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

    order_id = None
    if order_type == "MKT":
        order_id = ibkr.place_market_order(symbol, quantity, action, contract_params)
    elif order_type == "LMT" and order_in.limit_price is not None:
        order_id = ibkr.place_limit_order(symbol, quantity, action, order_in.limit_price, contract_params)
    elif order_type == "STP" and order_in.stop_price is not None:
        order_id = ibkr.place_stop_order(symbol, quantity, action, order_in.stop_price, contract_params)
    elif order_type == "BRACKET" and order_in.take_profit and order_in.stop_loss:
        ibkr.place_bracket_order(
            symbol,
            quantity,
            action,
            order_in.take_profit,
            order_in.stop_loss,
            contract_params,
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid order parameters")

    logger.info(
        "order_submitted symbol=%s action=%s qty=%s type=%s order_id=%s user=%s",
        symbol,
        action,
        quantity,
        order_type,
        order_id,
        current_user.username,
    )

    order = Order(
        user_id=current_user.id,
        ibkr_order_id=order_id,
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
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.delete("/order/{order_id}")
def cancel_order(
    order_id: int,
    ibkr: IBKRClient = Depends(get_ibkr_client),
    current_user: User = Depends(get_current_user),
) -> dict:
    if not ibkr.is_connected():
        raise HTTPException(status_code=503, detail="IBKR not connected")
    ibkr.cancel_order(order_id)
    return {"status": "cancelled", "order_id": order_id}


@router.put("/order/{order_id}")
def modify_order(
    order_id: int,
    new_params: OrderRequest,
    ibkr: IBKRClient = Depends(get_ibkr_client),
    current_user: User = Depends(get_current_user),
) -> dict:
    if not ibkr.is_connected():
        raise HTTPException(status_code=503, detail="IBKR not connected")
    ibkr.modify_order(order_id, new_params.model_dump())
    return {"status": "modified", "order_id": order_id}


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
    ibkr: IBKRClient = Depends(get_ibkr_client),
    current_user: User = Depends(get_current_user),
) -> dict:
    return ibkr.get_open_orders()


@router.post("/kill-switch")
def kill_switch(
    ibkr: IBKRClient = Depends(get_ibkr_client),
    risk_manager: RiskManager = Depends(get_risk_manager),
    current_user: User = Depends(get_current_user),
) -> dict:
    risk_manager.trigger_emergency_stop()
    if ibkr.is_connected():
        ibkr.kill_switch()
    logger.critical("kill_switch_triggered user=%s", current_user.username)
    return {"status": "triggered"}
