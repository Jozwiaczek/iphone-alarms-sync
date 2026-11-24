"""Actions, events, entities and the alarm-time timer."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util
from pytest_homeassistant.common import (
    MockConfigEntry,
    async_capture_events,
    async_fire_time_changed,
)

from custom_components.iphone_alarms_sync.binary_sensor import ALARM_BINARY_SENSORS
from custom_components.iphone_alarms_sync.const import (
    DOMAIN,
    EVENT_ALARM_EVENT,
    MISSED_EVENT_GRACE,
    STALE_AFTER,
    STALE_CHECK_INTERVAL,
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


async def test_alarm_device_name_has_time_only_for_shared_or_empty_label(
    hass: HomeAssistant, entry
) -> None:
    third_id = "FFFFFFFF-0000-1111-2222-333333333333"
    unlabeled_id = "99999999-8888-7777-6666-555555555555"
    await _sync(
        hass,
        [
            alarm_payload(),
            alarm_payload(alarm_id=OTHER_ID, label="Alarm", hour=6, minute=30),
            alarm_payload(alarm_id=third_id, label="Alarm", hour=8, minute=5),
            alarm_payload(alarm_id=unlabeled_id, label="", hour=9, minute=0),
        ],
    )
    registry = dr.async_get(hass)

    def name(alarm_id: str) -> str | None:
        device = registry.async_get_device_by_identifier(
            (DOMAIN, PHONE_ID, alarm_id), entry.entry_id
        )
        return device.name

    assert name(ALARM_ID) == "John iPhone Wake"
    assert name(OTHER_ID) == "John iPhone 06:30 Alarm"
    assert name(third_id) == "John iPhone 08:05 Alarm"
    assert name(unlabeled_id) == "John iPhone 09:00"


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
    sensor = "sensor.john_iphone_wake_up_alarm_last_went_off"
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
    assert triggers[0].data == {"device_id": phone_device.id, "subtype": "wakeup"}


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
    assert triggers[0].data == {"device_id": alarm_device.id, "subtype": "alarm"}
    assert hass.states.get("sensor.john_iphone_wake_last_snoozed").state != "unknown"


async def test_alarm_time_updates_last_alarm(
    hass: HomeAssistant, time_zone: None, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(
        dt_util.as_utc(
            datetime(2026, 11, 13, 6, 0, tzinfo=dt_util.get_default_time_zone())
        )
    )
    config_entry = await _setup_synced(hass, alarm_payload())
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
    assert config_entry.runtime_data.coordinator.last_activity_at() == _local(
        2026, 11, 13, 6, 0
    )


async def _setup_synced(
    hass: HomeAssistant, alarm: dict, **options: str
) -> MockConfigEntry:
    """Set up a phone that synced `alarm` just now."""
    config_entry = make_entry({ALARM_ID: alarm})
    config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        config_entry,
        options={
            **config_entry.options,
            "synced_at": dt_util.utcnow().isoformat(),
            **options,
        },
    )
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


async def _ring(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, at: datetime
) -> None:
    freezer.move_to(at)
    async_fire_time_changed(hass, at)
    await hass.async_block_till_done()


async def _report_goes_off(hass: HomeAssistant) -> None:
    await hass.services.async_call(
        DOMAIN,
        "report_alarm_event",
        {"phone_id": PHONE_ID, "alarm_id": ALARM_ID, "event": "goes_off"},
        blocking=True,
    )
    await hass.async_block_till_done()


SWITCH = "switch.john_iphone_wake_estimated_goes_off"


async def test_estimated_goes_off_fires_once_per_ring(
    hass: HomeAssistant, time_zone: None, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(_local(2026, 11, 13, 6, 0))
    await _setup_synced(hass, alarm_payload())
    assert hass.states.get(SWITCH).state == "on"
    events = async_capture_events(hass, EVENT_ALARM_EVENT)
    triggers = async_capture_events(hass, f"{DOMAIN}_goes_off")

    await _ring(hass, freezer, _local(2026, 11, 13, 7, 0))
    assert [(e.data["alarm_id"], e.data["estimated"]) for e in events] == [
        (ALARM_ID, True)
    ]
    assert triggers[0].data["subtype"] == "alarm"
    alarm_event = hass.states.get("event.john_iphone_wake_alarm")
    assert alarm_event.attributes["event_type"] == "goes_off"
    assert alarm_event.attributes["estimated"] is True
    assert hass.states.get("event.john_iphone_any_alarm").state == "unknown"

    # iOS turned the one-time alarm off; without a new sync it must not ring again.
    await _ring(hass, freezer, _local(2026, 11, 14, 7, 0))
    assert len(events) == 1


async def test_estimated_goes_off_can_be_turned_off(
    hass: HomeAssistant, time_zone: None, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(_local(2026, 11, 13, 6, 0))
    await _setup_synced(hass, alarm_payload(repeats=True, repeat_days=["Friday"]))
    events = async_capture_events(hass, EVENT_ALARM_EVENT)
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": SWITCH}, blocking=True
    )

    await _ring(hass, freezer, _local(2026, 11, 13, 7, 0))
    assert events == []

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": SWITCH}, blocking=True
    )
    await _ring(hass, freezer, _local(2026, 11, 20, 7, 0))
    assert len(events) == 1


@pytest.mark.parametrize("shortcut_first", [True, False])
async def test_shortcut_takes_over_from_estimate_without_a_duplicate(
    hass: HomeAssistant,
    time_zone: None,
    freezer: FrozenDateTimeFactory,
    shortcut_first: bool,
) -> None:
    alarm_at = _local(2026, 11, 13, 7, 0)
    freezer.move_to(alarm_at - timedelta(seconds=5))
    await _setup_synced(hass, alarm_payload(repeats=True, repeat_days=["Friday"]))
    events = async_capture_events(hass, EVENT_ALARM_EVENT)

    if shortcut_first:
        await _report_goes_off(hass)
        await _ring(hass, freezer, alarm_at)
    else:
        await _ring(hass, freezer, alarm_at)
        freezer.tick(timedelta(seconds=5))
        await _report_goes_off(hass)

    assert [e.data["estimated"] for e in events] == [not shortcut_first]
    assert hass.states.get(SWITCH).state == "off"
    assert hass.states.get("sensor.john_iphone_wake_last_went_off").state != "unknown"

    # From now on only the shortcut fires.
    await _ring(hass, freezer, alarm_at + timedelta(days=7))
    assert len(events) == 1
    await _report_goes_off(hass)
    assert [e.data["estimated"] for e in events] == [not shortcut_first, False]


async def test_estimate_is_off_for_a_phone_that_reports_goes_off(
    hass: HomeAssistant, time_zone: None
) -> None:
    """Upgrade from v1.5 and new alarms: shortcut users get no extra events."""
    await _setup_synced(
        hass, alarm_payload(), any_last_event_goes_off_at="2026-11-12T06:00:00+00:00"
    )
    assert hass.states.get(SWITCH).state == "off"

    await _sync(hass, [alarm_payload(), alarm_payload(alarm_id=OTHER_ID, label="Gym")])
    gym = "switch.john_iphone_gym_estimated_goes_off"
    assert hass.states.get(gym).state == "off"


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


async def test_malformed_alarm_is_rejected_and_nothing_stored(
    hass: HomeAssistant, entry
) -> None:
    with pytest.raises(ServiceValidationError, match="no valid alarm list"):
        await _sync(hass, [alarm_payload(hour="soon")])
    assert entry.options["alarms"][ALARM_ID]["hour"] == 7
    assert hass.states.get("sensor.john_iphone_next_alarm").state != "unavailable"


async def test_sync_coerces_and_trims_values(hass: HomeAssistant, entry) -> None:
    await _sync(hass, [alarm_payload(label=" Wake ", hour="6", repeat_days=None)])
    alarm = entry.runtime_data.coordinator.phone.alarms[ALARM_ID]
    assert (alarm.label, alarm.hour, alarm.repeat_days) == ("Wake", 6, [])


async def test_rejected_call_still_clears_missed_sensor(
    hass: HomeAssistant, entry
) -> None:
    coordinator = entry.runtime_data.coordinator
    coordinator.phone.missed_alarm_at = "2026-11-13T06:00:00+00:00"
    coordinator.async_set_updated_data(coordinator.phone)
    sensor = "binary_sensor.john_iphone_alarm_event_missed"
    assert hass.states.get(sensor).state == "on"

    with pytest.raises(ServiceValidationError, match="Unknown Alarm ID"):
        await hass.services.async_call(
            DOMAIN,
            "report_alarm_event",
            {"phone_id": PHONE_ID, "alarm_id": OTHER_ID, "event": "stopped"},
            blocking=True,
        )
    await hass.async_block_till_done()
    assert hass.states.get(sensor).state == "off"


async def test_empty_sync_removes_nothing(hass: HomeAssistant, entry) -> None:
    await _sync(hass, [])
    assert ALARM_ID in entry.runtime_data.coordinator.phone.alarms
    assert hass.states.get("sensor.john_iphone_last_sync").state != "unknown"


async def test_snooze_time_is_kept_and_needs_snooze(hass: HomeAssistant, entry) -> None:
    number = "number.john_iphone_wake_snooze_time"
    set_value = {"entity_id": number, "value": 5}
    await hass.services.async_call("number", "set_value", set_value, blocking=True)
    assert hass.states.get(number).state == "5"
    assert entry.options["alarms"][ALARM_ID]["snooze_time"] == 5

    await _sync(hass, [alarm_payload(allows_snooze=False)])
    assert hass.states.get(number).state == "unknown"
    with pytest.raises(ServiceValidationError, match="does not allow snooze"):
        await hass.services.async_call("number", "set_value", set_value, blocking=True)


async def test_silent_phone_raises_repair_until_it_sends_data(
    hass: HomeAssistant, entry, freezer: FrozenDateTimeFactory
) -> None:
    issue_id = f"no_data_{entry.entry_id}"
    issues = ir.async_get(hass)
    await _sync(hass, [alarm_payload()])
    assert issues.async_get_issue(DOMAIN, issue_id) is None

    freezer.tick(STALE_AFTER + STALE_CHECK_INTERVAL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert issues.async_get_issue(DOMAIN, issue_id)

    await _sync(hass, [alarm_payload()])
    assert issues.async_get_issue(DOMAIN, issue_id) is None


# Issue #43: an iPhone set to German, Monday to Friday at 06:15.
GERMAN_WEEKDAYS = ["Dienstag", "Donnerstag", "Freitag", "Montag", "Mittwoch"]


def _repeats_on(alarm) -> list[str]:
    return [
        d.key.removeprefix("repeats_")
        for d in ALARM_BINARY_SENSORS
        if d.key.startswith("repeats_") and d.is_on_fn(alarm)
    ]


async def test_sync_reads_repeat_days_in_the_iphone_language(
    hass: HomeAssistant, time_zone: None, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(_local(2026, 11, 14, 10, 0))  # Saturday
    config_entry = make_entry()
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await _sync(
        hass,
        [
            alarm_payload(
                label="Wecker",
                hour=6,
                minute=15,
                repeats=True,
                repeat_days=GERMAN_WEEKDAYS,
            )
        ],
    )

    alarm = config_entry.runtime_data.coordinator.phone.alarms[ALARM_ID]
    assert alarm.repeat_days == [
        "Tuesday",
        "Thursday",
        "Friday",
        "Monday",
        "Wednesday",
    ]
    assert config_entry.options["alarms"][ALARM_ID]["repeat_days"] == (
        alarm.repeat_days
    )
    assert _repeats_on(alarm) == [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
    ]
    monday = _local(2026, 11, 16, 6, 15)
    assert (
        dt_util.parse_datetime(
            hass.states.get("sensor.john_iphone_wecker_next_occurrence").state
        )
        == monday
    )
    assert (
        dt_util.parse_datetime(hass.states.get("sensor.john_iphone_next_alarm").state)
        == monday
    )
    assert hass.states.get("sensor.john_iphone_next_alarm_label").state == "Wecker"


async def test_sync_keeps_unknown_repeat_days(
    hass: HomeAssistant, entry, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(_local(2026, 11, 14, 10, 0))  # Saturday
    await _sync(
        hass,
        [
            alarm_payload(repeats=True, repeat_days=["Montag", "Friday", "Funday"]),
            alarm_payload(
                alarm_id=OTHER_ID,
                label="Gym",
                repeats=True,
                repeat_days=["Funday", "Montag", "Monday"],
            ),
        ],
    )
    alarms = entry.runtime_data.coordinator.phone.alarms
    assert alarms[ALARM_ID].repeat_days == ["Monday", "Friday", "Funday"]
    assert _repeats_on(alarms[ALARM_ID]) == ["monday", "friday"]
    # Duplicates after translation are harmless.
    assert _repeats_on(alarms[OTHER_ID]) == ["monday"]
    assert dt_util.parse_datetime(
        hass.states.get("sensor.john_iphone_gym_next_occurrence").state
    ) == _local(2026, 11, 16, 7, 0)


async def test_repeating_alarm_with_only_unknown_days_has_no_next_occurrence(
    hass: HomeAssistant, entry
) -> None:
    await _sync(hass, [alarm_payload(repeats=True, repeat_days=["Funday"])])
    state = hass.states.get("sensor.john_iphone_wake_next_occurrence")
    assert state.state == "unknown"


async def test_alarm_saved_with_localized_days_works_without_a_sync(
    hass: HomeAssistant, time_zone: None, freezer: FrozenDateTimeFactory
) -> None:
    """Alarms saved by v1.5 kept the days in the iPhone's language."""
    freezer.move_to(_local(2026, 11, 14, 10, 0))  # Saturday
    config_entry = make_entry(
        {ALARM_ID: alarm_payload(repeats=True, repeat_days=GERMAN_WEEKDAYS)}
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    alarm = config_entry.runtime_data.coordinator.phone.alarms[ALARM_ID]
    assert "Montag" not in alarm.repeat_days
    assert dt_util.parse_datetime(
        hass.states.get("sensor.john_iphone_next_alarm").state
    ) == _local(2026, 11, 16, 7, 0)
