from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


@dataclass
class Alert:
    id: str
    severity: str
    message: str
    created_at: str
    acknowledged: bool = False
    context: Optional[dict] = field(default=None)


@dataclass
class AlertSettings:
    in_app: bool = True
    email: bool = False
    sms: bool = False
    webhook: bool = False
    sound_enabled: bool = True


class AlertManager:
    def __init__(self, max_alerts: int = 500) -> None:
        self._alerts: List[Alert] = []
        self._max_alerts = max_alerts
        self._settings = AlertSettings()

    def create(self, severity: str, message: str, context: Optional[dict] = None) -> Alert:
        alert = Alert(
            id=f"alert_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
            severity=severity.upper(),
            message=message,
            created_at=datetime.now(timezone.utc).isoformat(),
            context=context,
        )
        self._alerts.insert(0, alert)
        if len(self._alerts) > self._max_alerts:
            self._alerts = self._alerts[: self._max_alerts]
        return alert

    def list(self, limit: int = 100) -> List[Alert]:
        return self._alerts[:limit]

    def acknowledge(self, alert_id: str) -> Optional[Alert]:
        for alert in self._alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                return alert
        return None

    def get_settings(self) -> AlertSettings:
        return self._settings

    def update_settings(self, **kwargs: bool) -> AlertSettings:
        for key, value in kwargs.items():
            if hasattr(self._settings, key):
                setattr(self._settings, key, bool(value))
        return self._settings
