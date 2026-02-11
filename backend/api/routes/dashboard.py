from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.routes.auth import get_current_user
from core.db import get_db
from core.ibkr_client import IBKRClient
from models import AccountSnapshot, Trade, User

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def get_ibkr_client() -> IBKRClient:
    from main import app

    return app.state.ibkr_client


@router.get("/overview")
def overview(
    db: Session = Depends(get_db),
    ibkr: IBKRClient = Depends(get_ibkr_client),
    current_user: User = Depends(get_current_user),
) -> dict:
    account_summary = ibkr.get_account_summary() if ibkr.is_connected() else {}
    recent_trades = (
        db.query(Trade)
        .filter(Trade.user_id == current_user.id)
        .order_by(Trade.entry_time.desc())
        .limit(5)
        .all()
    )
    return {
        "account_summary": account_summary,
        "recent_trades": [
            {
                "symbol": t.symbol,
                "action": t.action,
                "quantity": t.quantity,
                "pnl": t.pnl,
                "status": t.status,
            }
            for t in recent_trades
        ],
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/metrics")
def metrics(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    total_trades = db.query(Trade).filter(Trade.user_id == current_user.id).count()
    winning_trades = db.query(Trade).filter(Trade.user_id == current_user.id, Trade.pnl > 0).count()
    losing_trades = db.query(Trade).filter(Trade.user_id == current_user.id, Trade.pnl <= 0).count()
    win_rate = (winning_trades / total_trades) * 100 if total_trades else 0
    return {
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": round(win_rate, 2),
    }


@router.get("/trades/recent")
def recent_trades(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list:
    since = datetime.utcnow() - timedelta(days=1)
    trades = (
        db.query(Trade)
        .filter(Trade.user_id == current_user.id, Trade.entry_time >= since)
        .all()
    )
    return [
        {
            "symbol": t.symbol,
            "action": t.action,
            "quantity": t.quantity,
            "pnl": t.pnl,
            "status": t.status,
            "entry_time": t.entry_time,
        }
        for t in trades
    ]


@router.get("/account/snapshots")
def snapshots(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list:
    snapshots = (
        db.query(AccountSnapshot)
        .filter(AccountSnapshot.user_id == current_user.id)
        .order_by(AccountSnapshot.snapshot_time.desc())
        .limit(10)
        .all()
    )
    return [
        {
            "account_value": s.account_value,
            "cash_balance": s.cash_balance,
            "buying_power": s.buying_power,
            "daily_pnl": s.daily_pnl,
            "snapshot_time": s.snapshot_time,
        }
        for s in snapshots
    ]
