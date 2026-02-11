from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.db import get_db
from core.ibkr_client import IBKRClient
from api.routes.auth import get_current_user
from models import AccountSnapshot, Trade, User

router = APIRouter(prefix="/api/account", tags=["account"])


def get_ibkr_client() -> IBKRClient:
    from main import app

    return app.state.ibkr_client


@router.get("/summary")
def account_summary(
    ibkr: IBKRClient = Depends(get_ibkr_client),
    current_user: User = Depends(get_current_user),
) -> dict:
    if not ibkr.is_connected():
        return {"connected": False}
    return ibkr.get_account_summary()


@router.get("/positions")
def positions(
    ibkr: IBKRClient = Depends(get_ibkr_client),
    current_user: User = Depends(get_current_user),
) -> list:
    if not ibkr.is_connected():
        return []
    return ibkr.get_positions()


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
