from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from core.auto_trader import AutoTrader
from core.autonomous_engine import AutonomousEngine
from api.routes.auth import get_current_user
from core.risk_manager import RiskManager
from core.ibkr_client import IBKRClient
from utils.market_hours import market_session
from models import User

router = APIRouter(prefix="/api/ai", tags=["ai"])


class WatchlistRequest(BaseModel):
    symbols: List[str]


def get_market_data_provider():
    from main import app
    return getattr(app.state, "market_data_provider", None)


def get_auto_trader() -> AutoTrader:
    from main import app

    return app.state.auto_trader


def get_autonomous_engine() -> Optional[AutonomousEngine]:
    from main import app

    return getattr(app.state, "autonomous_engine", None)


def get_ibkr_client() -> IBKRClient:
    from main import app

    return app.state.ibkr_client


def get_risk_manager() -> RiskManager:
    from main import app

    return app.state.risk_manager


def get_activity_log():
    from main import app

    return app.state.ai_activity


@router.get("/scan")
def scan_market(
    auto_trader: AutoTrader = Depends(get_auto_trader),
    current_user: User = Depends(get_current_user),
) -> dict:
    return {"ranked": auto_trader.scan_market()}


@router.get("/top")
def top_picks(
    limit: int = 5,
    auto_trader: AutoTrader = Depends(get_auto_trader),
    current_user: User = Depends(get_current_user),
) -> dict:
    return {"ranked": auto_trader.select_top(limit)}


@router.post("/auto-trade")
def auto_trade(
    limit: int = 5,
    execute: bool = False,
    confirm_execute: bool = False,
    auto_trader: AutoTrader = Depends(get_auto_trader),
    ibkr: IBKRClient = Depends(get_ibkr_client),
    risk_manager: RiskManager = Depends(get_risk_manager),
    activity_log=Depends(get_activity_log),
    current_user: User = Depends(get_current_user),
) -> dict:
    picks = auto_trader.select_top(limit)
    executed = []

    if execute:
        activity_log.update_status(state="RUNNING", last_scan="auto_trade")
        activity_log.add("SCAN", "Auto-trade scan started", "INFO", {"limit": str(limit)})
        if not confirm_execute:
            raise HTTPException(status_code=400, detail="confirm_execute=true required")
        if ibkr.get_trading_mode() != "PAPER":
            raise HTTPException(status_code=403, detail="Auto-trade only allowed in PAPER mode")
        if not ibkr.is_connected():
            raise HTTPException(status_code=503, detail="IBKR not connected")
        if not risk_manager.can_trade():
            raise HTTPException(status_code=403, detail="Trading halted by risk controls")
        if not market_session().get("regular"):
            raise HTTPException(status_code=403, detail="Auto-trade only during regular market hours")

        account_summary = ibkr.get_account_summary()
        account_value = float(account_summary.get("NetLiquidation", 0) or 0)
        buying_power = float(account_summary.get("BuyingPower", 0) or 0)

        for pick in picks:
            symbol = pick.get("symbol")
            last_price = float(pick.get("last_price", 0))
            if not symbol or last_price <= 0:
                continue
            if risk_manager.trades_today >= risk_manager.config.max_trades_per_day:
                break
            stop_distance = last_price * 0.01
            quantity = risk_manager.calculate_position_size(
                symbol, risk_manager.config.risk_per_trade_percent, stop_distance, account_value
            )
            if not risk_manager.check_position_size_limit(symbol, quantity, last_price, account_value):
                continue
            if not risk_manager.check_buying_power(quantity * last_price, buying_power):
                continue
            order_id = ibkr.place_market_order(symbol, quantity, "BUY")
            executed.append({"symbol": symbol, "quantity": quantity, "order_id": order_id})
            risk_manager.trades_today += 1
            activity_log.add(
                "ORDER",
                f"Auto-trade order submitted for {symbol}",
                "INFO",
                {"order_id": str(order_id), "quantity": str(quantity)},
            )

        activity_log.update_status(last_order=str(executed[-1]["order_id"]) if executed else None)

    return {"ranked": picks, "executed": executed}


@router.get("/activity")
def activity_feed(
    activity_log=Depends(get_activity_log),
    current_user: User = Depends(get_current_user),
) -> dict:
    return activity_log.snapshot()


@router.get("/status")
def ai_status(
    activity_log=Depends(get_activity_log),
    current_user: User = Depends(get_current_user),
) -> dict:
    return {"status": activity_log.status}


# ==================== Autonomous Engine Endpoints ====================

