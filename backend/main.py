import time
import asyncio
import logging
from datetime import datetime

import numpy as np
import pandas as pd

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from api.routes import account, auth, backtest, dashboard, settings, strategies, trading, ai_trading, qa, alerts, risk, trades, news, market, alpaca
from api.websocket.market_data import router as ws_router
from config import settings as app_settings
from core import (
    AlertManager,
    PositionManager,
    PreTradeRiskValidator,
    RiskConfig,
    RiskManager,
    StrategyEngine,
)
from core.alpaca_client import AlpacaClient
from core.ai_activity import ActivityLog
from core.auto_trader import AutoTrader
from core.autonomous_engine import AutonomousEngine
from market.alpaca_provider import AlpacaMarketDataProvider
from market.universe import get_default_universe
from core.init_db import init_db
from utils.logger import setup_logging

app = FastAPI(title="Zella AI Trading API", version="0.1.1")

def _coerce_json(value):
    """Convert numpy/pandas scalars and containers into JSON-serializable types."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, pd.Timedelta):
        return value.total_seconds()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {key: _coerce_json(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_coerce_json(item) for item in value]
    return value

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

    # Check autonomous engine (keep this fast/lightweight)
    if hasattr(app.state, "autonomous_engine") and app.state.autonomous_engine:
        engine = app.state.autonomous_engine
        health_status["components"]["autonomous_engine"] = {
            "running": engine.running,
            "enabled": engine.enabled,
            "mode": engine.mode,
        }
    else:
        health_status["components"]["autonomous_engine"] = {"status": "not_initialized"}

    # Check broker connection
    broker_status = "disconnected"
    if hasattr(app.state, "alpaca_client") and app.state.alpaca_client:
        if app.state.alpaca_client.is_connected():
            broker_status = "alpaca_connected"
    health_status["components"]["broker"] = broker_status

    # Check market data provider with cache status
    if hasattr(app.state, "market_data_provider") and app.state.market_data_provider:
        provider = app.state.market_data_provider
        if hasattr(provider, "get_cache_status"):
            cache_status = provider.get_cache_status()
            health_status["components"]["market_data"] = {
                "status": "initialized",
                "cache_size": cache_status.get("cache_size", 0),
                "symbols_with_prices": cache_status.get("symbols_with_prices", 0),
                "streaming_active": cache_status.get("streaming_active", False),
                "rate_limited": cache_status.get("rate_limited", False),
            }
        else:
            health_status["components"]["market_data"] = "initialized"
    else:
        health_status["components"]["market_data"] = "not_initialized"

    return _coerce_json(health_status)

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


async def server_self_ping():
    """
    Background task that keeps the server alive by performing periodic internal health checks.
    This prevents Render from marking the service as idle even when no external requests come in.
    Critical for 24/7 trading bot operation.
    """
    import aiohttp
    import os

    # Use Render's URL or hardcoded production URL
    server_url = os.environ.get("RENDER_EXTERNAL_URL", "https://zella-site.onrender.com")
    port = os.environ.get("PORT", "8000")
    local_url = f"http://127.0.0.1:{port}"
    ping_count = 0

    while True:
        try:
            await asyncio.sleep(10)  # Ping every 10 seconds for strong keep-alive
            ping_count += 1

            async with aiohttp.ClientSession() as session:
                async def ping(url: str) -> bool:
                    try:
                        async with session.get(f"{url}/health", timeout=aiohttp.ClientTimeout(total=10)) as response:
                            return response.status == 200
                    except Exception:
                        return False

                ok_external = await ping(server_url)
                ok_local = await ping(local_url)

                if ok_external or ok_local:
                    if ping_count % 6 == 0:
                        logger.info(f"✓ Self-ping #{ping_count} OK - server alive")
                else:
                    logger.warning("Self-ping failed for both external and local health checks")
        except Exception as e:
            logger.warning(f"Self-ping failed: {e} - will retry")
            await asyncio.sleep(5)


async def resilience_watchdog():
    """
    Background watchdog to keep core services running.
    Ensures Alpaca connection, market data provider, and autonomous engine stay alive.
    """
    import asyncio as _asyncio

    while True:
        try:
            await _asyncio.sleep(20)

            # Ensure Alpaca client connection
            if app_settings.alpaca_api_key and app_settings.alpaca_secret_key:
                if not hasattr(app.state, "alpaca_client") or app.state.alpaca_client is None:
                    logger.warning("Alpaca client missing - recreating")
                    app.state.alpaca_client = AlpacaClient(
                        api_key=app_settings.alpaca_api_key,
                        secret_key=app_settings.alpaca_secret_key,
                        paper=app_settings.alpaca_paper,
                        data_feed=app_settings.alpaca_data_feed,
                    )
                if app.state.alpaca_client and not app.state.alpaca_client.is_connected():
                    app.state.alpaca_client.ensure_connected()
                if app.state.alpaca_client and hasattr(app.state.alpaca_client, "start_trade_updates_stream"):
                    try:
                        app.state.alpaca_client.start_trade_updates_stream(
                            lambda update: app.state.autonomous_engine.handle_trade_update(update)
                            if getattr(app.state, "autonomous_engine", None)
                            else None
                        )
                    except Exception:
                        pass

            # Ensure market data provider and cache health
            if app_settings.alpaca_api_key and app_settings.alpaca_secret_key:
                if not hasattr(app.state, "market_data_provider") or app.state.market_data_provider is None:
                    logger.warning("Market data provider missing - recreating")
                    app.state.market_data_provider = AlpacaMarketDataProvider(
                        api_key=app_settings.alpaca_api_key,
                        secret_key=app_settings.alpaca_secret_key,
                        universe=get_default_universe(),
                        data_feed=app_settings.alpaca_data_feed,
                    )
                    # Warm up the new provider
                    app.state.market_data_provider.warm_up(timeout=5.0)
                else:
                    # Check cache health and trigger refresh if needed
                    provider = app.state.market_data_provider
                    if hasattr(provider, "get_cache_status"):
                        status = provider.get_cache_status()
                        symbols_with_prices = status.get("symbols_with_prices", 0)
                        cache_age = status.get("cache_age_seconds")

                        # If cache is empty or very stale (>60s), force refresh
                        if symbols_with_prices < 10 or (cache_age and cache_age > 60):
                            logger.warning(f"Cache unhealthy: {symbols_with_prices} symbols, age={cache_age}s - refreshing")
                            provider.warm_up(timeout=5.0)

            # Ensure auto trader
            if getattr(app.state, "market_data_provider", None) and getattr(app.state, "auto_trader", None) is None:
                app.state.auto_trader = AutoTrader(
                    app.state.market_data_provider,
                    app.state.strategy_engine,
                    screener_config={
                        "min_avg_volume": app_settings.screener_min_avg_volume,
                        "min_avg_volume_low_float": app_settings.screener_min_avg_volume_low_float,
                        "min_avg_volume_mid_float": app_settings.screener_min_avg_volume_mid_float,
                        "min_avg_volume_large_float": app_settings.screener_min_avg_volume_large_float,
                        "min_price": app_settings.screener_min_price,
                        "max_price": app_settings.screener_max_price,
                        "min_volatility": app_settings.screener_min_volatility,
                        "min_relative_volume": app_settings.screener_min_relative_volume,
                        "min_relative_volume_low_float": app_settings.screener_min_relative_volume_low_float,
                        "min_relative_volume_mid_float": app_settings.screener_min_relative_volume_mid_float,
                        "min_relative_volume_large_float": app_settings.screener_min_relative_volume_large_float,
                        "min_premarket_volume": app_settings.screener_min_premarket_volume,
                        "low_float_max": app_settings.screener_low_float_max,
                        "mid_float_max": app_settings.screener_mid_float_max,
                        "in_play_min_rvol": app_settings.screener_in_play_min_rvol,
                        "in_play_gap_percent": app_settings.screener_in_play_gap_percent,
                        "in_play_volume_multiplier": app_settings.screener_in_play_volume_multiplier,
                        "require_premarket_volume": app_settings.screener_require_premarket_volume,
                        "require_daily_trend": app_settings.screener_require_daily_trend,
                    },
                )

            # Ensure autonomous engine
            if getattr(app.state, "market_data_provider", None):
                if not hasattr(app.state, "autonomous_engine") or app.state.autonomous_engine is None:
                    logger.warning("Autonomous engine missing - recreating")
                    app.state.autonomous_engine = AutonomousEngine(
                        market_data_provider=app.state.market_data_provider,
                        strategy_engine=app.state.strategy_engine,
                        risk_manager=app.state.risk_manager,
                        position_manager=app.state.position_manager,
                        broker_client=app.state.alpaca_client,
                        config={
                            "enabled": True,
                            "mode": "FULL_AUTO",
                            "risk_posture": "BALANCED",
                            "scan_interval": 1,
                            "max_positions": 5,
                            "enabled_strategies": "ALL",
                        },
                    )

                engine = app.state.autonomous_engine
                if engine and not engine.running:
                    if not engine.enabled and app_settings.autonomous_auto_resume:
                        engine.enabled = True
                        logger.warning("Autonomous engine auto-resume enabled - setting enabled=True")
                    if engine.enabled:
                        logger.warning("Autonomous engine stopped - restarting")
                        await engine.start()
                elif engine and engine.running:
                    # Restart main loop if scan heartbeat is stale
                    try:
                        heartbeat = getattr(engine, "last_scan_heartbeat", None)
                        threshold = getattr(engine, "scan_watchdog_threshold", 60)
                        if heartbeat:
                            age = (datetime.utcnow() - heartbeat).total_seconds()
                            if age > threshold:
                                logger.warning(f"Scan heartbeat stale ({int(age)}s) - restarting main loop")
                                await engine._restart_task("main_trading_loop", f"watchdog stale {int(age)}s")
                    except Exception as e:
                        logger.warning(f"Scan watchdog check failed: {e}")
        except Exception as e:
            logger.warning(f"Resilience watchdog error: {e}")
            await _asyncio.sleep(5)


@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start_time
    REQUEST_COUNT.labels(request.method, request.url.path, response.status_code).inc()
    REQUEST_LATENCY.labels(request.method, request.url.path).observe(elapsed)
    return response


@app.on_event("startup")
async def on_startup() -> None:
    setup_logging()
    init_db()

    # Validate configuration
    config_warnings = app_settings.validate_configuration()
    if config_warnings:
        logger.warning("Configuration warnings:")
        for warning in config_warnings:
            logger.warning(f"  {warning}")

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
    app.state.ai_activity = ActivityLog()
    app.state.strategy_configs = {}

    # Initialize Alpaca client (Alpaca-only mode)
    logger.info(f"Alpaca initialization: use_alpaca={app_settings.use_alpaca}, effective={app_settings.use_alpaca_effective}")
    logger.info(f"Alpaca keys configured: api_key={bool(app_settings.alpaca_api_key)}, secret={bool(app_settings.alpaca_secret_key)}, paper={app_settings.alpaca_paper}")

    app.state.alpaca_client = None

    if app_settings.alpaca_api_key and app_settings.alpaca_secret_key:
        try:
            logger.info(f"Creating Alpaca client (paper={app_settings.alpaca_paper})...")
            alpaca_client = AlpacaClient(
                api_key=app_settings.alpaca_api_key,
                secret_key=app_settings.alpaca_secret_key,
                paper=app_settings.alpaca_paper,
                data_feed=app_settings.alpaca_data_feed,
            )
            if alpaca_client.connect():
                app.state.alpaca_client = alpaca_client
                logger.info(f"✓ Alpaca connected successfully (paper={app_settings.alpaca_paper})")
            else:
                app.state.alpaca_client = alpaca_client
                logger.warning("✗ Alpaca client created but initial connection failed - will retry on API calls")
        except Exception as e:
            logger.error(f"✗ Failed to create Alpaca client: {e}")
            app.state.alpaca_client = None
    else:
        logger.error("✗ Alpaca API keys missing - configure ALPACA_API_KEY and ALPACA_SECRET_KEY")

    # Initialize Strategy Engine with Alpaca broker (if available)
    app.state.strategy_engine = StrategyEngine(
        app.state.alpaca_client, app.state.risk_manager, app.state.position_manager
    )
    # Initialize Dynamic Universe Manager (auto-updates weekly with most liquid stocks)
    if app_settings.alpaca_api_key and app_settings.alpaca_secret_key:
        from market.dynamic_universe import get_dynamic_universe_manager
        app.state.dynamic_universe_manager = get_dynamic_universe_manager(
            api_key=app_settings.alpaca_api_key,
            secret_key=app_settings.alpaca_secret_key
        )
        logger.info(f"Dynamic Universe Manager initialized: {len(app.state.dynamic_universe_manager.get_universe())} symbols")

    # Initialize Market Data Provider (Alpaca-only)
    if app_settings.alpaca_api_key and app_settings.alpaca_secret_key:
        logger.info("Using Alpaca Market Data Provider (Alpaca-only mode)")
        app.state.market_data_provider = AlpacaMarketDataProvider(
            api_key=app_settings.alpaca_api_key,
            secret_key=app_settings.alpaca_secret_key,
            universe=get_default_universe(),
            data_feed=app_settings.alpaca_data_feed,
        )

        # Warm up the cache BEFORE starting the engine
        logger.info("Warming up market data cache (this ensures data is ready before scanning)...")
        cache_ready = app.state.market_data_provider.warm_up(timeout=10.0)
        if cache_ready:
            status = app.state.market_data_provider.get_cache_status()
            logger.info(f"✓ Cache ready: {status['symbols_with_prices']} symbols with prices")
        else:
            logger.warning("⚠ Cache warm-up timeout - scanning may show 0 symbols initially")
            status = app.state.market_data_provider.get_cache_status()
            logger.warning(f"  Cache status: {status}")
    else:
        logger.error("Alpaca API keys missing - market data provider not initialized")
        app.state.market_data_provider = None

    if app.state.market_data_provider:
        app.state.auto_trader = AutoTrader(
            app.state.market_data_provider,
            app.state.strategy_engine,
            screener_config={
                "min_avg_volume": app_settings.screener_min_avg_volume,
                "min_avg_volume_low_float": app_settings.screener_min_avg_volume_low_float,
                "min_avg_volume_mid_float": app_settings.screener_min_avg_volume_mid_float,
                "min_avg_volume_large_float": app_settings.screener_min_avg_volume_large_float,
                "min_price": app_settings.screener_min_price,
                "max_price": app_settings.screener_max_price,
                "min_volatility": app_settings.screener_min_volatility,
                "min_relative_volume": app_settings.screener_min_relative_volume,
                "min_relative_volume_low_float": app_settings.screener_min_relative_volume_low_float,
                "min_relative_volume_mid_float": app_settings.screener_min_relative_volume_mid_float,
                "min_relative_volume_large_float": app_settings.screener_min_relative_volume_large_float,
                "min_premarket_volume": app_settings.screener_min_premarket_volume,
                "low_float_max": app_settings.screener_low_float_max,
                "mid_float_max": app_settings.screener_mid_float_max,
                "in_play_min_rvol": app_settings.screener_in_play_min_rvol,
                "in_play_gap_percent": app_settings.screener_in_play_gap_percent,
                "in_play_volume_multiplier": app_settings.screener_in_play_volume_multiplier,
                "require_premarket_volume": app_settings.screener_require_premarket_volume,
                "require_daily_trend": app_settings.screener_require_daily_trend,
            },
        )
    else:
        app.state.auto_trader = None

    # Initialize Autonomous Trading Engine (Alpaca-only)
    broker_client = app.state.alpaca_client

    if app.state.market_data_provider:
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
                    "scan_interval": 1,  # 1s for real-time updates
                    "max_positions": 5,
                    "enabled_strategies": "ALL"
                }
            )

            logger.info("🚀 Auto-starting Autonomous Trading Engine...")
            try:
                app.state.engine_start_task = asyncio.create_task(app.state.autonomous_engine.start())
                logger.info("✅ Autonomous Engine start() scheduled - main loop will run in background")
            except Exception as e:
                logger.error(f"❌ Failed to schedule autonomous engine start: {e}")
                import traceback
                traceback.print_exc()

            if not (app.state.alpaca_client and app.state.alpaca_client.is_connected()):
                logger.info("✓ Autonomous Trading Engine initialized and starting (DEMO MODE - scan only)")
            else:
                logger.info("✓ Autonomous Trading Engine initialized and starting (LIVE MODE)")

            # Start Alpaca trade updates stream for execution awareness
            if app.state.alpaca_client and hasattr(app.state.alpaca_client, "start_trade_updates_stream"):
                try:
                    app.state.alpaca_client.start_trade_updates_stream(
                        lambda update: app.state.autonomous_engine.handle_trade_update(update)
                        if app.state.autonomous_engine
                        else None
                    )
                    logger.info("✓ Alpaca trade updates stream started")
                except Exception as e:
                    logger.warning(f"Trade updates stream failed to start: {e}")
        except Exception as e:
            logger.error(f"✗ Failed to initialize Autonomous Engine: {e}")
            app.state.autonomous_engine = None
    else:
        logger.error("Autonomous engine not started: market data provider is missing (check Alpaca keys)")

    # Start server self-ping to prevent Render idle timeout (critical for 24/7 operation)
    app.state.keepalive_task = asyncio.create_task(server_self_ping())
    logger.info("✓ Started server self-ping keepalive task (30s interval)")

    # Start resilience watchdog to auto-heal connections and background services
    app.state.resilience_task = asyncio.create_task(resilience_watchdog())
    logger.info("✓ Started resilience watchdog task (20s interval)")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    if hasattr(app.state, "keepalive_task") and app.state.keepalive_task:
        app.state.keepalive_task.cancel()
    if hasattr(app.state, "resilience_task") and app.state.resilience_task:
        app.state.resilience_task.cancel()
    if hasattr(app.state, "engine_start_task") and app.state.engine_start_task:
        app.state.engine_start_task.cancel()

    # Stop autonomous engine if running
    if hasattr(app.state, "autonomous_engine") and app.state.autonomous_engine:
        logger.info("Stopping Autonomous Trading Engine...")
        await app.state.autonomous_engine.stop()

    # Disconnect broker clients
    # Alpaca has no persistent disconnect requirement here

    if hasattr(app.state, "alpaca_client") and app.state.alpaca_client and app.state.alpaca_client.is_connected():
        app.state.alpaca_client.disconnect()


app.include_router(auth.router)
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


@app.get("/debug/engine")
async def debug_engine() -> dict:
    """Debug endpoint to check engine state (no auth required for debugging)"""
    if not hasattr(app.state, "autonomous_engine") or not app.state.autonomous_engine:
        return {"error": "Engine not initialized", "state": None}

    engine = app.state.autonomous_engine
    return {
        "enabled": engine.enabled,
        "running": engine.running,
        "mode": engine.mode,
        "last_scan": engine.last_scan_time.isoformat() if engine.last_scan_time else None,
        "decisions_count": len(engine.decisions),
        "decisions": engine.decisions[:10],  # Last 10 decisions
        "symbols_scanned": engine.symbols_scanned,
        "broker_connected": engine.broker.is_connected() if engine.broker else False,
    }
