from __future__ import annotations

from datetime import datetime, time, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore


EASTERN = ZoneInfo("America/New_York") if ZoneInfo else timezone.utc


def market_session(now: datetime | None = None) -> dict:
    now = now or datetime.now(tz=EASTERN)
    if now.tzinfo is None:
        now = now.replace(tzinfo=EASTERN)
    weekday = now.weekday()  # 0=Mon
    if weekday >= 5:
        return {"session": "CLOSED", "regular": False, "premarket": False, "afterhours": False}
    regular_start = time(9, 30)
    regular_end = time(16, 0)
    premarket_start = time(4, 0)
    premarket_end = time(9, 30)
    afterhours_start = time(16, 0)
    afterhours_end = time(20, 0)

    current_time = now.timetz()
    if premarket_start <= current_time < premarket_end:
        return {"session": "PREMARKET", "regular": False, "premarket": True, "afterhours": False}
    if regular_start <= current_time < regular_end:
        return {"session": "REGULAR", "regular": True, "premarket": False, "afterhours": False}
    if afterhours_start <= current_time < afterhours_end:
        return {"session": "AFTERHOURS", "regular": False, "premarket": False, "afterhours": True}
    return {"session": "CLOSED", "regular": False, "premarket": False, "afterhours": False}
