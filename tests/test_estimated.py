"""Estimated "goes off": user scenarios and edge cases."""

from __future__ import annotations

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant.common import (
    MockConfigEntry,
    async_capture_events,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.iphone_alarms_sync.const import (
    DOMAIN,
    EVENT_ALARM_EVENT,
    MISSED_EVENT_GRACE,
    STALE_AFTER,
    STALE_CHECK_INTERVAL,
)
from custom_components.iphone_alarms_sync.coordinator import AlarmData
from custom_components.iphone_alarms_sync.utils import rings_at

from .conftest import ALARM_ID, PHONE_ID, alarm_payload, make_entry
from .test_init import (
    OTHER_ID,
    SWITCH,
    _local,
    _report_goes_off,
    _ring,
    _setup_synced,
    _sync,
)

GYM_SWITCH = "switch.john_iphone_gym_estimated_goes_off"
FRIDAY = {"repeats": True, "repeat_days": ["Friday"]}
# Friday 2026-11-13.
SIX = (2026, 11, 13, 6, 0)
SEVEN = (2026, 11, 13, 7, 0)


def _estimated(events: list) -> list[str]:
    return [e.data["alarm_id"] for e in events if e.data["estimated"]]


async def test_new_user_with_sync_only(
    hass: HomeAssistant, time_zone: None, freezer: FrozenDateTimeFactory
) -> None:
    """Add the phone, run Sync once: goes off works and reaches an automation."""
    freezer.move_to(_local(*SIX))
    config_entry = make_entry()
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await _sync(hass, [alarm_payload()])
    assert hass.states.get(SWITCH).state == "on"

    calls = async_mock_service(hass, "test", "automation")
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "triggers": {
                    "trigger": f"{DOMAIN}.goes_off",
                    "target": {"entity_id": "event.john_iphone_wake_alarm"},
                },
                "actions": {"action": "test.automation"},
            }
        },
    )
    await _ring(hass, freezer, _local(*SEVEN))
    assert len(calls) == 1


