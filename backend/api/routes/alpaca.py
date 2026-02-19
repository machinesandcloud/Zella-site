"""Alpaca API routes."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.routes.auth import get_current_user
from config.settings import settings
from models import User
from core.alpaca_client import AlpacaClient

router = APIRouter(prefix="/api/alpaca", tags=["alpaca"])
logger = logging.getLogger("alpaca")


def get_alpaca_client() -> Optional[AlpacaClient]:
    """Get Alpaca client from app state."""
    from main import app
    return getattr(app.state, "alpaca_client", None)


class AlpacaConnectRequest(BaseModel):
    api_key: Optional[str] = None
    secret_key: Optional[str] = None
    paper: Optional[bool] = True


@router.post("/connect")
def connect_alpaca(
    body: AlpacaConnectRequest,
    alpaca: Optional[AlpacaClient] = Depends(get_alpaca_client),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Connect to Alpaca API."""
    if not alpaca:
        raise HTTPException(status_code=400, detail="Alpaca not enabled. Set USE_ALPACA=true in env vars.")

    if not alpaca.is_connected():
        connected = alpaca.connect()
        if not connected:
            raise HTTPException(status_code=500, detail="Failed to connect to Alpaca API. Check your API keys.")

    logger.info(f"Alpaca connected - user={current_user.username}, mode={alpaca.get_trading_mode()}")
    return {"status": "connected", "mode": alpaca.get_trading_mode()}


@router.post("/disconnect")
def disconnect_alpaca(
    alpaca: Optional[AlpacaClient] = Depends(get_alpaca_client),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Disconnect from Alpaca API."""
    if not alpaca:
        raise HTTPException(status_code=400, detail="Alpaca not enabled")

    alpaca.disconnect()
    logger.info(f"Alpaca disconnected - user={current_user.username}")
    return {"status": "disconnected"}


@router.get("/status")
def status(
    alpaca: Optional[AlpacaClient] = Depends(get_alpaca_client),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get Alpaca connection status."""
    if not alpaca:
        return {"enabled": False}

    return {
        "enabled": True,
        "connected": alpaca.is_connected(),
        "mode": alpaca.get_trading_mode()
    }


@router.get("/account")
def get_account(
    alpaca: Optional[AlpacaClient] = Depends(get_alpaca_client),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get account summary."""
    if not alpaca or not alpaca.is_connected():
        raise HTTPException(status_code=400, detail="Alpaca not connected")

    return alpaca.get_account_summary()


@router.get("/positions")
def get_positions(
    alpaca: Optional[AlpacaClient] = Depends(get_alpaca_client),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get all positions."""
    if not alpaca or not alpaca.is_connected():
        raise HTTPException(status_code=400, detail="Alpaca not connected")

    return {"positions": alpaca.get_positions()}


@router.get("/orders")
def get_orders(
    status: Optional[str] = None,
    alpaca: Optional[AlpacaClient] = Depends(get_alpaca_client),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get orders (optionally filter by status: open, closed, all)."""
    if not alpaca or not alpaca.is_connected():
        raise HTTPException(status_code=400, detail="Alpaca not connected")

    return {"orders": alpaca.get_orders(status=status)}


class PlaceOrderRequest(BaseModel):
    symbol: str
    quantity: int
    side: str  # "BUY" or "SELL"
    order_type: str = "MARKET"  # "MARKET" or "LIMIT"
    limit_price: Optional[float] = None


@router.post("/order")
def place_order(
    order: PlaceOrderRequest,
    alpaca: Optional[AlpacaClient] = Depends(get_alpaca_client),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Place an order."""
    if not alpaca or not alpaca.is_connected():
        raise HTTPException(status_code=400, detail="Alpaca not connected")

    try:
        if order.order_type.upper() == "MARKET":
            result = alpaca.place_market_order(
                symbol=order.symbol,
                quantity=order.quantity,
                side=order.side
            )
        elif order.order_type.upper() == "LIMIT":
            if not order.limit_price:
                raise HTTPException(status_code=400, detail="limit_price required for LIMIT orders")
            result = alpaca.place_limit_order(
                symbol=order.symbol,
                quantity=order.quantity,
                side=order.side,
                limit_price=order.limit_price
            )
        else:
            raise HTTPException(status_code=400, detail=f"Invalid order_type: {order.order_type}")

        logger.info(f"Order placed - user={current_user.username}, order={result}")
        return result
    except Exception as e:
        logger.error(f"Error placing order: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/order/{order_id}")
def cancel_order(
    order_id: str,
    alpaca: Optional[AlpacaClient] = Depends(get_alpaca_client),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Cancel an order by ID."""
    if not alpaca or not alpaca.is_connected():
        raise HTTPException(status_code=400, detail="Alpaca not connected")

    success = alpaca.cancel_order(order_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to cancel order")

    logger.info(f"Order cancelled - user={current_user.username}, order_id={order_id}")
    return {"status": "cancelled", "orderId": order_id}


@router.get("/quote/{symbol}")
def get_quote(
    symbol: str,
    alpaca: Optional[AlpacaClient] = Depends(get_alpaca_client),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get latest quote for a symbol."""
    if not alpaca or not alpaca.is_connected():
        raise HTTPException(status_code=400, detail="Alpaca not connected")

    quote = alpaca.get_quote(symbol)
    if not quote:
        raise HTTPException(status_code=404, detail=f"Quote not found for {symbol}")

    return quote


@router.get("/bars/{symbol}")
def get_bars(
    symbol: str,
    timeframe: str = "1Min",
    limit: int = 100,
    alpaca: Optional[AlpacaClient] = Depends(get_alpaca_client),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get historical bars for a symbol."""
    if not alpaca or not alpaca.is_connected():
        raise HTTPException(status_code=400, detail="Alpaca not connected")

    bars = alpaca.get_bars(symbol, timeframe=timeframe, limit=limit)
    return {"symbol": symbol, "timeframe": timeframe, "bars": bars}
