from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.routes.auth import get_current_user
from models import User

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


def get_alert_manager():
    from main import app

    return app.state.alert_manager


class AlertOut(BaseModel):
    id: str
    severity: str
    message: str
    created_at: str
    acknowledged: bool = False
    context: Optional[dict] = None


class AlertAck(BaseModel):
    alert_id: str


@router.get("", response_model=List[AlertOut])
def list_alerts(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
) -> List[AlertOut]:
    manager = get_alert_manager()
    return manager.list(limit=limit)


@router.post("/ack", response_model=AlertOut)
def acknowledge_alert(
    payload: AlertAck,
    current_user: User = Depends(get_current_user),
) -> AlertOut:
    manager = get_alert_manager()
    alert = manager.acknowledge(payload.alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert
