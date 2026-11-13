"""Shared fixtures for the iPhone Alarms Sync tests."""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.iphone_alarms_sync.const import DOMAIN

PHONE_ID = "john_iphone"
ALARM_ID = "11111111-2222-3333-4444-555555555555".upper()


def alarm_payload(**overrides: Any) -> dict[str, Any]:
    """One alarm as the Sync shortcut sends it."""
    return {
        "alarm_id": ALARM_ID,
        "label": "Wake",
        "enabled": True,
        "hour": 7,
        "minute": 0,
        "repeats": False,
        "repeat_days": [],
        "allows_snooze": True,
        **overrides,
    }


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Load the integration from custom_components."""


@pytest.fixture
async def time_zone(hass: HomeAssistant) -> None:
    """Alarm times are local; use a zone where UTC is a different day at night."""
    await hass.config.async_set_time_zone("Europe/Warsaw")


def make_entry(alarms: dict[str, dict[str, Any]] | None = None) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        version=3,
        unique_id=PHONE_ID,
        title="John iPhone",
        data={
            "phone_id": PHONE_ID,
            "phone_name": "John iPhone",
            "mobile_app_device_id": None,
            "sync_disabled_alarms": True,
        },
        options={"alarms": alarms or {}},
    )


@pytest.fixture
async def entry(hass: HomeAssistant, time_zone: None) -> MockConfigEntry:
    """A set-up phone with the 07:00 "Wake" alarm."""
    config_entry = make_entry({ALARM_ID: alarm_payload()})
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry
