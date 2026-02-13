from fastapi import APIRouter, Depends

from api.routes.auth import get_current_user
from models import User
from utils.market_hours import market_session

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/session")
def session_status(current_user: User = Depends(get_current_user)) -> dict:
    return market_session()
