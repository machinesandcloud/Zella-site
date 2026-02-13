from fastapi import APIRouter, Depends, HTTPException

from core.auto_trader import AutoTrader
from api.routes.auth import get_current_user
from core.risk_manager import RiskManager
from core.ibkr_client import IBKRClient
from utils.market_hours import market_session
from models import User

router = APIRouter(prefix="/api/ai", tags=["ai"])


def get_auto_trader() -> AutoTrader:
    from main import app

    return app.state.auto_trader


def get_ibkr_client() -> IBKRClient:
    from main import app

    return app.state.ibkr_client


def get_risk_manager() -> RiskManager:
    from main import app

    return app.state.risk_manager


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
    current_user: User = Depends(get_current_user),
) -> dict:
    picks = auto_trader.select_top(limit)
    executed = []

    if execute:
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

    return {"ranked": picks, "executed": executed}
