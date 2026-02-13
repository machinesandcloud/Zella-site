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


class AlertSettingsOut(BaseModel):
    in_app: bool
    email: bool
    sms: bool
    webhook: bool
    sound_enabled: bool


class AlertSettingsUpdate(BaseModel):
    in_app: bool | None = None
    email: bool | None = None
    sms: bool | None = None
    webhook: bool | None = None
    sound_enabled: bool | None = None


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


@router.get("/settings", response_model=AlertSettingsOut)
def get_settings(current_user: User = Depends(get_current_user)) -> AlertSettingsOut:
    settings = get_alert_manager().get_settings()
    return settings


@router.put("/settings", response_model=AlertSettingsOut)
def update_settings(
    payload: AlertSettingsUpdate,
    current_user: User = Depends(get_current_user),
) -> AlertSettingsOut:
    settings = get_alert_manager().update_settings(**payload.model_dump(exclude_none=True))
    return settings
