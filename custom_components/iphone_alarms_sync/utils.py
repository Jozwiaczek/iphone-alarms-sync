from __future__ import annotations

import logging
import re
import unicodedata
from datetime import datetime, time, timedelta
from typing import TYPE_CHECKING

from homeassistant.util import dt as dt_util

from .weekdays import WEEKDAY_NAMES

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
_ENGLISH_DAYS = {day: name for name, day in WEEKDAY_MAP.items()}
_LOGGER = logging.getLogger(__name__)
# Unknown day names already logged, so each sync does not repeat the warning.
_unknown_days: set[str] = set()

UUID_PATTERN = re.compile(
    r"([0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12})",
    re.IGNORECASE,
)


def normalize_weekday(name: str) -> str:
    """The English name of a repeat day the shortcut sent in the iPhone's language."""
    day = WEEKDAY_NAMES.get(unicodedata.normalize("NFC", name).strip().casefold())
    if day is not None:
        return _ENGLISH_DAYS[day]
    # Kept as sent: dropping it would lose a day we may learn to read later.
    if name not in _unknown_days:
        _unknown_days.add(name)
        _LOGGER.warning("Unknown repeat day %r; please report it as an issue", name)
    return name


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


def rings_at(alarm: AlarmData, at: datetime, synced_at: datetime | None) -> bool:
    """Whether the alarm is expected to ring at `at`."""
    if calculate_next_occurrence(alarm, at - timedelta(minutes=1)) != at:
        return False
    # iOS turns a one-time alarm off after it rings, but HA learns that only on the
    # next sync, so only its first ring after the last sync counts.
    return bool(alarm.repeats and alarm.repeat_days) or (
        synced_at is not None and calculate_next_occurrence(alarm, synced_at) == at
    )


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
