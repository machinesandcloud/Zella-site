from datetime import datetime, timedelta
import random

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.routes.auth import get_current_user
from models import User

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


class BacktestRequest(BaseModel):
    strategy: str
    symbol: str
    start_date: str
    end_date: str
    initial_capital: float = 10000


@router.post("/run")
def run_backtest(
    payload: BacktestRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    random.seed(f"{payload.strategy}:{payload.symbol}:{payload.start_date}")
    start = datetime.fromisoformat(payload.start_date)
    points = 30
    step = max((datetime.fromisoformat(payload.end_date) - start).days // points, 1)

    equity = payload.initial_capital
    equity_curve = []
    trades = []
    wins = 0
    losses = 0
    gross_profit = 0
    gross_loss = 0

    for idx in range(points):
        equity += random.uniform(-150, 220)
        date = start + timedelta(days=idx * step)
        equity_curve.append({"date": date.date().isoformat(), "equity": round(equity, 2)})

        if idx % 3 == 0:
            pnl = random.uniform(-120, 180)
            trades.append(
                {
                    "symbol": payload.symbol,
                    "entryDate": date.date().isoformat(),
                    "exitDate": (date + timedelta(days=1)).date().isoformat(),
                    "pnl": round(pnl, 2),
                    "side": "LONG" if pnl >= 0 else "SHORT",
                }
            )
            if pnl >= 0:
                wins += 1
                gross_profit += pnl
            else:
                losses += 1
                gross_loss += pnl

    total_trades = len(trades)
    win_rate = round((wins / total_trades) * 100, 2) if total_trades else 0
    profit_factor = round(gross_profit / abs(gross_loss), 2) if gross_loss else 0
    total_return = round(((equity - payload.initial_capital) / payload.initial_capital) * 100, 2)

    return {
        "summary": {
            "strategy": payload.strategy,
            "symbol": payload.symbol,
            "total_trades": total_trades,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "total_return": total_return,
            "ending_equity": round(equity, 2),
        },
        "equity_curve": equity_curve,
        "trades": trades,
    }
