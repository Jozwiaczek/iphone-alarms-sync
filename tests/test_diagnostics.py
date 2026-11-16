"""Diagnostics download for bug reports."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from custom_components.iphone_alarms_sync.const import DOMAIN
from custom_components.iphone_alarms_sync.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .conftest import ALARM_ID, PHONE_ID, alarm_payload, make_entry


async def test_diagnostics_before_first_sync(hass: HomeAssistant) -> None:
    entry = make_entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["phone"]["phone_id"] == PHONE_ID
    assert result["phone"]["synced_at"] is None
    assert result["phone"]["alarms"] == {}
    assert result["events"] == []


async def test_diagnostics_after_sync_and_event(hass: HomeAssistant, entry) -> None:
    await hass.services.async_call(
        DOMAIN,
        "sync_alarms",
        {"phone_id": PHONE_ID, "alarms": [alarm_payload(label="Gym")]},
        blocking=True,
    )
    await hass.services.async_call(
        DOMAIN,
        "report_alarm_event",
        {"phone_id": PHONE_ID, "alarm_id": ALARM_ID, "event": "goes_off"},
        blocking=True,
    )

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["phone"]["synced_at"] is not None
    assert result["phone"]["alarms"][ALARM_ID]["label"] == "Gym"
    assert ALARM_ID in result["options"]["alarms"]
    assert [e["event"] for e in result["events"]] == ["goes_off"]
