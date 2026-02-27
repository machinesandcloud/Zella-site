import time
import asyncio
import logging

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from api.routes import account, auth, backtest, dashboard, ibkr, settings, strategies, trading, ai_trading, qa, alerts, risk, trades, news, market, alpaca
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
from core.ibkr_webapi import IBKRWebAPIClient
from core.alpaca_client import AlpacaClient
from core.ai_activity import ActivityLog
from core.auto_trader import AutoTrader
from core.autonomous_engine import AutonomousEngine
from core.mock_ibkr_client import MockIBKRClient
from core.ibkr_client import ibkr_api_available
from market.ibkr_provider import IBKRMarketDataProvider
from market.free_provider import FreeMarketDataProvider
from market.webapi_provider import IBKRWebAPIProvider
from market.alpaca_provider import AlpacaMarketDataProvider
from market.universe import get_default_universe
from core.init_db import init_db
from utils.logger import setup_logging

app = FastAPI(title="Zella AI Trading API", version="0.1.1")


@app.get("/health")
async def health_check():
    """
    Robust health check endpoint for Render.
    Returns detailed status of all critical components.
    """
    health_status = {
        "status": "healthy",
        "service": "zella-ai-backend",
        "components": {}
    }

    # Check autonomous engine
    if hasattr(app.state, "autonomous_engine") and app.state.autonomous_engine:
        engine = app.state.autonomous_engine
        health_status["components"]["autonomous_engine"] = {
            "running": engine.running,
            "enabled": engine.enabled,
            "mode": engine.mode
        }
        # Include performance engine status
        if hasattr(engine, 'perf_engine'):
            health_status["components"]["performance_engine"] = {
                "cache_hit_rate": round(engine.perf_engine.cache.hit_rate, 3),
                "symbols_tracked": len(engine.perf_engine.symbols),
                "staged_orders": len(engine.perf_engine.order_prestager.get_all_staged()),
                "integration_validated": getattr(engine, '_integration_validated', False)
            }
    else:
        health_status["components"]["autonomous_engine"] = {"status": "not_initialized"}

    # Check broker connection
    broker_status = "disconnected"
    if hasattr(app.state, "alpaca_client") and app.state.alpaca_client:
        if app.state.alpaca_client.is_connected():
            broker_status = "alpaca_connected"
    elif hasattr(app.state, "ibkr_client") and app.state.ibkr_client:
        if app.state.ibkr_client.is_connected():
            broker_status = "ibkr_connected"
        elif hasattr(app.state.ibkr_client, '__class__') and 'Mock' in app.state.ibkr_client.__class__.__name__:
            broker_status = "mock_connected"

    health_status["components"]["broker"] = broker_status

    # Check market data provider
    if hasattr(app.state, "market_data_provider") and app.state.market_data_provider:
        health_status["components"]["market_data"] = "initialized"
    else:
        health_status["components"]["market_data"] = "not_initialized"

    return health_status

