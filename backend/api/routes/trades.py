from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

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


@router.get("/setup-stats")
def setup_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    trades = (
        db.query(Trade)
        .filter(Trade.user_id == current_user.id)
        .all()
    )
    stats = {}
    for trade in trades:
        key = trade.setup_tag or "Unlabeled"
        entry = stats.setdefault(
            key,
            {
                "setup": key,
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "total_pnl": 0.0,
            },
        )
        entry["trades"] += 1
        pnl = float(trade.pnl or 0)
        entry["total_pnl"] += pnl
        if pnl > 0:
            entry["wins"] += 1
        elif pnl < 0:
            entry["losses"] += 1
    output = []
    for item in stats.values():
        trades_count = item["trades"]
        win_rate = (item["wins"] / trades_count * 100) if trades_count else 0
        avg_pnl = item["total_pnl"] / trades_count if trades_count else 0
        output.append(
            {
                "setup": item["setup"],
                "trades": trades_count,
                "wins": item["wins"],
                "losses": item["losses"],
                "win_rate": round(win_rate, 2),
                "avg_pnl": round(avg_pnl, 2),
                "total_pnl": round(item["total_pnl"], 2),
            }
        )
    return {"setups": sorted(output, key=lambda x: x["total_pnl"], reverse=True)}


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


# ==================== Strategy Performance Endpoints ====================

class StrategyTradeOut(BaseModel):
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
    strategy_name: Optional[str] = None

    class Config:
        from_attributes = True


def calculate_strategy_pnl(trades: List[Trade], days: int) -> dict:
    """Calculate PnL statistics for trades within a time period."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    filtered = [t for t in trades if t.exit_time and t.exit_time >= cutoff]

    total_pnl = sum(float(t.pnl or 0) for t in filtered)
    wins = sum(1 for t in filtered if (t.pnl or 0) > 0)
    losses = sum(1 for t in filtered if (t.pnl or 0) < 0)
    trade_count = len(filtered)
    win_rate = (wins / trade_count * 100) if trade_count > 0 else 0
    avg_pnl = total_pnl / trade_count if trade_count > 0 else 0

    return {
        "total_pnl": round(total_pnl, 2),
        "trades": trade_count,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 2),
        "avg_pnl": round(avg_pnl, 2),
    }


@router.get("/strategy-performance")
def strategy_performance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get performance metrics for each strategy over different time periods.
    Returns PnL for 1 day, 3 days, 7 days, and 30 days.
    """
    # Get all trades with a strategy name
    trades = (
        db.query(Trade)
        .filter(
            Trade.user_id == current_user.id,
            Trade.strategy_name.isnot(None),
            Trade.strategy_name != "",
        )
        .all()
    )

    # Group trades by strategy
    strategy_trades: dict[str, List[Trade]] = {}
    for trade in trades:
        strategy = trade.strategy_name
        if strategy not in strategy_trades:
            strategy_trades[strategy] = []
        strategy_trades[strategy].append(trade)

    # Calculate metrics for each strategy
    strategies = []
    for strategy_name, strat_trades in strategy_trades.items():
        # All-time stats
        all_pnl = sum(float(t.pnl or 0) for t in strat_trades)
        all_trades = len(strat_trades)
        all_wins = sum(1 for t in strat_trades if (t.pnl or 0) > 0)
        all_losses = sum(1 for t in strat_trades if (t.pnl or 0) < 0)

        strategies.append({
            "strategy": strategy_name,
            "all_time": {
                "total_pnl": round(all_pnl, 2),
                "trades": all_trades,
                "wins": all_wins,
                "losses": all_losses,
                "win_rate": round((all_wins / all_trades * 100) if all_trades > 0 else 0, 2),
            },
            "daily": calculate_strategy_pnl(strat_trades, 1),
            "three_day": calculate_strategy_pnl(strat_trades, 3),
            "weekly": calculate_strategy_pnl(strat_trades, 7),
            "monthly": calculate_strategy_pnl(strat_trades, 30),
        })

    # Sort by all-time PnL descending
    strategies.sort(key=lambda x: x["all_time"]["total_pnl"], reverse=True)

    return {
        "strategies": strategies,
        "total_strategies": len(strategies),
    }


@router.get("/by-strategy/{strategy_name}", response_model=List[StrategyTradeOut])
def trades_by_strategy(
    strategy_name: str,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Trade]:
    """
    Get all trades for a specific strategy.
    """
    trades = (
        db.query(Trade)
        .filter(
            Trade.user_id == current_user.id,
            Trade.strategy_name == strategy_name,
        )
        .order_by(Trade.exit_time.desc())
        .limit(limit)
        .all()
    )
    return trades


@router.get("/strategies")
def list_strategies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get a list of all unique strategy names that have been used.
    """
    strategies = (
        db.query(Trade.strategy_name)
        .filter(
            Trade.user_id == current_user.id,
            Trade.strategy_name.isnot(None),
            Trade.strategy_name != "",
        )
        .distinct()
        .all()
    )

    return {
        "strategies": [s[0] for s in strategies],
        "count": len(strategies),
    }
