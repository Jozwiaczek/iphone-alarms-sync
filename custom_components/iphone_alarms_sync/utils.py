from __future__ import annotations

import re
from datetime import datetime, time, timedelta
from typing import TYPE_CHECKING, cast

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

    if now is None:
        now = dt_util.utcnow()

    now_local = dt_util.as_local(now)
    current_time = now_local.time()
    current_weekday = now_local.weekday()
    current_date = now_local.date()

    alarm_time = time(hour=alarm.hour, minute=alarm.minute)

    if alarm.repeats and alarm.repeat_days:
        min_days_ahead = 7
        next_datetime = None

        for day_name in alarm.repeat_days:
            day_num = WEEKDAY_MAP.get(day_name)
            if day_num is None:
                continue

            days_ahead = (day_num - current_weekday) % 7
            if days_ahead == 0 and alarm_time <= current_time:
                days_ahead = 7
            candidate_date = current_date + timedelta(days=days_ahead)
            combined = datetime.combine(candidate_date, alarm_time)
            candidate_datetime = dt_util.as_utc(combined)

            if days_ahead == 0:
                if next_datetime is None or candidate_datetime < next_datetime:
                    next_datetime = candidate_datetime
                    min_days_ahead = 0
            elif days_ahead > 0:
                if days_ahead < min_days_ahead or (
                    days_ahead == min_days_ahead
                    and (next_datetime is None or candidate_datetime < next_datetime)
                ):
                    next_datetime = candidate_datetime
                    min_days_ahead = days_ahead

        if next_datetime is None:
            for day_name in alarm.repeat_days:
                day_num = WEEKDAY_MAP.get(day_name)
                if day_num is None:
                    continue
                days_ahead = (day_num - current_weekday) % 7
                if days_ahead > 0:
                    candidate_date = current_date + timedelta(days=days_ahead)
                    combined = datetime.combine(candidate_date, alarm_time)
                    candidate_datetime = dt_util.as_utc(combined)
                    if next_datetime is None or candidate_datetime < next_datetime:
                        next_datetime = candidate_datetime

        return next_datetime
    else:
        combined = datetime.combine(current_date, alarm_time)
        alarm_datetime = cast(datetime, dt_util.as_utc(combined))
        if alarm_time > current_time:
            return alarm_datetime
        return None


def calculate_next_alarm_datetime(
    phone: PhoneData, now: datetime | None = None
) -> tuple[datetime | None, str | None]:
    if now is None:
        now = dt_util.utcnow()

    now_local = dt_util.as_local(now)
    current_time = now_local.time()
    current_weekday = now_local.weekday()
    current_date = now_local.date()

    next_alarm_datetime: datetime | None = None
    next_alarm_id: str | None = None
    min_days_ahead = 7

    for alarm in phone.alarms.values():
        if not alarm.enabled:
            continue

        alarm_time = time(hour=alarm.hour, minute=alarm.minute)

        if alarm.repeats and alarm.repeat_days:
            for day_name in alarm.repeat_days:
                day_num = WEEKDAY_MAP.get(day_name)
                if day_num is None:
                    continue

                days_ahead = (day_num - current_weekday) % 7
                candidate_date = current_date + timedelta(days=days_ahead)
                combined = datetime.combine(candidate_date, alarm_time)
                candidate_datetime = dt_util.as_utc(combined)

                if days_ahead == 0 and alarm_time > current_time:
                    if (
                        next_alarm_datetime is None
                        or candidate_datetime < next_alarm_datetime
                    ):
                        next_alarm_datetime = candidate_datetime
                        next_alarm_id = alarm.alarm_id
                        min_days_ahead = 0
                elif days_ahead > 0:
                    if days_ahead < min_days_ahead or (
                        days_ahead == min_days_ahead
                        and (
                            next_alarm_datetime is None
                            or candidate_datetime < next_alarm_datetime
                        )
                    ):
                        next_alarm_datetime = candidate_datetime
                        next_alarm_id = alarm.alarm_id
                        min_days_ahead = days_ahead
        else:
            alarm_datetime = dt_util.as_utc(datetime.combine(current_date, alarm_time))
            if alarm_time > current_time:
                if next_alarm_datetime is None or alarm_datetime < next_alarm_datetime:
                    next_alarm_datetime = alarm_datetime
                    next_alarm_id = alarm.alarm_id
                    min_days_ahead = 0

    return next_alarm_datetime, next_alarm_id


def extract_alarm_uuid(alarm_id: str) -> str:
    match = UUID_PATTERN.search(alarm_id)
    if match:
        return match.group(1).upper()
    return alarm_id
