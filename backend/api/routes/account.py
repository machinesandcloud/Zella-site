from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.db import get_db
from core.alpaca_client import AlpacaClient
from api.routes.auth import get_current_user
from models import AccountSnapshot, Trade, User

router = APIRouter(prefix="/api/account", tags=["account"])


def get_alpaca_client() -> AlpacaClient | None:
    from main import app
    return getattr(app.state, "alpaca_client", None)


@router.get("/summary")
def account_summary(
    alpaca: AlpacaClient | None = Depends(get_alpaca_client),
    current_user: User = Depends(get_current_user),
) -> dict:
    if not alpaca or not alpaca.is_connected():
        return {"connected": False}
    return alpaca.get_account_summary()


@router.get("/positions")
def positions(
    alpaca: AlpacaClient | None = Depends(get_alpaca_client),
    current_user: User = Depends(get_current_user),
) -> list:
    if not alpaca or not alpaca.is_connected():
        return []
    return alpaca.get_positions()


@router.get("/history")
def account_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    trades = (
        db.query(Trade)
        .filter(Trade.user_id == current_user.id)
        .order_by(Trade.entry_time.desc())
        .limit(50)
        .all()
    )
    snapshots = (
        db.query(AccountSnapshot)
        .filter(AccountSnapshot.user_id == current_user.id)
        .order_by(AccountSnapshot.snapshot_time.desc())
        .limit(50)
        .all()
    )
    return {
        "trades": [
            {
                "symbol": t.symbol,
                "action": t.action,
                "quantity": t.quantity,
                "pnl": t.pnl,
                "entry_time": t.entry_time,
                "exit_time": t.exit_time,
            }
            for t in trades
        ],
        "snapshots": [
            {
                "account_value": s.account_value,
                "cash_balance": s.cash_balance,
                "buying_power": s.buying_power,
                "daily_pnl": s.daily_pnl,
                "snapshot_time": s.snapshot_time,
            }
            for s in snapshots
        ],
    }
