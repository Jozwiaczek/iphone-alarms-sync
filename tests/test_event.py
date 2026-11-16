"""Event entities and the "Alarm goes off" trigger for several alarms."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant.common import async_mock_service

from custom_components.iphone_alarms_sync.const import DOMAIN

from .conftest import ALARM_ID, PHONE_ID, alarm_payload

OTHER_ID = "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"
THIRD_ID = "99999999-8888-7777-6666-555555555555"


async def _report(hass: HomeAssistant, service: str, **data: str) -> None:
    await hass.services.async_call(
        DOMAIN, service, {"phone_id": PHONE_ID, **data}, blocking=True
    )


async def test_alarm_goes_off_trigger_for_chosen_alarms(
    hass: HomeAssistant, entry
) -> None:
    await hass.services.async_call(
        DOMAIN,
        "sync_alarms",
        {
            "phone_id": PHONE_ID,
            "alarms": [
                alarm_payload(),
                alarm_payload(alarm_id=OTHER_ID, label="Gym", hour=6),
                alarm_payload(alarm_id=THIRD_ID, label="Nap", hour=14),
            ],
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    calls = async_mock_service(hass, "test", "automation")
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "triggers": {
                    "trigger": f"{DOMAIN}.goes_off",
                    "target": {
                        "entity_id": [
                            "event.john_iphone_07_00_wake_alarm",
                            "event.john_iphone_06_00_gym_alarm",
                            "event.john_iphone_wake_up_alarm",
                        ]
                    },
                },
                "actions": {
                    "action": "test.automation",
                    "data": {"entity": "{{ trigger.entity_id }}"},
                },
            }
        },
    )
    await _report(hass, "report_alarm_event", alarm_id=ALARM_ID, event="snoozed")
    await _report(hass, "report_alarm_event", alarm_id=THIRD_ID, event="goes_off")
    await _report(hass, "report_device_event", event="any_goes_off")
    await _report(hass, "report_alarm_event", alarm_id=ALARM_ID, event="goes_off")
    await _report(hass, "report_alarm_event", alarm_id=OTHER_ID, event="goes_off")
    await _report(hass, "report_device_event", event="wakeup_goes_off")
    await hass.async_block_till_done()

    assert [c.data["entity"] for c in calls] == [
        "event.john_iphone_07_00_wake_alarm",
        "event.john_iphone_06_00_gym_alarm",
        "event.john_iphone_wake_up_alarm",
    ]
    state = hass.states.get("event.john_iphone_any_alarm")
    assert state.attributes["event_type"] == "goes_off"


async def test_sleep_event_entity(hass: HomeAssistant, entry) -> None:
    await _report(hass, "report_device_event", event="bedtime_starts")
    state = hass.states.get("event.john_iphone_sleep")
    assert state.attributes["event_type"] == "bedtime_starts"


async def test_area_target_skips_other_integrations(hass: HomeAssistant, entry) -> None:
    area = ar.async_get(hass).async_create("Bedroom")
    registry = er.async_get(hass)
    ours = "event.john_iphone_07_00_wake_alarm"
    foreign = registry.async_get_or_create("event", "other", "door").entity_id
    for entity_id in (ours, foreign):
        registry.async_update_entity(entity_id, area_id=area.id)
    hass.states.async_set(foreign, "unknown")
    calls = async_mock_service(hass, "test", "automation")
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "triggers": {
                    "trigger": f"{DOMAIN}.stopped",
                    "target": {"area_id": area.id},
                },
                "actions": {
                    "action": "test.automation",
                    "data": {"entity": "{{ trigger.entity_id }}"},
                },
            }
        },
    )
    hass.states.async_set(
        foreign, "2026-11-15T07:00:00+00:00", {"event_type": "stopped"}
    )
    await _report(hass, "report_alarm_event", alarm_id=ALARM_ID, event="stopped")
    await hass.async_block_till_done()
    assert [c.data["entity"] for c in calls] == [ours]
