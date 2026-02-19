"""Alpaca API routes."""

import logging
import os
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

def ensure_alpaca_client() -> Optional[AlpacaClient]:
    """Create and attach an Alpaca client if enabled and missing."""
    from main import app

    if not settings.use_alpaca_effective:
        return None

    existing = getattr(app.state, "alpaca_client", None)
    if existing:
        return existing

    if not (settings.alpaca_api_key and settings.alpaca_secret_key):
        return None

    try:
        logger.info("Creating Alpaca client on-demand in status check...")
        client = AlpacaClient(
            api_key=settings.alpaca_api_key,
            secret_key=settings.alpaca_secret_key,
            paper=settings.alpaca_paper
        )
        # Try a light connect; if it fails, still store client for retry later.
        if client.connect():
            logger.info("✓ Alpaca connected successfully (on-demand)")
        else:
            logger.warning("✗ Alpaca client created but connection failed (on-demand)")
        app.state.alpaca_client = client
        return client
    except Exception as e:
        logger.error(f"Failed to create Alpaca client on-demand: {e}")
        return None


class AlpacaConnectRequest(BaseModel):
    api_key: Optional[str] = None
    secret_key: Optional[str] = None
    paper: Optional[bool] = True


@router.post("/connect")
def connect_alpaca(
    body: AlpacaConnectRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Connect to Alpaca API with new credentials or reconnect existing client.

    If api_key and secret_key are provided, creates a new client with those credentials.
    Otherwise, reconnects the existing client from app state.
    """
    from main import app

    # Validate inputs if new credentials provided
    if body.api_key and body.secret_key:
        # Validate API key format
        if len(body.api_key) < 10:
            raise HTTPException(status_code=400, detail="Invalid API key format")
        if len(body.secret_key) < 10:
            raise HTTPException(status_code=400, detail="Invalid secret key format")

        try:
            # Create new client with provided credentials
            logger.info(f"Creating new Alpaca client for user={current_user.username}, paper={body.paper}")
            new_client = AlpacaClient(
                api_key=body.api_key,
                secret_key=body.secret_key,
                paper=body.paper if body.paper is not None else True
            )

            # Test connection
            if not new_client.connect():
                raise HTTPException(
                    status_code=401,
                    detail="Failed to authenticate with Alpaca. Check your API keys and make sure they're valid."
                )

            # Success - replace app state client
            app.state.alpaca_client = new_client
            logger.info(f"✓ New Alpaca client connected - user={current_user.username}, mode={new_client.get_trading_mode()}")
            return {"status": "connected", "mode": new_client.get_trading_mode(), "new_credentials": True}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating Alpaca client: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create Alpaca client: {str(e)}")

    # No new credentials - reconnect existing client
    else:
        alpaca = getattr(app.state, "alpaca_client", None)
        if not alpaca:
            raise HTTPException(
                status_code=400,
                detail="Alpaca not configured. Provide api_key and secret_key to set up Alpaca."
            )

        if not alpaca.is_connected():
            connected = alpaca.connect()
            if not connected:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to reconnect to Alpaca API. Try providing fresh API credentials."
                )

        logger.info(f"Alpaca reconnected - user={current_user.username}, mode={alpaca.get_trading_mode()}")
        return {"status": "connected", "mode": alpaca.get_trading_mode(), "new_credentials": False}


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
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get Alpaca connection status with detailed diagnostics.

    Returns connection state, configuration info, and helpful error messages.
    """
    from main import app
    from config.settings import settings

    alpaca = getattr(app.state, "alpaca_client", None)
    if not alpaca:
        alpaca = ensure_alpaca_client()

    # Alpaca not configured at all
    if not settings.use_alpaca_effective:
        return {
            "enabled": False,
            "connected": False,
            "reason": "Alpaca not enabled in configuration",
            "help": "Set ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables, or set USE_ALPACA=true"
        }

    # Alpaca client not initialized
    if not alpaca:
        has_keys = bool(settings.alpaca_api_key and settings.alpaca_secret_key)
        return {
            "enabled": True,
            "connected": False,
            "reason": "Alpaca client not initialized" if has_keys else "API keys not configured",
            "help": "Check server logs for initialization errors" if has_keys else "Configure ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables"
        }

    # Alpaca client exists - check connection
    connected = alpaca.is_connected()
    result = {
        "enabled": True,
        "connected": connected,
        "mode": alpaca.get_trading_mode(),
        "paper_trading": alpaca.paper,
        "render_commit": os.getenv("RENDER_GIT_COMMIT", ""),
        "render_service": os.getenv("RENDER_SERVICE_ID", "")
    }

    if not connected:
        result["reason"] = "Not connected to Alpaca"
        result["help"] = "Click 'Connect' to establish connection, or check API keys if connection fails"

    return result


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
