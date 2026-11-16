"""Diagnostics for bug reports: the phone's stored and in-memory state."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.core import HomeAssistant

from .coordinator import IPhoneAlarmsSyncConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: IPhoneAlarmsSyncConfigEntry
) -> dict[str, Any]:
    coordinator = entry.runtime_data.coordinator
    return {
        # Stored and in-memory state side by side show when a change was not saved.
        "options": dict(entry.options),
        "phone": asdict(coordinator.phone),
        "events": [asdict(event) for event in coordinator.get_events()],
    }
