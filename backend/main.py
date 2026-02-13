from fastapi import FastAPI

from api.routes import account, auth, dashboard, ibkr, settings, strategies, trading, ai_trading, qa, alerts, risk
from api.websocket.market_data import router as ws_router
from config import settings as app_settings
from core import (
    AlertManager,
    IBKRClient,
    PositionManager,
    PreTradeRiskValidator,
    RiskConfig,
    RiskManager,
    StrategyEngine,
)
from core.auto_trader import AutoTrader
from core.mock_ibkr_client import MockIBKRClient
from core.ibkr_client import ibkr_api_available
from market.ibkr_provider import IBKRMarketDataProvider
from market.universe import get_default_universe
from core.init_db import init_db
from utils.logger import setup_logging

app = FastAPI(title="Zella AI Trading API", version="0.1.0")


@app.on_event("startup")
def on_startup() -> None:
    setup_logging()
    init_db()

    if app_settings.use_mock_ibkr or not ibkr_api_available():
        app.state.ibkr_client = MockIBKRClient()
    else:
        app.state.ibkr_client = IBKRClient()
    app.state.risk_manager = RiskManager(
        RiskConfig(
            max_position_size_percent=app_settings.max_position_size_percent,
            max_daily_loss=app_settings.max_daily_loss,
            max_positions=app_settings.max_concurrent_positions,
            risk_per_trade_percent=app_settings.max_risk_per_trade,
        )
    )
    app.state.alert_manager = AlertManager()
    app.state.risk_validator = PreTradeRiskValidator(
        max_position_size_percent=app_settings.max_position_size_percent,
        max_daily_loss=app_settings.max_daily_loss,
        max_positions=app_settings.max_concurrent_positions,
    )
    app.state.position_manager = PositionManager()
    app.state.strategy_engine = StrategyEngine(
        app.state.ibkr_client, app.state.risk_manager, app.state.position_manager
    )
    app.state.strategy_configs = {}
    app.state.market_data_provider = IBKRMarketDataProvider(
        app.state.ibkr_client, universe=get_default_universe()
    )
    app.state.auto_trader = AutoTrader(
        app.state.market_data_provider,
        app.state.strategy_engine,
        screener_config={
            "min_avg_volume": app_settings.screener_min_avg_volume,
            "min_price": app_settings.screener_min_price,
            "max_price": app_settings.screener_max_price,
            "min_volatility": app_settings.screener_min_volatility,
        },
    )


@app.on_event("shutdown")
def on_shutdown() -> None:
    if hasattr(app.state, "ibkr_client") and app.state.ibkr_client.is_connected():
        app.state.ibkr_client.disconnect()


app.include_router(auth.router)
app.include_router(ibkr.router)
app.include_router(account.router)
app.include_router(trading.router)
app.include_router(strategies.router)
app.include_router(dashboard.router)
app.include_router(settings.router)
app.include_router(ai_trading.router)
app.include_router(qa.router)
app.include_router(alerts.router)
app.include_router(risk.router)
app.include_router(ws_router)


@app.get("/")
def root() -> dict:
    return {"name": "Zella AI Trading", "status": "ok"}
