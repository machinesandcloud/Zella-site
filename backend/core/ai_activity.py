from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List


@dataclass
class ActivityEvent:
    event_type: str
    message: str
    level: str = "INFO"
    details: Dict[str, str] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ActivityLog:
    def __init__(self, max_events: int = 200) -> None:
        self.max_events = max_events
        self.events: List[ActivityEvent] = []
        self.status = {
            "state": "IDLE",
            "mode": "PAPER",
            "last_tick": None,
            "last_scan": None,
            "last_order": None,
        }

    def add(self, event_type: str, message: str, level: str = "INFO", details: Dict[str, str] | None = None) -> None:
        event = ActivityEvent(event_type=event_type, message=message, level=level, details=details or {})
        self.events.insert(0, event)
        if len(self.events) > self.max_events:
            self.events = self.events[: self.max_events]

    def snapshot(self) -> Dict[str, object]:
        return {
            "status": self.status,
            "events": [event.__dict__ for event in self.events],
        }

    def update_status(self, **kwargs: str) -> None:
        self.status.update(kwargs)