allowed_origins = [
    origin.strip()
    for origin in app_settings.cors_allowed_origins.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=app_settings.cors_allow_origin_regex or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REQUEST_COUNT = Counter(
    "zella_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "zella_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
)

logger = logging.getLogger("zella")


async def keep_ibkr_session_alive():
    """Background task to keep IBKR Web API session alive - pings every 30 seconds to prevent Render idle timeout."""
    while True:
        try:
            await asyncio.sleep(30)  # 30 seconds - Render kills idle connections after ~60s
            if hasattr(app.state, "ibkr_webapi_client") and app.state.ibkr_webapi_client:
                result = app.state.ibkr_webapi_client.tickle()
                logger.debug(f"IBKR session tickle: {result}")  # Debug level to reduce log spam
        except Exception as e:
            logger.error(f"Error in IBKR session keepalive: {e}")
            # Don't crash the loop - keep trying
            await asyncio.sleep(5)


async def server_self_ping():
    """
    Background task that keeps the server alive by performing periodic internal health checks.
    This prevents Render from marking the service as idle even when no external requests come in.
    Critical for 24/7 trading bot operation.
    """
    import aiohttp

    while True:
        try:
            await asyncio.sleep(30)  # Ping every 30 seconds

            # Internal health check - lightweight verification the server is responsive
            async with aiohttp.ClientSession() as session:
                # Use environment variable for the server URL, fallback to localhost
                import os
                server_url = os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:10000")
                async with session.get(f"{server_url}/health", timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        logger.debug("Server self-ping successful")
                    else:
                        logger.warning(f"Server self-ping returned status {response.status}")
        except Exception as e:
            logger.debug(f"Server self-ping failed (may be normal during startup): {e}")
            # Don't crash - just continue trying
            await asyncio.sleep(5)


@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start_time
    REQUEST_COUNT.labels(request.method, request.url.path, response.status_code).inc()
    REQUEST_LATENCY.labels(request.method, request.url.path).observe(elapsed)
    return response


@app.on_event("startup")
def on_startup() -> None:
    setup_logging()
    init_db()

    # Validate configuration
    config_warnings = app_settings.validate_configuration()
    if config_warnings:
        logger.warning("Configuration warnings:")
        for warning in config_warnings:
            logger.warning(f"  {warning}")

    if app_settings.use_mock_ibkr or not ibkr_api_available():
        app.state.ibkr_client = MockIBKRClient()
        # Auto-connect mock client so autonomous engine can start
        app.state.ibkr_client.connect_to_ibkr("127.0.0.1", 7497, 1, is_paper_trading=True)
        logger.info("MockIBKRClient auto-connected for paper trading")
    else:
        app.state.ibkr_client = IBKRClient()
    app.state.risk_manager = RiskManager(
        RiskConfig(
            max_position_size_percent=app_settings.max_position_size_percent,
            max_daily_loss=app_settings.max_daily_loss,
            max_positions=app_settings.max_concurrent_positions,
            risk_per_trade_percent=app_settings.max_risk_per_trade,
            max_trades_per_day=app_settings.max_trades_per_day,
            max_consecutive_losses=app_settings.max_consecutive_losses,
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
    app.state.ai_activity = ActivityLog()
    app.state.strategy_configs = {}
    # Initialize Market Data Provider
    # Priority: Alpaca > IBKR WebAPI > Free Data > IBKR
    if app_settings.use_alpaca and app_settings.alpaca_api_key and app_settings.alpaca_secret_key:
        logger.info("Using Alpaca Market Data Provider with day trading universe (90+ stocks)")
        app.state.market_data_provider = AlpacaMarketDataProvider(
            api_key=app_settings.alpaca_api_key,
            secret_key=app_settings.alpaca_secret_key
        )
    elif app_settings.use_ibkr_webapi:
        web_client = IBKRWebAPIClient(
            base_url=app_settings.ibkr_webapi_base_url,
            account_id=app_settings.ibkr_webapi_account_id or None,
            verify_ssl=app_settings.ibkr_webapi_verify_ssl,
        )
        app.state.ibkr_webapi_client = web_client
        app.state.market_data_provider = IBKRWebAPIProvider(web_client)
    elif app_settings.use_free_data or app_settings.use_mock_ibkr:
        logger.info("Using Free Market Data Provider with day trading universe (90+ stocks)")
        app.state.market_data_provider = FreeMarketDataProvider(get_default_universe())
    else:
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
            "min_relative_volume": app_settings.screener_min_relative_volume,
        },
    )

    # Start IBKR session keepalive task if using Web API
    if app_settings.use_ibkr_webapi:
        asyncio.create_task(keep_ibkr_session_alive())
        logger.info("Started IBKR Web API session keepalive task")

    # Initialize Alpaca client if enabled
    logger.info(f"Alpaca initialization: use_alpaca={app_settings.use_alpaca}, effective={app_settings.use_alpaca_effective}")
    logger.info(f"Alpaca keys configured: api_key={bool(app_settings.alpaca_api_key)}, secret={bool(app_settings.alpaca_secret_key)}, paper={app_settings.alpaca_paper}")

    app.state.alpaca_client = None  # Initialize to None by default

    if app_settings.use_alpaca_effective:
        if app_settings.alpaca_api_key and app_settings.alpaca_secret_key:
            try:
                logger.info(f"Creating Alpaca client (paper={app_settings.alpaca_paper})...")
                alpaca_client = AlpacaClient(
                    api_key=app_settings.alpaca_api_key,
                    secret_key=app_settings.alpaca_secret_key,
                    paper=app_settings.alpaca_paper
                )
                # Test connection with timeout
                if alpaca_client.connect():
                    app.state.alpaca_client = alpaca_client
                    logger.info(f"✓ Alpaca connected successfully (paper={app_settings.alpaca_paper})")
                else:
                    # Still set the client even if connection failed - it can retry later
                    app.state.alpaca_client = alpaca_client
                    logger.warning("✗ Alpaca client created but initial connection failed - will retry on API calls")
            except Exception as e:
                logger.error(f"✗ Failed to create Alpaca client: {e}")
                app.state.alpaca_client = None
        else:
            logger.warning(f"✗ Alpaca enabled but API keys missing: api_key={'SET' if app_settings.alpaca_api_key else 'MISSING'}, secret={'SET' if app_settings.alpaca_secret_key else 'MISSING'}")
    else:
        logger.info("Alpaca disabled in configuration")

    # Initialize Autonomous Trading Engine (Alpaca or Mock)
    broker_client = app.state.alpaca_client if app.state.alpaca_client else app.state.ibkr_client

    try:
        logger.info("Initializing Autonomous Trading Engine...")
        app.state.autonomous_engine = AutonomousEngine(
            market_data_provider=app.state.market_data_provider,
            strategy_engine=app.state.strategy_engine,
            risk_manager=app.state.risk_manager,
            position_manager=app.state.position_manager,
            broker_client=broker_client,
            config={
                "enabled": True,  # Auto-enable for real-time scanning
                "mode": "FULL_AUTO",
                "risk_posture": "BALANCED",
                "scan_interval": 30,  # 30s for real-time updates
                "max_positions": 5,
                "enabled_strategies": "ALL"
            }
        )

        # Auto-start the engine for real-time market scanning
        async def start_engine_async():
            await asyncio.sleep(2)  # Wait for full initialization
            if hasattr(app.state, "autonomous_engine") and app.state.autonomous_engine:
                logger.info("🚀 Auto-starting Autonomous Trading Engine...")
                await app.state.autonomous_engine.start()

        asyncio.create_task(start_engine_async())

        if app_settings.use_mock_ibkr or not (app.state.alpaca_client and app.state.alpaca_client.is_connected()):
            logger.info("✓ Autonomous Trading Engine initialized and starting (DEMO MODE - scan only)")
        else:
            logger.info("✓ Autonomous Trading Engine initialized and starting (LIVE MODE)")
    except Exception as e:
        logger.error(f"✗ Failed to initialize Autonomous Engine: {e}")
        app.state.autonomous_engine = None

    # Start server self-ping to prevent Render idle timeout (critical for 24/7 operation)
    asyncio.create_task(server_self_ping())
    logger.info("✓ Started server self-ping keepalive task (30s interval)")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    # Stop autonomous engine if running
    if hasattr(app.state, "autonomous_engine") and app.state.autonomous_engine:
        logger.info("Stopping Autonomous Trading Engine...")
        await app.state.autonomous_engine.stop()

    # Disconnect broker clients
    if hasattr(app.state, "ibkr_client") and app.state.ibkr_client.is_connected():
        app.state.ibkr_client.disconnect()

    if hasattr(app.state, "alpaca_client") and app.state.alpaca_client and app.state.alpaca_client.is_connected():
        app.state.alpaca_client.disconnect()


app.include_router(auth.router)
app.include_router(ibkr.router)
app.include_router(alpaca.router)
app.include_router(account.router)
app.include_router(trading.router)
app.include_router(strategies.router)
app.include_router(dashboard.router)
app.include_router(settings.router)
app.include_router(ai_trading.router)
app.include_router(qa.router)
app.include_router(alerts.router)
app.include_router(risk.router)
app.include_router(backtest.router)
app.include_router(trades.router)
app.include_router(news.router)
app.include_router(market.router)
app.include_router(ws_router)


@app.get("/")
async def root() -> dict:
    """Root endpoint - basic status check."""
    return {"name": "Zella AI Trading", "status": "ok", "health_endpoint": "/health"}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
