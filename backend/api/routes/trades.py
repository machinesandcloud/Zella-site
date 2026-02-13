from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.routes.auth import get_current_user
from core.db import get_db
from models import Trade, User

router = APIRouter(prefix="/api/trades", tags=["trades"])


class TradeOut(BaseModel):
    id: int
    symbol: str
    action: str
    quantity: int
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
    entry_time: Optional[str] = None
    exit_time: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    setup_tag: Optional[str] = None
    catalyst: Optional[str] = None
    stop_method: Optional[str] = None
    risk_mode: Optional[str] = None

    class Config:
        from_attributes = True


class TradeNoteUpdate(BaseModel):
    notes: Optional[str] = None
    setup_tag: Optional[str] = None
    catalyst: Optional[str] = None
    stop_method: Optional[str] = None
    risk_mode: Optional[str] = None


@router.get("", response_model=List[TradeOut])
def list_trades(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Trade]:
    return (
        db.query(Trade)
        .filter(Trade.user_id == current_user.id)
        .order_by(Trade.entry_time.desc())
        .limit(200)
        .all()
    )


@router.put("/{trade_id}/notes", response_model=TradeOut)
def update_notes(
    trade_id: int,
    payload: TradeNoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Trade:
    trade = (
        db.query(Trade)
        .filter(Trade.user_id == current_user.id, Trade.id == trade_id)
        .first()
    )
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    if payload.notes is not None:
        trade.notes = payload.notes
    if payload.setup_tag is not None:
        trade.setup_tag = payload.setup_tag
    if payload.catalyst is not None:
        trade.catalyst = payload.catalyst
    if payload.stop_method is not None:
        trade.stop_method = payload.stop_method
    if payload.risk_mode is not None:
        trade.risk_mode = payload.risk_mode
    db.commit()
    db.refresh(trade)
    return trade
