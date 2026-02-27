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
    trades = db.query(Trade).filter(Trade.user_id == current_user.id).all()
    total_trades = len(trades)
    winning_trades = len([t for t in trades if (t.pnl or 0) > 0])
    losing_trades = len([t for t in trades if (t.pnl or 0) <= 0])
    win_rate = (winning_trades / total_trades) * 100 if total_trades else 0
    gross_profit = sum(float(t.pnl or 0) for t in trades if (t.pnl or 0) > 0)
    gross_loss = sum(float(t.pnl or 0) for t in trades if (t.pnl or 0) < 0)
    avg_win = gross_profit / winning_trades if winning_trades else 0
    avg_loss = abs(gross_loss) / losing_trades if losing_trades else 0
    profit_factor = gross_profit / abs(gross_loss) if gross_loss else 0
    largest_win = max([float(t.pnl or 0) for t in trades], default=0)
    largest_loss = min([float(t.pnl or 0) for t in trades], default=0)
    total_pnl = sum(float(t.pnl or 0) for t in trades)
    return {
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": round(win_rate, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2),
        "largest_win": round(largest_win, 2),
        "largest_loss": round(largest_loss, 2),
        "total_pnl": round(total_pnl, 2),
    }


@router.get("/trades/recent")
def recent_trades(
    days: int = 7,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> list:
    """Get recent trades. Default is last 7 days, up to 50 trades."""
    since = datetime.utcnow() - timedelta(days=days)
    trades = (
        db.query(Trade)
        .filter(Trade.user_id == current_user.id, Trade.entry_time >= since)
        .order_by(Trade.entry_time.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "symbol": t.symbol,
            "action": t.action,
            "quantity": t.quantity,
            "pnl": t.pnl,
            "pnl_percent": t.pnl_percent,
            "status": t.status,
            "entry_time": t.entry_time.isoformat() if t.entry_time else None,
            "exit_time": t.exit_time.isoformat() if t.exit_time else None,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "strategy_name": t.strategy_name,
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