@router.post("/autonomous/start")
async def start_autonomous_engine(
    engine: Optional[AutonomousEngine] = Depends(get_autonomous_engine),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Start the fully autonomous trading engine"""
    if not engine:
        raise HTTPException(status_code=503, detail="Autonomous engine not initialized")

    await engine.start()
    return {"status": "started", "message": "Autonomous trading engine started"}


@router.post("/autonomous/stop")
async def stop_autonomous_engine(
    engine: Optional[AutonomousEngine] = Depends(get_autonomous_engine),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Stop the autonomous trading engine"""
    if not engine:
        raise HTTPException(status_code=503, detail="Autonomous engine not initialized")

    await engine.stop()
    return {"status": "stopped", "message": "Autonomous trading engine stopped"}


@router.get("/autonomous/status")
def get_autonomous_status(
    engine: Optional[AutonomousEngine] = Depends(get_autonomous_engine),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get autonomous engine status and metrics"""
    if not engine:
        raise HTTPException(status_code=503, detail="Autonomous engine not initialized")

    return engine.get_status()


@router.post("/autonomous/config")
async def update_autonomous_config(
    config: Dict[str, Any],
    engine: Optional[AutonomousEngine] = Depends(get_autonomous_engine),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Update autonomous engine configuration"""
    if not engine:
        raise HTTPException(status_code=503, detail="Autonomous engine not initialized")

    engine.update_config(config)
    return {"status": "updated", "config": config}


@router.get("/autonomous/strategies")
def get_strategy_performance(
    engine: Optional[AutonomousEngine] = Depends(get_autonomous_engine),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get performance metrics for all strategies"""
    if not engine:
        raise HTTPException(status_code=503, detail="Autonomous engine not initialized")

    return {
        "strategies": list(engine.all_strategies.keys()),
        "performance": engine.strategy_performance,
        "total_strategies": len(engine.all_strategies)
    }


@router.post("/autonomous/scan")
async def trigger_manual_scan(
    engine: Optional[AutonomousEngine] = Depends(get_autonomous_engine),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Trigger a manual market scan (works even outside market hours for testing)"""
    if not engine:
        raise HTTPException(status_code=503, detail="Autonomous engine not initialized")

    try:
        # Run scan directly (bypass market hours check for testing)
        opportunities = await engine._scan_market()
        analyzed = await engine._analyze_opportunities(opportunities)

        return {
            "status": "completed",
            "symbols_scanned": engine.symbols_scanned,
            "opportunities_found": len(opportunities),
            "analyzed": len(analyzed),
            "filter_summary": engine.filter_summary,
            "top_picks": [e.get("symbol") for e in opportunities[:5]],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


# ==================== Watchlist Management Endpoints ====================

@router.get("/watchlist")
def get_watchlist(
    market_data=Depends(get_market_data_provider),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get current watchlist/universe being analyzed"""
    if not market_data:
        raise HTTPException(status_code=503, detail="Market data provider not initialized")

    if hasattr(market_data, 'get_watchlist_info'):
        return market_data.get_watchlist_info()
    else:
        # Fallback for providers without watchlist management
        return {
            "total_symbols": len(market_data.get_universe()),
            "universe": market_data.get_universe(),
            "custom_symbols": [],
            "custom_count": 0
        }


@router.post("/watchlist/add")
def add_to_watchlist(
    request: WatchlistRequest,
    market_data=Depends(get_market_data_provider),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Add symbols to the watchlist"""
    if not market_data:
        raise HTTPException(status_code=503, detail="Market data provider not initialized")

    if not hasattr(market_data, 'add_to_watchlist'):
        raise HTTPException(status_code=501, detail="Watchlist management not supported")

    return market_data.add_to_watchlist(request.symbols)


@router.post("/watchlist/remove")
def remove_from_watchlist(
    request: WatchlistRequest,
    market_data=Depends(get_market_data_provider),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Remove symbols from the watchlist"""
    if not market_data:
        raise HTTPException(status_code=503, detail="Market data provider not initialized")

    if not hasattr(market_data, 'remove_from_watchlist'):
        raise HTTPException(status_code=501, detail="Watchlist management not supported")

    return market_data.remove_from_watchlist(request.symbols)


@router.post("/watchlist/set")
def set_watchlist(
    request: WatchlistRequest,
    market_data=Depends(get_market_data_provider),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Set the entire custom watchlist (replaces existing)"""
    if not market_data:
        raise HTTPException(status_code=503, detail="Market data provider not initialized")

    if not hasattr(market_data, 'set_watchlist'):
        raise HTTPException(status_code=501, detail="Watchlist management not supported")

    return market_data.set_watchlist(request.symbols)


@router.get("/watchlist/snapshots")
def get_watchlist_snapshots(
    symbols: str = None,  # Optional comma-separated list of symbols
    market_data=Depends(get_market_data_provider),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get real-time market snapshots for watchlist symbols.
    Returns price, bid, ask, volume, change, etc. for each symbol.

    Args:
        symbols: Optional comma-separated list of symbols. If not provided, returns all watchlist symbols.
    """
    if not market_data:
        raise HTTPException(status_code=503, detail="Market data provider not initialized")

    # Get symbols to fetch
    if symbols:
        symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    else:
        # Get all watchlist symbols (limit to first 50 for performance)
        symbol_list = market_data.get_universe()[:50]

    if not symbol_list:
        return {"snapshots": {}, "count": 0}

    # Get snapshots using batch method if available, otherwise individual
    snapshots = {}

    if hasattr(market_data, 'get_batch_snapshots'):
        # Free provider has batch method
        snapshots = market_data.get_batch_snapshots(symbol_list)
    else:
        # Fall back to individual snapshots
        for symbol in symbol_list:
            try:
                snapshot = market_data.get_market_snapshot(symbol)
                if snapshot and snapshot.get("price"):
                    snapshots[symbol] = snapshot
            except Exception:
                pass

    return {
        "snapshots": snapshots,
        "count": len(snapshots),
        "requested": len(symbol_list)
    }


@router.get("/symbols/search")
async def search_symbols(
    q: str,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Search for valid stock symbols using Alpaca API.
    Returns matching tradable symbols for autocomplete.
    """
    from config import settings as app_settings

    if not q or len(q) < 1:
        return {"symbols": []}

    q = q.upper().strip()

    try:
        # Use Alpaca Trading API to search assets
        import httpx

        headers = {
            "APCA-API-KEY-ID": app_settings.alpaca_api_key,
            "APCA-API-SECRET-KEY": app_settings.alpaca_secret_key,
        }

        # Determine if paper or live
        base_url = "https://paper-api.alpaca.markets" if app_settings.alpaca_paper else "https://api.alpaca.markets"

        async with httpx.AsyncClient() as client:
            # Get all assets and filter
            response = await client.get(
                f"{base_url}/v2/assets",
                headers=headers,
                params={"status": "active", "asset_class": "us_equity"},
                timeout=10.0
            )

            if response.status_code != 200:
                # Fallback to static list from universe
                from market.universe import get_default_universe
                universe = get_default_universe()
                matches = [s for s in universe if s.startswith(q)][:limit]
                return {"symbols": matches, "source": "fallback"}

            assets = response.json()

            # Filter by search query and tradability
            matches = []
            for asset in assets:
                symbol = asset.get("symbol", "")
                name = asset.get("name", "")
                tradable = asset.get("tradable", False)
                fractionable = asset.get("fractionable", False)

                if not tradable:
                    continue

                # Match by symbol or name
                if symbol.startswith(q) or q in name.upper():
                    matches.append({
                        "symbol": symbol,
                        "name": name,
                        "exchange": asset.get("exchange", ""),
                        "tradable": tradable,
                        "fractionable": fractionable
                    })

                if len(matches) >= limit:
                    break

            # Sort by exact match first, then by symbol length
            matches.sort(key=lambda x: (0 if x["symbol"] == q else 1, len(x["symbol"])))

            return {"symbols": matches[:limit], "source": "alpaca"}

    except Exception as e:
        # Fallback to static universe list
        from market.universe import get_default_universe
        universe = get_default_universe()
        matches = [{"symbol": s, "name": "", "tradable": True} for s in universe if s.startswith(q)][:limit]
        return {"symbols": matches, "source": "fallback", "error": str(e)}


@router.get("/symbols/validate")
async def validate_symbol(
    symbol: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Validate if a symbol is a real, tradable stock."""
    from config import settings as app_settings

    symbol = symbol.upper().strip()

    if not symbol:
        return {"valid": False, "reason": "Empty symbol"}

    try:
        import httpx

        headers = {
            "APCA-API-KEY-ID": app_settings.alpaca_api_key,
            "APCA-API-SECRET-KEY": app_settings.alpaca_secret_key,
        }

        base_url = "https://paper-api.alpaca.markets" if app_settings.alpaca_paper else "https://api.alpaca.markets"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/v2/assets/{symbol}",
                headers=headers,
                timeout=5.0
            )

            if response.status_code == 200:
                asset = response.json()
                tradable = asset.get("tradable", False)
                return {
                    "valid": tradable,
                    "symbol": asset.get("symbol"),
                    "name": asset.get("name"),
                    "exchange": asset.get("exchange"),
                    "tradable": tradable,
                    "reason": "Valid tradable asset" if tradable else "Asset exists but not tradable"
                }
            elif response.status_code == 404:
                return {"valid": False, "reason": "Symbol not found"}
            else:
                return {"valid": False, "reason": f"API error: {response.status_code}"}

    except Exception as e:
        # Fallback: check if in our universe
        from market.universe import get_default_universe
        universe = get_default_universe()
        if symbol in universe:
            return {"valid": True, "symbol": symbol, "reason": "Found in trading universe", "source": "fallback"}
        return {"valid": False, "reason": str(e), "source": "fallback"}
