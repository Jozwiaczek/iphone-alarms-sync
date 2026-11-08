from __future__ import annotations

import re
from datetime import datetime, time, timedelta
from typing import TYPE_CHECKING

from homeassistant.util import dt as dt_util

if TYPE_CHECKING:
    from .coordinator import AlarmData, PhoneData

WEEKDAY_MAP = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}

UUID_PATTERN = re.compile(
    r"([0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12})",
    re.IGNORECASE,
)


def calculate_next_occurrence(
    alarm: AlarmData, now: datetime | None = None
) -> datetime | None:
    if not alarm.enabled:
        return None

    now_local = dt_util.as_local(now or dt_util.utcnow())
    alarm_time = time(hour=alarm.hour, minute=alarm.minute)
    repeating = bool(alarm.repeats and alarm.repeat_days)

    if repeating:
        offsets = [
            (WEEKDAY_MAP[day] - now_local.weekday()) % 7
            for day in alarm.repeat_days
            if day in WEEKDAY_MAP
        ]
    else:
        offsets = [0]

    candidates = []
    for days_ahead in offsets:
        if days_ahead == 0 and alarm_time <= now_local.time():
            # Passed today: a one-time alarm rings tomorrow, a weekly one next week.
            days_ahead = 7 if repeating else 1
        local = datetime.combine(
            now_local.date() + timedelta(days=days_ahead), alarm_time
        )
        candidates.append(dt_util.as_utc(local))

    return min(candidates, default=None)


def calculate_next_alarm_datetime(
    phone: PhoneData, now: datetime | None = None
) -> tuple[datetime | None, str | None]:
    next_alarm_datetime: datetime | None = None
    next_alarm_id: str | None = None

    for alarm in phone.alarms.values():
        occurrence = calculate_next_occurrence(alarm, now)
        if occurrence is not None and (
            next_alarm_datetime is None or occurrence < next_alarm_datetime
        ):
            next_alarm_datetime, next_alarm_id = occurrence, alarm.alarm_id

    return next_alarm_datetime, next_alarm_id


def extract_alarm_uuid(alarm_id: str) -> str:
    match = UUID_PATTERN.search(alarm_id)
    if match:
        return match.group(1).upper()
    return alarm_id
