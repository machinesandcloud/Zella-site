from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict

from fastapi import APIRouter, Depends

from api.routes.auth import get_current_user
from core.alpaca_client import AlpacaClient
from core.risk_manager import RiskManager
from models import User

router = APIRouter(prefix="/api/risk", tags=["risk"])


def get_alpaca_client() -> AlpacaClient | None:
    from main import app
    return getattr(app.state, "alpaca_client", None)


def get_risk_manager() -> RiskManager:
    from main import app

    return app.state.risk_manager


@router.get("/summary")
def risk_summary(
    alpaca: AlpacaClient | None = Depends(get_alpaca_client),
    risk_manager: RiskManager = Depends(get_risk_manager),
    current_user: User = Depends(get_current_user),
) -> Dict[str, object]:
    summary = alpaca.get_account_summary() if alpaca and alpaca.is_connected() else {}
    positions = alpaca.get_positions() if alpaca and alpaca.is_connected() else []
    account_value = float(summary.get("NetLiquidation", 0) or 0)
    daily_pnl = float(summary.get("RealizedPnL", 0) or 0)
    gross_exposure = 0.0
    net_exposure = 0.0
    largest = {"symbol": None, "percentOfAccount": 0.0}
    for pos in positions:
        qty = float(pos.get("quantity", 0) or 0)
        price = float(pos.get("avgPrice", 0) or 0)
        value = qty * price
        gross_exposure += abs(value)
        net_exposure += value
        if account_value > 0:
            percent = abs(value) / account_value * 100
            if percent > largest["percentOfAccount"]:
                largest = {"symbol": pos.get("symbol"), "percentOfAccount": percent}

    return {
        "accountMetrics": {
            "totalAccountValue": account_value,
            "cashBalance": float(summary.get("CashBalance", 0) or 0),
            "buyingPower": float(summary.get("BuyingPower", 0) or 0),
            "marginUsed": 0,
            "marginAvailable": float(summary.get("BuyingPower", 0) or 0),
            "dailyPnL": daily_pnl,
            "dailyPnLPercent": (daily_pnl / account_value * 100) if account_value else 0,
            "dailyLossLimit": risk_manager.config.max_daily_loss,
            "distanceToLimit": risk_manager.config.max_daily_loss + daily_pnl,
            "limitPercent": (
                abs(daily_pnl) / risk_manager.config.max_daily_loss * 100
                if risk_manager.config.max_daily_loss
                else 0
            ),
            "currentPositions": len(positions),
            "maxPositions": risk_manager.config.max_positions,
            "tradesToday": risk_manager.trades_today,
            "maxTradesPerDay": risk_manager.config.max_trades_per_day,
            "consecutiveLosses": risk_manager.consecutive_losses,
            "maxConsecutiveLosses": risk_manager.config.max_consecutive_losses,
            "totalExposure": gross_exposure,
            "netExposure": net_exposure,
            "grossExposure": gross_exposure,
            "largestPosition": largest,
            "sectorExposure": {},
        },
        "alerts": [],
        "killSwitch": {
            "enabled": risk_manager.emergency_stop_triggered,
            "reason": "Manual" if risk_manager.emergency_stop_triggered else None,
            "triggeredAt": datetime.now(timezone.utc).isoformat()
            if risk_manager.emergency_stop_triggered
            else None,
            "canReEnable": True,
            "cooldownMinutes": 0,
        },
        "circuitBreakers": {
            "consecutiveLosses": {
                "count": risk_manager.consecutive_losses,
                "limit": risk_manager.config.max_consecutive_losses,
                "action": "HALT",
            },
            "rapidDrawdown": {"lossPercent": 0, "timeMinutes": 0, "threshold": 5, "action": "HALT"},
        },
    }
