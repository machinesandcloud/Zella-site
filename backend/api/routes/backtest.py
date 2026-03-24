"""
Backtest API Routes

Provides endpoints for running backtests, walk-forward validation,
and retrieving historical backtest results.
"""
from datetime import datetime
from typing import Any, Dict, List
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.routes.auth import get_current_user
from core.db import get_db
from core.backtest_engine import BacktestConfig, BacktestEngine
from core.backtest_metrics import BacktestMetricsCalculator
from core.walk_forward import WalkForwardConfig, WalkForwardValidator
from market.free_provider import FreeMarketDataProvider
from models import User
from models.backtest import BacktestRun, BacktestTrade, BacktestStatus


router = APIRouter(prefix="/api/backtest", tags=["backtest"])
logger = logging.getLogger(__name__)


class BacktestRequest(BaseModel):
    """Request model for running a backtest."""
    strategy: str
    symbol: str
    start_date: str
    end_date: str
    initial_capital: float = 10000.0
    parameters: Dict[str, Any] = Field(default_factory=dict)
    commission_per_trade: float = 0.0
    slippage_percent: float = 0.1
    bar_size: str = "5 mins"
    position_size_type: str = "fixed_quantity"
    position_size_value: float = 100


class WalkForwardRequest(BaseModel):
    """Request model for walk-forward validation."""
    strategy: str
    symbol: str
    start_date: str
    end_date: str
    initial_capital: float = 10000.0
    parameters: Dict[str, Any] = Field(default_factory=dict)
    in_sample_ratio: float = 0.7
    num_windows: int = 3
    anchored: bool = False
    commission_per_trade: float = 0.0
    slippage_percent: float = 0.1
    bar_size: str = "5 mins"


def _convert_duration_to_range(start_date: str, end_date: str) -> str:
    """Convert date range to data provider duration string."""
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    days = (end - start).days
    if days <= 5:
        return "5 D"
    elif days <= 30:
        return "1 M"
    elif days <= 90:
        return "3 M"
    elif days <= 180:
        return "6 M"
    return "1 Y"


