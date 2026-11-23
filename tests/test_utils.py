"""Alarm time calculations."""

from __future__ import annotations

import logging
import unicodedata
from datetime import datetime

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.iphone_alarms_sync.coordinator import AlarmData, PhoneData
from custom_components.iphone_alarms_sync.utils import (
    WEEKDAY_MAP,
    calculate_next_alarm_datetime,
    calculate_next_occurrence,
    normalize_weekday,
)
from custom_components.iphone_alarms_sync.weekdays import WEEKDAY_NAMES


def _local(text: str) -> datetime:
    return dt_util.as_utc(
        datetime.fromisoformat(text).replace(tzinfo=dt_util.get_default_time_zone())
    )


async def test_one_time_alarm_rings_today_or_tomorrow(
    hass: HomeAssistant, time_zone: None
) -> None:
    alarm = AlarmData(alarm_id="A", enabled=True, hour=7, minute=0)
    # Friday 2026-11-13.
    assert calculate_next_occurrence(alarm, _local("2026-11-13 06:00")) == _local(
        "2026-11-13 07:00"
    )
    assert calculate_next_occurrence(alarm, _local("2026-11-13 07:00")) == _local(
        "2026-11-14 07:00"
    )


async def test_repeating_alarm_picks_next_weekday(
    hass: HomeAssistant, time_zone: None
) -> None:
    alarm = AlarmData(
        alarm_id="A",
        enabled=True,
        hour=6,
        minute=30,
        repeats=True,
        repeat_days=["Monday", "Friday"],
    )
    # Friday after 06:30 -> next Monday.
    assert calculate_next_occurrence(alarm, _local("2026-11-13 08:00")) == _local(
        "2026-11-16 06:30"
    )


async def test_disabled_alarm_has_no_occurrence(
    hass: HomeAssistant, time_zone: None
) -> None:
    alarm = AlarmData(alarm_id="A", enabled=False, hour=7)
    assert calculate_next_occurrence(alarm, _local("2026-11-13 06:00")) is None


async def test_next_alarm_after_local_midnight(
    hass: HomeAssistant, time_zone: None
) -> None:
    # 00:30 in Warsaw is still the previous day in UTC.
    phone = PhoneData(
        phone_id="p",
        phone_name="P",
        mobile_app_device_id=None,
        alarms={
            "A": AlarmData(alarm_id="A", enabled=True, hour=0, minute=45),
            "B": AlarmData(alarm_id="B", enabled=True, hour=7, minute=0),
        },
    )
    assert calculate_next_alarm_datetime(phone, _local("2026-11-14 00:30")) == (
        _local("2026-11-14 00:45"),
        "A",
    )


@pytest.mark.parametrize(
    ("sent", "day"),
    [
        ("Montag", "Monday"),  # de, from issue #43
        ("Mittwoch", "Wednesday"),
        ("Sonntag", "Sunday"),
        ("poniedziałek", "Monday"),  # pl
        ("niedziela", "Sunday"),
        ("lundi", "Monday"),  # fr
        ("domingo", "Sunday"),  # es, pt
        ("segunda-feira", "Monday"),  # pt
        ("Понедельник", "Monday"),  # ru, stand-alone form is capitalised
        ("月曜日", "Monday"),  # ja
        ("星期一", "Monday"),  # zh
        ("الاثنين", "Monday"),  # ar
        ("יום שני", "Monday"),  # he
        ("Δευτέρα", "Monday"),  # el
        ("Cumartesi", "Saturday"),  # tr
        ("Friday", "Friday"),  # en, as before
        (" MONTAG ", "Monday"),
        ("montag", "Monday"),
        (unicodedata.normalize("NFD", "Poniedziałek"), "Monday"),
    ],
)
def test_normalize_weekday_reads_any_iphone_language(sent: str, day: str) -> None:
    assert normalize_weekday(sent) == day


def test_unknown_weekday_is_kept_and_logged_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        # "So" is Sunday in German but Saturday in Czech, so abbreviations stay unknown.
        assert [normalize_weekday(d) for d in ("Blursday", "Blursday", "So")] == [
            "Blursday",
            "Blursday",
            "So",
        ]
    assert caplog.text.count("Unknown repeat day 'Blursday'") == 1
    assert "'So'" in caplog.text


def test_weekday_table_covers_every_day() -> None:
    assert set(WEEKDAY_NAMES.values()) == set(range(7))
    for name, day in WEEKDAY_MAP.items():
        assert WEEKDAY_NAMES[name.casefold()] == day
    # Keys are stored the way normalize_weekday looks them up.
    for key in WEEKDAY_NAMES:
        assert key == unicodedata.normalize("NFC", key).strip().casefold()
