import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.routes.auth import get_current_user
from core.risk_manager import RiskManager
from models import User
from config import settings as app_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])
logger = logging.getLogger("settings")


def get_risk_manager() -> RiskManager:
    from main import app

    return app.state.risk_manager


class RiskSettings(BaseModel):
    max_position_size_percent: float
    max_daily_loss: float
    max_concurrent_positions: int
    risk_per_trade_percent: float


class IBKRDefaults(BaseModel):
    host: str
    port: int
    client_id: int
    is_paper_trading: bool
    use_mock_ibkr: bool
    use_ibkr_webapi: bool
    use_free_data: bool
    use_alpaca: bool


@router.get("/risk", response_model=RiskSettings)
def get_risk_settings(
    risk_manager: RiskManager = Depends(get_risk_manager),
    current_user: User = Depends(get_current_user),
) -> RiskSettings:
    config = risk_manager.config
    return RiskSettings(
        max_position_size_percent=config.max_position_size_percent,
        max_daily_loss=config.max_daily_loss,
        max_concurrent_positions=config.max_positions,
        risk_per_trade_percent=config.risk_per_trade_percent,
    )


@router.put("/risk", response_model=RiskSettings)
def update_risk_settings(
    body: RiskSettings,
    risk_manager: RiskManager = Depends(get_risk_manager),
    current_user: User = Depends(get_current_user),
) -> RiskSettings:
    risk_manager.set_max_position_size(body.max_position_size_percent)
    risk_manager.set_max_daily_loss(body.max_daily_loss)
    risk_manager.set_max_positions(body.max_concurrent_positions)
    risk_manager.set_risk_per_trade(body.risk_per_trade_percent)
    logger.info("risk_settings_updated user=%s values=%s", current_user.username, body.model_dump())
    return body


@router.get("/ibkr-defaults", response_model=IBKRDefaults)
def get_ibkr_defaults(
    current_user: User = Depends(get_current_user),
) -> IBKRDefaults:
    is_paper = app_settings.default_trading_mode.upper() != "LIVE"
    return IBKRDefaults(
        host=app_settings.ibkr_host,
        port=app_settings.ibkr_paper_port if is_paper else app_settings.ibkr_live_port,
        client_id=app_settings.ibkr_client_id,
        is_paper_trading=is_paper,
        use_mock_ibkr=app_settings.use_mock_ibkr,
        use_ibkr_webapi=app_settings.use_ibkr_webapi,
        use_free_data=app_settings.use_free_data,
        use_alpaca=app_settings.use_alpaca,
    )
