"""Device triggers of the phone and alarm devices."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.iphone_alarms_sync.const import DOMAIN
from custom_components.iphone_alarms_sync.device_trigger import async_get_triggers

from .conftest import ALARM_ID, PHONE_ID

ALARM_TYPES = ["goes_off", "snoozed", "stopped"]
SLEEP_TYPES = ["bedtime_starts", "waking_up", "wind_down_starts"]


def _device_id(hass: HomeAssistant, entry, *identifier: str) -> str:
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, PHONE_ID, *identifier), entry.entry_id
    )
    assert device
    return device.id


async def test_phone_offers_alarm_and_sleep_triggers(
    hass: HomeAssistant, entry
) -> None:
    triggers = await async_get_triggers(hass, _device_id(hass, entry))
    assert [t["type"] for t in triggers] == ALARM_TYPES + SLEEP_TYPES


async def test_alarm_offers_only_alarm_triggers(hass: HomeAssistant, entry) -> None:
    triggers = await async_get_triggers(hass, _device_id(hass, entry, ALARM_ID))
    assert [t["type"] for t in triggers] == ALARM_TYPES


async def test_alarm_trigger_runs_automation(hass: HomeAssistant, entry) -> None:
    calls = async_mock_service(hass, "test", "automation")
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "trigger": {
                    "platform": "device",
                    "domain": DOMAIN,
                    "device_id": _device_id(hass, entry, ALARM_ID),
                    "type": "goes_off",
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    for event in ("snoozed", "goes_off"):
        await hass.services.async_call(
            DOMAIN,
            "report_alarm_event",
            {"phone_id": PHONE_ID, "alarm_id": ALARM_ID, "event": event},
            blocking=True,
        )
    await hass.async_block_till_done()
    assert len(calls) == 1
