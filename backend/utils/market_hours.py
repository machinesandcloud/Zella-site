from __future__ import annotations

from datetime import datetime, time, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore


EASTERN = ZoneInfo("America/New_York") if ZoneInfo else timezone.utc

# Day trading time boundaries (Eastern Time)
MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)
NEW_TRADES_CUTOFF = time(15, 30)  # 3:30 PM - stop opening new positions
EOD_LIQUIDATION_TIME = time(15, 50)  # 3:50 PM - close ALL positions
POWER_HOUR_START = time(15, 0)  # 3:00 PM
OPENING_RANGE_END = time(9, 45)  # 9:45 AM - let opening chaos settle


def is_opening_range(now: datetime | None = None) -> bool:
    """
    Check if we're in the opening range period (9:30-9:45 AM ET).

    PRO TIP: The first 15 minutes are extremely volatile and unpredictable.
    Smart traders wait for the opening range to establish before entering.
    """
    now = now or datetime.now(tz=EASTERN)
    if now.tzinfo is None:
        now = now.replace(tzinfo=EASTERN)
    current_time = now.timetz()
    return MARKET_OPEN <= current_time < OPENING_RANGE_END


def minutes_since_open(now: datetime | None = None) -> int:
    """
    Get minutes elapsed since market open.
    Returns -1 if market is not in regular session.
    """
    now = now or datetime.now(tz=EASTERN)
    if now.tzinfo is None:
        now = now.replace(tzinfo=EASTERN)

    session = market_session(now)
    if not session["regular"]:
        return -1

    open_dt = now.replace(hour=9, minute=30, second=0, microsecond=0)
    delta = now - open_dt
    return max(0, int(delta.total_seconds() / 60))


def is_past_new_trade_cutoff(now: datetime | None = None) -> bool:
    """
    Check if we're past the cutoff time for opening new positions.
    Day traders should NOT open new positions after 3:30 PM ET.
    """
    now = now or datetime.now(tz=EASTERN)
    if now.tzinfo is None:
        now = now.replace(tzinfo=EASTERN)
    current_time = now.timetz()
    return current_time >= NEW_TRADES_CUTOFF


def is_eod_liquidation_time(now: datetime | None = None) -> bool:
    """
    Check if it's time to liquidate all positions (3:50 PM ET).
    Day traders MUST close all positions before market close.
    """
    now = now or datetime.now(tz=EASTERN)
    if now.tzinfo is None:
        now = now.replace(tzinfo=EASTERN)
    current_time = now.timetz()
    return current_time >= EOD_LIQUIDATION_TIME and current_time < MARKET_CLOSE


def minutes_until_close(now: datetime | None = None) -> int:
    """
    Get minutes remaining until market close.
    Returns -1 if market is closed.
    """
    now = now or datetime.now(tz=EASTERN)
    if now.tzinfo is None:
        now = now.replace(tzinfo=EASTERN)

    session = market_session(now)
    if not session["regular"]:
        return -1

    close_dt = now.replace(hour=16, minute=0, second=0, microsecond=0)
    delta = close_dt - now
    return max(0, int(delta.total_seconds() / 60))


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