@router.post("/run")
def run_backtest(
    payload: BacktestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Run a backtest on a strategy with historical data."""
    try:
        start_date = datetime.fromisoformat(payload.start_date)
        end_date = datetime.fromisoformat(payload.end_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")

    if start_date >= end_date:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")

    config = BacktestConfig(
        strategy_name=payload.strategy,
        symbol=payload.symbol.upper(),
        start_date=start_date,
        end_date=end_date,
        initial_capital=payload.initial_capital,
        strategy_parameters=payload.parameters,
        commission_per_trade=payload.commission_per_trade,
        slippage_percent=payload.slippage_percent,
        bar_size=payload.bar_size,
        position_size_type=payload.position_size_type,
        position_size_value=payload.position_size_value,
    )

    # Fetch historical data
    try:
        provider = FreeMarketDataProvider()
        duration = _convert_duration_to_range(payload.start_date, payload.end_date)
        bars = provider.get_historical_bars(payload.symbol.upper(), duration, payload.bar_size)
        if not bars:
            raise HTTPException(status_code=400, detail=f"No historical data for {payload.symbol}")
        logger.info(f"Fetched {len(bars)} bars for {payload.symbol}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch data: {e}")

    # Run backtest
    try:
        engine = BacktestEngine(config)
        result = engine.run(bars)
        calculator = BacktestMetricsCalculator()
        metrics = calculator.calculate(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        raise HTTPException(status_code=500, detail=f"Backtest failed: {e}")

    # Save to database
    try:
        backtest_run = BacktestRun(
            user_id=current_user.id,
            strategy_name=config.strategy_name,
            symbol=config.symbol,
            start_date=config.start_date,
            end_date=config.end_date,
            initial_capital=config.initial_capital,
            parameters=config.strategy_parameters,
            commission_per_trade=config.commission_per_trade,
            slippage_percent=config.slippage_percent,
            bar_size=config.bar_size,
            status=BacktestStatus.COMPLETED.value,
            progress_percent=100,
            completed_at=datetime.utcnow(),
            total_trades=metrics.total_trades,
            winning_trades=metrics.winning_trades,
            losing_trades=metrics.losing_trades,
            total_pnl=metrics.total_return,
            total_return_pct=metrics.total_return_pct,
            ending_equity=result.final_equity,
            max_drawdown=metrics.max_drawdown,
            max_drawdown_pct=metrics.max_drawdown_pct,
            sharpe_ratio=metrics.sharpe_ratio,
            sortino_ratio=metrics.sortino_ratio,
            calmar_ratio=metrics.calmar_ratio,
            win_rate=metrics.win_rate,
            profit_factor=metrics.profit_factor,
            avg_win=metrics.avg_win,
            avg_loss=metrics.avg_loss,
            max_consecutive_wins=metrics.max_consecutive_wins,
            max_consecutive_losses=metrics.max_consecutive_losses,
            avg_trade_duration_minutes=metrics.avg_trade_duration_minutes,
            equity_curve=[
                {"date": ep.timestamp.isoformat()[:10], "equity": round(ep.equity, 2)}
                for ep in result.equity_curve[::max(1, len(result.equity_curve) // 100)]
            ],
        )
        db.add(backtest_run)
        for trade in result.trades:
            db_trade = BacktestTrade(
                backtest_run_id=backtest_run.id,
                symbol=trade.symbol,
                action=trade.action,
                quantity=trade.quantity,
                entry_time=trade.entry_time,
                entry_price=trade.entry_price,
                entry_reason=trade.entry_reason,
                entry_confidence=trade.entry_confidence,
                exit_time=trade.exit_time,
                exit_price=trade.exit_price,
                exit_reason=trade.exit_reason,
                pnl=trade.pnl,
                pnl_percent=trade.pnl_percent,
                commission=trade.commission,
                slippage=trade.slippage,
                stop_loss=trade.stop_loss,
                take_profit=trade.take_profit,
                duration_minutes=trade.duration_minutes,
            )
            db.add(db_trade)
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to save backtest to database: {e}")

    return {
        "summary": {
            "strategy": payload.strategy,
            "symbol": payload.symbol,
            "total_trades": metrics.total_trades,
            "win_rate": round(metrics.win_rate, 2),
            "profit_factor": round(metrics.profit_factor, 4),
            "total_return": round(metrics.total_return, 2),
            "total_return_pct": round(metrics.total_return_pct, 2),
            "ending_equity": round(result.final_equity, 2),
            "sharpe_ratio": round(metrics.sharpe_ratio, 4),
            "sortino_ratio": round(metrics.sortino_ratio, 4),
            "max_drawdown": round(metrics.max_drawdown, 2),
            "max_drawdown_pct": round(metrics.max_drawdown_pct, 2),
            "calmar_ratio": round(metrics.calmar_ratio, 4),
        },
        "equity_curve": [
            {"date": ep.timestamp.isoformat()[:10], "equity": round(ep.equity, 2)}
            for ep in result.equity_curve[::max(1, len(result.equity_curve) // 50)]
        ],
        "trades": [
            {
                "symbol": t.symbol,
                "action": t.action,
                "quantity": t.quantity,
                "entryDate": t.entry_time.isoformat() if t.entry_time else None,
                "exitDate": t.exit_time.isoformat() if t.exit_time else None,
                "entryPrice": round(t.entry_price, 2),
                "exitPrice": round(t.exit_price, 2) if t.exit_price else None,
                "pnl": round(t.pnl, 2) if t.pnl else 0,
                "pnl_percent": round(t.pnl_percent, 2) if t.pnl_percent else 0,
                "exit_reason": t.exit_reason,
                "side": "LONG" if t.action == "BUY" else "SHORT",
            }
            for t in result.trades
        ],
        "metrics": metrics.to_dict(),
    }


@router.post("/walk-forward")
def run_walk_forward(
    payload: WalkForwardRequest,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Run walk-forward validation on a strategy."""
    try:
        start_date = datetime.fromisoformat(payload.start_date)
        end_date = datetime.fromisoformat(payload.end_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")

    if start_date >= end_date:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")

    if (end_date - start_date).days < 30:
        raise HTTPException(status_code=400, detail="Walk-forward requires at least 30 days")

    config = WalkForwardConfig(
        strategy_name=payload.strategy,
        symbol=payload.symbol.upper(),
        start_date=start_date,
        end_date=end_date,
        initial_capital=payload.initial_capital,
        strategy_parameters=payload.parameters,
        in_sample_ratio=payload.in_sample_ratio,
        num_windows=payload.num_windows,
        anchored=payload.anchored,
        commission_per_trade=payload.commission_per_trade,
        slippage_percent=payload.slippage_percent,
        bar_size=payload.bar_size,
    )

    try:
        provider = FreeMarketDataProvider()
        duration = _convert_duration_to_range(payload.start_date, payload.end_date)
        bars = provider.get_historical_bars(payload.symbol.upper(), duration, payload.bar_size)
        if not bars:
            raise HTTPException(status_code=400, detail=f"No data for {payload.symbol}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch data: {e}")

    try:
        validator = WalkForwardValidator(config)
        result = validator.run(bars)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Walk-forward failed: {e}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {e}")

    return result.to_dict()


@router.get("/history")
def get_backtest_history(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Get list of past backtest runs."""
    backtests = db.query(BacktestRun).filter(
        BacktestRun.user_id == current_user.id
    ).order_by(BacktestRun.created_at.desc()).limit(limit).all()

    return [
        {
            "id": b.id,
            "strategy": b.strategy_name,
            "symbol": b.symbol,
            "start_date": b.start_date.isoformat()[:10] if b.start_date else None,
            "end_date": b.end_date.isoformat()[:10] if b.end_date else None,
            "status": b.status,
            "total_return_pct": b.total_return_pct,
            "sharpe_ratio": b.sharpe_ratio,
            "total_trades": b.total_trades,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        }
        for b in backtests
    ]


@router.get("/strategies")
def get_available_strategies(
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, str]]:
    """Get list of available strategies for backtesting."""
    from core.strategy_engine import STRATEGY_REGISTRY
    return [
        {"name": name, "display_name": name.replace("_", " ").title()}
        for name in sorted(STRATEGY_REGISTRY.keys())
    ]


@router.delete("/{backtest_id}")
def delete_backtest(
    backtest_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """Delete a backtest run."""
    backtest = db.query(BacktestRun).filter(
        BacktestRun.id == backtest_id,
        BacktestRun.user_id == current_user.id
    ).first()
    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest not found")
    db.delete(backtest)
    db.commit()
    return {"message": "Backtest deleted successfully"}
