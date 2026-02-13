import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.routes.auth import get_current_user
from config import settings
from models import User
from core.ibkr_client import IBKRClient
from core.ibkr_webapi import IBKRWebAPIClient

router = APIRouter(prefix="/api/ibkr", tags=["ibkr"])
logger = logging.getLogger("ibkr")


def get_ibkr_client() -> IBKRClient:
    from main import app

    return app.state.ibkr_client


def get_webapi_client() -> IBKRWebAPIClient | None:
    from main import app

    return getattr(app.state, "ibkr_webapi_client", None)


class IBKRConnectRequest(BaseModel):
    host: Optional[str] = None
    port: Optional[int] = None
    client_id: Optional[int] = None
    is_paper_trading: Optional[bool] = True


@router.post("/connect")
def connect_ibkr(
    body: IBKRConnectRequest,
    ibkr: IBKRClient = Depends(get_ibkr_client),
    webapi: IBKRWebAPIClient | None = Depends(get_webapi_client),
    current_user: User = Depends(get_current_user),
) -> dict:
    if settings.use_ibkr_webapi and webapi:
        return {
            "status": "webapi",
            "message": "IBKR Web API is enabled. Authenticate via Client Portal Gateway.",
        }
    host = body.host or settings.ibkr_host
    port = body.port or (settings.ibkr_paper_port if body.is_paper_trading else settings.ibkr_live_port)
    client_id = body.client_id or settings.ibkr_client_id
    connected = ibkr.connect_to_ibkr(host, port, client_id, body.is_paper_trading)
    if hasattr(ibkr, "api_available") and not ibkr.api_available():
        raise HTTPException(status_code=501, detail="IBKR API not installed. Using placeholder client.")
    if not connected:
        raise HTTPException(status_code=500, detail="Failed to connect to IBKR")
    logger.info("ibkr_connected user=%s mode=%s", current_user.username, ibkr.get_trading_mode())
    return {"status": "connected", "mode": ibkr.get_trading_mode()}


@router.post("/disconnect")
def disconnect_ibkr(
    ibkr: IBKRClient = Depends(get_ibkr_client),
    webapi: IBKRWebAPIClient | None = Depends(get_webapi_client),
    current_user: User = Depends(get_current_user),
) -> dict:
    if settings.use_ibkr_webapi and webapi:
        return {"status": "webapi", "message": "Disconnect via Client Portal Gateway UI."}
    ibkr.disconnect()
    logger.info("ibkr_disconnected user=%s", current_user.username)
    return {"status": "disconnected"}


@router.get("/status")
def status(
    ibkr: IBKRClient = Depends(get_ibkr_client),
    webapi: IBKRWebAPIClient | None = Depends(get_webapi_client),
    current_user: User = Depends(get_current_user),
) -> dict:
    if settings.use_ibkr_webapi and webapi:
        return {"connected": webapi.is_connected(), "mode": "WEBAPI"}
    return {"connected": ibkr.is_connected(), "mode": ibkr.get_trading_mode()}


@router.get("/webapi/status")
def webapi_status(
    webapi: IBKRWebAPIClient | None = Depends(get_webapi_client),
    current_user: User = Depends(get_current_user),
) -> dict:
    if not webapi:
        return {"enabled": False}
    return {"enabled": True, "connected": webapi.is_connected(), "base_url": webapi.base_url}


@router.put("/toggle-mode")
def toggle_mode(
    enable_paper: bool,
    confirm_live: bool = False,
    ibkr: IBKRClient = Depends(get_ibkr_client),
    current_user: User = Depends(get_current_user),
) -> dict:
    if not enable_paper and not confirm_live:
        raise HTTPException(status_code=400, detail="Live trading requires confirm_live=true")
    ibkr.set_paper_trading_mode(enable_paper)
    logger.info("ibkr_mode_changed user=%s mode=%s", current_user.username, ibkr.get_trading_mode())
    return {"mode": ibkr.get_trading_mode()}
