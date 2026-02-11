from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.routes.auth import get_current_user
from core.strategy_engine import STRATEGY_REGISTRY, StrategyEngine
from models import User

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


def get_strategy_engine() -> StrategyEngine:
    from main import app

    return app.state.strategy_engine


def get_strategy_configs() -> Dict[str, Any]:
    from main import app

    return app.state.strategy_configs


class StrategyConfig(BaseModel):
    parameters: Dict[str, Any] = {}
    risk: Dict[str, Any] = {}


@router.get("")
def list_strategies(
    engine: StrategyEngine = Depends(get_strategy_engine),
    current_user: User = Depends(get_current_user),
) -> dict:
    return {
        "available": list(STRATEGY_REGISTRY.keys()),
        "active": engine.get_active_strategies(),
    }


@router.get("/{strategy_id}")
def get_strategy(
    strategy_id: str,
    configs: Dict[str, Any] = Depends(get_strategy_configs),
    current_user: User = Depends(get_current_user),
) -> dict:
    return configs.get(strategy_id, {})


@router.post("/{strategy_id}/start")
def start_strategy(
    strategy_id: str,
    body: StrategyConfig,
    engine: StrategyEngine = Depends(get_strategy_engine),
    configs: Dict[str, Any] = Depends(get_strategy_configs),
    current_user: User = Depends(get_current_user),
) -> dict:
    if strategy_id not in STRATEGY_REGISTRY:
        raise HTTPException(status_code=404, detail="Strategy not found")
    configs[strategy_id] = body.model_dump()
    engine.start_strategy(strategy_id, strategy_id, body.model_dump())
    return {"status": "started", "strategy_id": strategy_id}


@router.post("/{strategy_id}/stop")
def stop_strategy(
    strategy_id: str,
    engine: StrategyEngine = Depends(get_strategy_engine),
    current_user: User = Depends(get_current_user),
) -> dict:
    engine.stop_strategy(strategy_id)
    return {"status": "stopped", "strategy_id": strategy_id}


@router.put("/{strategy_id}/config")
def update_config(
    strategy_id: str,
    body: StrategyConfig,
    configs: Dict[str, Any] = Depends(get_strategy_configs),
    current_user: User = Depends(get_current_user),
) -> dict:
    configs[strategy_id] = body.model_dump()
    return {"status": "updated", "strategy_id": strategy_id, "config": configs[strategy_id]}


@router.get("/{strategy_id}/performance")
def strategy_performance(
    strategy_id: str,
    engine: StrategyEngine = Depends(get_strategy_engine),
    current_user: User = Depends(get_current_user),
) -> dict:
    return engine.get_strategy_performance(strategy_id)
