"""Actions, events, entities and the alarm-time timer."""

from __future__ import annotations

from datetime import datetime

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    async_capture_events,
    async_fire_time_changed,
)

from custom_components.iphone_alarms_sync.const import (
    DOMAIN,
    EVENT_ALARM_EVENT,
    MISSED_EVENT_GRACE,
)

from .conftest import ALARM_ID, PHONE_ID, alarm_payload, make_entry

OTHER_ID = "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"


async def _sync(hass: HomeAssistant, alarms: list[dict]) -> None:
    await hass.services.async_call(
        DOMAIN,
        "sync_alarms",
        {"phone_id": PHONE_ID, "alarms": alarms},
        blocking=True,
    )
    await hass.async_block_till_done()


async def test_sync_adds_and_removes_alarm_entities(hass: HomeAssistant, entry) -> None:
    other = "binary_sensor.john_iphone_gym_enabled"
    assert hass.states.get(other) is None

    await _sync(hass, [alarm_payload(), alarm_payload(alarm_id=OTHER_ID, label="Gym")])
    assert hass.states.get(other).state == "on"
    assert hass.states.get("sensor.john_iphone_total_alarms").state == "2"

    await _sync(hass, [alarm_payload()])
    assert hass.states.get(other) is None
    assert not dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, PHONE_ID, OTHER_ID), entry.entry_id
    )


async def test_disabled_alarms_not_synced_when_turned_off(hass: HomeAssistant) -> None:
    config_entry = make_entry()
    config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        config_entry, data={**config_entry.data, "sync_disabled_alarms": False}
    )
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await _sync(hass, [alarm_payload(enabled=False)])
    assert config_entry.runtime_data.coordinator.phone.alarms == {}


async def test_device_event_updates_sensor_and_fires_events(
    hass: HomeAssistant, entry
) -> None:
    sensor = "sensor.john_iphone_wake_up_last_goes_off_at"
    assert hass.states.get(sensor).state == "unknown"
    events = async_capture_events(hass, EVENT_ALARM_EVENT)
    triggers = async_capture_events(hass, f"{DOMAIN}_goes_off")

    await hass.services.async_call(
        DOMAIN,
        "report_device_event",
        {"phone_id": PHONE_ID, "event": "wakeup_goes_off"},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert hass.states.get(sensor).state != "unknown"
    assert events[0].data["alarm_id"] == "wakeup"
    assert events[0].data["event"] == "goes_off"
    phone_device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, PHONE_ID), entry.entry_id
    )
    assert triggers[0].data == {"device_id": phone_device.id}


async def test_alarm_event_fires_trigger_for_alarm_device(
    hass: HomeAssistant, entry
) -> None:
    triggers = async_capture_events(hass, f"{DOMAIN}_snoozed")
    await hass.services.async_call(
        DOMAIN,
        "report_alarm_event",
        {"phone_id": PHONE_ID, "alarm_id": ALARM_ID.lower(), "event": "snoozed"},
        blocking=True,
    )
    await hass.async_block_till_done()

    alarm_device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, PHONE_ID, ALARM_ID), entry.entry_id
    )
    assert triggers[0].data == {"device_id": alarm_device.id}
    assert hass.states.get("sensor.john_iphone_wake_last_snoozed_at").state != (
        "unknown"
    )


async def test_alarm_time_updates_last_alarm(
    hass: HomeAssistant, time_zone: None, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(
        dt_util.as_utc(
            datetime(2026, 11, 13, 6, 0, tzinfo=dt_util.get_default_time_zone())
        )
    )
    config_entry = make_entry({ALARM_ID: alarm_payload()})
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.john_iphone_last_alarm").state == "unknown"
    assert hass.states.get("sensor.john_iphone_next_alarm_label").state == "Wake"

    alarm_at = dt_util.as_utc(
        datetime(2026, 11, 13, 7, 0, tzinfo=dt_util.get_default_time_zone())
    )
    freezer.move_to(alarm_at)
    async_fire_time_changed(hass, alarm_at)
    await hass.async_block_till_done()

    assert (
        dt_util.parse_datetime(hass.states.get("sensor.john_iphone_last_alarm").state)
        == alarm_at
    )
    assert (
        dt_util.parse_datetime(
            hass.states.get("sensor.john_iphone_wake_last_occurrence").state
        )
        == alarm_at
    )
    # The one-time alarm now rings tomorrow.
    assert dt_util.parse_datetime(
        hass.states.get("sensor.john_iphone_next_alarm").state
    ) == alarm_at.replace(day=14)


async def test_unknown_phone_id_is_rejected(hass: HomeAssistant, entry) -> None:
    with pytest.raises(ServiceValidationError, match="Unknown Phone ID"):
        await hass.services.async_call(
            DOMAIN, "sync_alarms", {"phone_id": "nope", "alarms": []}, blocking=True
        )


def _local(*args: int) -> datetime:
    return dt_util.as_utc(datetime(*args, tzinfo=dt_util.get_default_time_zone()))


async def test_missed_goes_off_event_turns_sensor_on(
    hass: HomeAssistant, time_zone: None, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(_local(2026, 11, 13, 6, 0))
    config_entry = make_entry(
        {ALARM_ID: alarm_payload(repeats=True, repeat_days=["Friday"])}
    )
    config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        config_entry,
        options={
            **config_entry.options,
            # The phone reported "any alarm" events before, so one is expected.
            "any_last_event_goes_off_at": _local(2026, 11, 12, 7, 0).isoformat(),
        },
    )
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    sensor = "binary_sensor.john_iphone_alarm_event_missed"
    assert hass.states.get(sensor).state == "off"

    check_at = _local(2026, 11, 13, 7, 0) + MISSED_EVENT_GRACE
    freezer.move_to(check_at)
    async_fire_time_changed(hass, check_at)
    await hass.async_block_till_done()
    assert hass.states.get(sensor).state == "on"

    await hass.services.async_call(
        DOMAIN,
        "report_device_event",
        {"phone_id": PHONE_ID, "event": "any_goes_off"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get(sensor).state == "off"


async def test_loads_and_keeps_v1_4_options(
    hass: HomeAssistant, time_zone: None
) -> None:
    """Options saved by v1.4.0 (with icon and last_alarm_id) survive a sync."""
    stored = {
        **alarm_payload(),
        "snooze_time": 5,
        "icon": "mdi:alarm",
        "last_event_goes_off_at": "2026-11-12T06:00:00+00:00",
        "last_occurrence_datetime": "2026-11-12T06:00:00+00:00",
    }
    config_entry = make_entry({ALARM_ID: stored})
    config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        config_entry,
        options={**config_entry.options, "last_alarm_id": ALARM_ID, "synced_at": None},
    )
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await _sync(hass, [alarm_payload(label="Wake up")])

    alarm = config_entry.options["alarms"][ALARM_ID]
    assert alarm["label"] == "Wake up"
    assert alarm["snooze_time"] == 5
    assert alarm["last_event_goes_off_at"] == "2026-11-12T06:00:00+00:00"
    assert "icon" not in alarm
    assert "last_alarm_id" not in config_entry.options
    assert hass.states.get("number.john_iphone_wake_snooze_time").state == "5"