async def test_upgrade_with_alarm_event_shortcut_stays_silent(
    hass: HomeAssistant, time_zone: None, freezer: FrozenDateTimeFactory
) -> None:
    """One alarm reported goes off before, so no alarm of the phone is estimated."""
    freezer.move_to(_local(*SIX))
    config_entry = make_entry(
        {
            ALARM_ID: {
                **alarm_payload(**FRIDAY),
                "last_event_goes_off_at": "2026-11-06T06:00:00+00:00",
            },
            OTHER_ID: alarm_payload(alarm_id=OTHER_ID, label="Gym", **FRIDAY),
        }
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(SWITCH).state == "off"
    assert hass.states.get(GYM_SWITCH).state == "off"

    events = async_capture_events(hass, EVENT_ALARM_EVENT)
    await _ring(hass, freezer, _local(*SEVEN))
    assert events == []


async def test_choice_survives_sync_and_restart(
    hass: HomeAssistant, time_zone: None, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(_local(*SIX))
    config_entry = await _setup_synced(hass, alarm_payload(**FRIDAY))
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": SWITCH}, blocking=True
    )
    await _sync(hass, [alarm_payload(label="Wake", **FRIDAY)])
    assert hass.states.get(SWITCH).state == "off"

    assert await hass.config_entries.async_reload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(SWITCH).state == "off"


async def test_one_time_alarm_rings_again_after_a_new_sync(
    hass: HomeAssistant, time_zone: None, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(_local(*SIX))
    await _setup_synced(hass, alarm_payload())
    events = async_capture_events(hass, EVENT_ALARM_EVENT)
    await _ring(hass, freezer, _local(*SEVEN))

    # The user turns the alarm on again in Clock, which syncs.
    freezer.move_to(_local(2026, 11, 13, 22, 0))
    await _sync(hass, [alarm_payload()])
    await _ring(hass, freezer, _local(2026, 11, 14, 7, 0))
    assert _estimated(events) == [ALARM_ID, ALARM_ID]


async def test_disabled_alarm_and_wrong_weekday_do_not_fire(
    hass: HomeAssistant, time_zone: None, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(_local(*SIX))
    await _setup_synced(
        hass, alarm_payload(repeats=True, repeat_days=["Saturday", "Sunday"])
    )
    events = async_capture_events(hass, EVENT_ALARM_EVENT)
    await _ring(hass, freezer, _local(*SEVEN))
    assert events == []

    # Saturday comes, but the alarm was turned off on the phone the evening before.
    freezer.move_to(_local(2026, 11, 13, 22, 0))
    await _sync(hass, [alarm_payload(enabled=False)])
    await _ring(hass, freezer, _local(2026, 11, 14, 7, 0))
    assert events == []


async def test_changed_time_fires_at_the_new_time_only(
    hass: HomeAssistant, time_zone: None, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(_local(*SIX))
    await _setup_synced(hass, alarm_payload(**FRIDAY))
    await _sync(hass, [alarm_payload(hour=7, minute=30, **FRIDAY)])
    events = async_capture_events(hass, EVENT_ALARM_EVENT)

    await _ring(hass, freezer, _local(*SEVEN))
    assert events == []
    await _ring(hass, freezer, _local(2026, 11, 13, 7, 30))
    assert _estimated(events) == [ALARM_ID]


async def test_deleted_alarm_does_not_fire(
    hass: HomeAssistant, time_zone: None, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(_local(*SIX))
    await _setup_synced(hass, alarm_payload(**FRIDAY))
    await _sync(hass, [alarm_payload(alarm_id=OTHER_ID, label="Gym", hour=9)])
    assert hass.states.get(SWITCH) is None
    events = async_capture_events(hass, EVENT_ALARM_EVENT)
    await _ring(hass, freezer, _local(*SEVEN))
    assert events == []


async def test_two_alarms_in_the_same_minute_both_fire(
    hass: HomeAssistant, time_zone: None, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(_local(*SIX))
    await _setup_synced(hass, alarm_payload())
    await _sync(
        hass,
        [alarm_payload(), alarm_payload(alarm_id=OTHER_ID, label="Gym", **FRIDAY)],
    )
    events = async_capture_events(hass, EVENT_ALARM_EVENT)
    await _ring(hass, freezer, _local(*SEVEN))
    assert sorted(_estimated(events)) == sorted([ALARM_ID, OTHER_ID])
    assert len({e.data["event_id"] for e in events}) == 2


async def test_no_late_event_when_home_assistant_was_down(
    hass: HomeAssistant, time_zone: None, freezer: FrozenDateTimeFactory
) -> None:
    """Home Assistant starts five minutes after the alarm: nothing fires late."""
    freezer.move_to(_local(2026, 11, 13, 7, 5))
    events = async_capture_events(hass, EVENT_ALARM_EVENT)
    config_entry = make_entry({ALARM_ID: alarm_payload(**FRIDAY)})
    config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        config_entry,
        options={**config_entry.options, "synced_at": _local(*SIX).isoformat()},
    )
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await _ring(hass, freezer, _local(2026, 11, 13, 7, 30))
    assert events == []
    # The next week it rings as usual.
    await _ring(hass, freezer, _local(2026, 11, 20, 7, 0))
    assert _estimated(events) == [ALARM_ID]


async def test_unloaded_entry_does_not_fire(
    hass: HomeAssistant, time_zone: None, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(_local(*SIX))
    config_entry = await _setup_synced(hass, alarm_payload(**FRIDAY))
    events = async_capture_events(hass, EVENT_ALARM_EVENT)
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await _ring(hass, freezer, _local(*SEVEN))
    assert events == []


async def test_estimate_is_no_proof_that_the_phone_works(
    hass: HomeAssistant, time_zone: None, freezer: FrozenDateTimeFactory
) -> None:
    """Estimated events keep neither the missed sensor nor the repair quiet."""
    freezer.move_to(_local(*SIX))
    config_entry = await _setup_synced(
        hass,
        alarm_payload(**FRIDAY),
        any_last_event_goes_off_at=_local(2026, 11, 12, 7, 0).isoformat(),
    )
    # The user wants estimates on top of the Any alarm shortcut.
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": SWITCH}, blocking=True
    )
    events = async_capture_events(hass, EVENT_ALARM_EVENT)
    await _ring(hass, freezer, _local(*SEVEN))
    assert _estimated(events) == [ALARM_ID]

    # The Any alarm shortcut stayed silent, so the alarm counts as missed.
    await _ring(hass, freezer, _local(*SEVEN) + MISSED_EVENT_GRACE)
    missed = "binary_sensor.john_iphone_alarm_event_missed"
    assert hass.states.get(missed).state == "on"

    # Weekly estimates do not hide a phone that stopped sending data.
    for _ in range(2):
        freezer.tick(STALE_AFTER)
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
    freezer.tick(STALE_CHECK_INTERVAL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert ir.async_get(hass).async_get_issue(
        DOMAIN, f"no_data_{config_entry.entry_id}"
    )
    assert config_entry.options["alarms"][ALARM_ID]["last_event_goes_off_at"] is None


async def test_snoozed_and_stopped_shortcuts_keep_the_estimate(
    hass: HomeAssistant, time_zone: None, freezer: FrozenDateTimeFactory
) -> None:
    """Only a real goes off replaces the estimate."""
    freezer.move_to(_local(*SIX))
    await _setup_synced(hass, alarm_payload(**FRIDAY))
    events = async_capture_events(hass, EVENT_ALARM_EVENT)
    await _ring(hass, freezer, _local(*SEVEN))
    for event in ("snoozed", "stopped"):
        await hass.services.async_call(
            DOMAIN,
            "report_alarm_event",
            {"phone_id": PHONE_ID, "alarm_id": ALARM_ID, "event": event},
            blocking=True,
        )
    await hass.async_block_till_done()
    assert [(e.data["event"], e.data["estimated"]) for e in events] == [
        ("goes_off", True),
        ("snoozed", False),
        ("stopped", False),
    ]
    assert hass.states.get(SWITCH).state == "on"


async def test_any_alarm_shortcut_keeps_the_estimate(
    hass: HomeAssistant, time_zone: None, freezer: FrozenDateTimeFactory
) -> None:
    """An Any alarm event is not tied to an alarm, so it switches nothing off."""
    freezer.move_to(_local(*SIX))
    await _setup_synced(hass, alarm_payload(**FRIDAY))
    await hass.services.async_call(
        DOMAIN,
        "report_device_event",
        {"phone_id": PHONE_ID, "event": "any_goes_off"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get(SWITCH).state == "on"
    assert (
        hass.states.get("event.john_iphone_any_alarm").attributes["estimated"] is False
    )
    # But an alarm added from now on is left to the shortcut.
    await _sync(
        hass,
        [
            alarm_payload(**FRIDAY),
            alarm_payload(alarm_id=OTHER_ID, label="Gym", **FRIDAY),
        ],
    )
    assert hass.states.get(GYM_SWITCH).state == "off"


async def test_shortcut_later_than_the_grace_period_fires_too(
    hass: HomeAssistant, time_zone: None, freezer: FrozenDateTimeFactory
) -> None:
    """A shortcut that reports much later is a new event, not a duplicate."""
    freezer.move_to(_local(*SIX))
    await _setup_synced(hass, alarm_payload(**FRIDAY))
    events = async_capture_events(hass, EVENT_ALARM_EVENT)
    await _ring(hass, freezer, _local(*SEVEN))
    freezer.tick(MISSED_EVENT_GRACE + timedelta(seconds=1))
    await _report_goes_off(hass)
    assert [e.data["estimated"] for e in events] == [True, False]
    assert hass.states.get(SWITCH).state == "off"


async def test_switch_turned_on_after_the_ring_does_not_swallow_the_shortcut(
    hass: HomeAssistant, time_zone: None, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(_local(*SIX))
    await _setup_synced(hass, alarm_payload(**FRIDAY))
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": SWITCH}, blocking=True
    )
    events = async_capture_events(hass, EVENT_ALARM_EVENT)
    await _ring(hass, freezer, _local(*SEVEN))
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": SWITCH}, blocking=True
    )
    freezer.tick(timedelta(seconds=30))
    await _report_goes_off(hass)
    assert [e.data["estimated"] for e in events] == [False]


async def test_manual_shortcut_run_switches_to_real_events(
    hass: HomeAssistant, time_zone: None, freezer: FrozenDateTimeFactory
) -> None:
    """Testing the new shortcut by hand, hours before the alarm, fires it."""
    freezer.move_to(_local(*SIX))
    await _setup_synced(hass, alarm_payload(**FRIDAY))
    events = async_capture_events(hass, EVENT_ALARM_EVENT)
    await _report_goes_off(hass)
    assert [e.data["estimated"] for e in events] == [False]
    await _ring(hass, freezer, _local(*SEVEN))
    assert len(events) == 1


async def test_recreated_alarm_starts_estimating_then_yields_to_its_shortcut(
    hass: HomeAssistant, time_zone: None, freezer: FrozenDateTimeFactory
) -> None:
    """With disabled alarms not synced, turning an alarm off deletes its history."""
    freezer.move_to(_local(*SIX))
    config_entry = make_entry()
    config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        config_entry, data={**config_entry.data, "sync_disabled_alarms": False}
    )
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await _sync(hass, [alarm_payload(**FRIDAY)])
    await _report_goes_off(hass)
    assert hass.states.get(SWITCH).state == "off"

    await _sync(
        hass,
        [
            alarm_payload(enabled=False, **FRIDAY),
            alarm_payload(alarm_id=OTHER_ID, label="Gym", hour=9),
        ],
    )
    await _sync(hass, [alarm_payload(**FRIDAY)])
    assert hass.states.get(SWITCH).state == "on"

    events = async_capture_events(hass, EVENT_ALARM_EVENT)
    await _ring(hass, freezer, _local(*SEVEN))
    freezer.tick(timedelta(seconds=3))
    await _report_goes_off(hass)
    assert len(events) == 1
    assert hass.states.get(SWITCH).state == "off"


async def test_two_phones_are_independent(
    hass: HomeAssistant, time_zone: None, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(_local(*SIX))
    await _setup_synced(
        hass,
        alarm_payload(**FRIDAY),
        any_last_event_goes_off_at=_local(2026, 11, 12, 7, 0).isoformat(),
    )
    mac = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        unique_id="john_mac",
        title="John Mac",
        data={"phone_id": "john_mac", "phone_name": "John Mac"},
        options={
            "alarms": {ALARM_ID: alarm_payload(**FRIDAY)},
            "synced_at": dt_util.utcnow().isoformat(),
        },
    )
    mac.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mac.entry_id)
    await hass.async_block_till_done()

    events = async_capture_events(hass, EVENT_ALARM_EVENT)
    await _ring(hass, freezer, _local(*SEVEN))
    assert [e.data["phone_id"] for e in events] == ["john_mac"]


async def test_rings_at(hass: HomeAssistant, time_zone: None) -> None:
    at = _local(*SEVEN)
    synced = _local(*SIX)
    one_time = AlarmData(alarm_id="A", enabled=True, hour=7)
    weekly = AlarmData(
        alarm_id="B", enabled=True, hour=7, repeats=True, repeat_days=["Friday"]
    )

    assert rings_at(one_time, at, synced)
    # Never synced, or synced before an earlier ring: iOS has turned it off.
    assert not rings_at(one_time, at, None)
    assert not rings_at(one_time, at, synced - timedelta(days=1))
    # Synced in the minute it rings: the next ring is tomorrow.
    assert not rings_at(one_time, at, at)
    assert not rings_at(one_time, at + timedelta(minutes=1), synced)

    assert rings_at(weekly, at, None)
    assert not rings_at(weekly, at + timedelta(days=1), synced)
    assert not rings_at(
        AlarmData(alarm_id="C", hour=7, repeats=True, repeat_days=["Friday"]),
        at,
        synced,
    )
    # "Repeats" without days is a one-time alarm.
    assert not rings_at(
        AlarmData(alarm_id="D", enabled=True, hour=7, repeats=True), at, None
    )


async def test_sync_only_phone_never_shows_a_missed_event(
    hass: HomeAssistant, time_zone: None, freezer: FrozenDateTimeFactory
) -> None:
    """No shortcut ever reported goes off, so none is expected."""
    freezer.move_to(_local(*SIX))
    await _setup_synced(hass, alarm_payload(**FRIDAY))
    await _ring(hass, freezer, _local(*SEVEN))
    await _ring(hass, freezer, _local(*SEVEN) + MISSED_EVENT_GRACE)
    assert hass.states.get("binary_sensor.john_iphone_alarm_event_missed").state == (
        "off"
    )


async def test_alarm_deleted_right_after_it_rang(
    hass: HomeAssistant, time_zone: None, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(_local(*SIX))
    await _setup_synced(
        hass,
        alarm_payload(**FRIDAY),
        any_last_event_goes_off_at=_local(2026, 11, 12, 7, 0).isoformat(),
    )
    await _ring(hass, freezer, _local(*SEVEN))
    # The sync that deletes the alarm also proves the phone is connected.
    await _sync(hass, [alarm_payload(alarm_id=OTHER_ID, label="Gym", hour=9)])
    await _ring(hass, freezer, _local(*SEVEN) + MISSED_EVENT_GRACE)
    assert hass.states.get("binary_sensor.john_iphone_alarm_event_missed").state == (
        "off"
    )


async def test_stale_one_time_alarm_is_not_reported_missed(
    hass: HomeAssistant, time_zone: None, freezer: FrozenDateTimeFactory
) -> None:
    """iOS turned the alarm off after its ring; the next day nothing is due."""
    freezer.move_to(_local(*SIX))
    await _setup_synced(
        hass,
        alarm_payload(),
        any_last_event_goes_off_at=_local(2026, 11, 12, 7, 0).isoformat(),
    )
    await _ring(hass, freezer, _local(*SEVEN))
    await hass.services.async_call(
        DOMAIN,
        "report_device_event",
        {"phone_id": PHONE_ID, "event": "any_goes_off"},
        blocking=True,
    )
    for day in (13, 14):
        await _ring(hass, freezer, _local(2026, 11, day, 7, 0) + MISSED_EVENT_GRACE)
        assert hass.states.get(
            "binary_sensor.john_iphone_alarm_event_missed"
        ).state == ("off")


async def test_localized_repeating_alarm_goes_off_every_week(
    hass: HomeAssistant, time_zone: None, freezer: FrozenDateTimeFactory
) -> None:
    """An iPhone set to German sends "Freitag"; the alarm still rings each Friday."""
    freezer.move_to(_local(*SIX))
    await _setup_synced(hass, alarm_payload(repeats=True, repeat_days=["Freitag"]))
    events = async_capture_events(hass, EVENT_ALARM_EVENT)

    await _ring(hass, freezer, _local(*SEVEN))
    await _ring(hass, freezer, _local(*SEVEN) + timedelta(days=7))
    assert _estimated(events) == [ALARM_ID, ALARM_ID]
