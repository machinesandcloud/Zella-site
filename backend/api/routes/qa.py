from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from core.db import get_db
from models import User, Trade
from api.routes.auth import hash_password, get_current_user

router = APIRouter(prefix="/api/qa", tags=["qa"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/db-diagnostics")
def db_diagnostics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Lightweight diagnostics to verify trade persistence and user alignment.
    """
    total_trades = db.query(func.count(Trade.id)).scalar() or 0
    user_trades = (
        db.query(func.count(Trade.id))
        .filter(Trade.user_id == current_user.id)
        .scalar()
        or 0
    )
    last_trade = db.query(Trade).order_by(Trade.entry_time.desc()).first()
    last_trade_summary = None
    if last_trade:
        last_trade_summary = {
            "id": last_trade.id,
            "symbol": last_trade.symbol,
            "entry_time": last_trade.entry_time.isoformat() if last_trade.entry_time else None,
            "user_id": last_trade.user_id,
            "status": last_trade.status,
            "pnl": float(last_trade.pnl or 0),
        }
    return {
        "current_user_id": current_user.id,
        "total_trades": total_trades,
        "user_trades": user_trades,
        "last_trade": last_trade_summary,
    }


@router.post("/seed-user")
def seed_user(db: Session = Depends(get_db)) -> dict:
    user = db.query(User).filter(User.username == "qa_user").first()
    if not user:
        user = User(username="qa_user", email="qa@example.com", password_hash=hash_password("qa"))
        db.add(user)
        db.commit()
        db.refresh(user)
    return {"id": user.id, "username": user.username}
