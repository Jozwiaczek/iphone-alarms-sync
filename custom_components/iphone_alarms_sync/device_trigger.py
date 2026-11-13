from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import CONF_TYPE
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.trigger import TriggerInfo
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    EVENT_BEDTIME_STARTS,
    EVENT_GOES_OFF,
    EVENT_SNOOZED,
    EVENT_STOPPED,
    EVENT_WAKING_UP,
    EVENT_WIND_DOWN_STARTS,
)

ALARM_TRIGGER_TYPES = {EVENT_GOES_OFF, EVENT_SNOOZED, EVENT_STOPPED}
SLEEP_TRIGGER_TYPES = {EVENT_BEDTIME_STARTS, EVENT_WAKING_UP, EVENT_WIND_DOWN_STARTS}

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {vol.Required(CONF_TYPE): vol.In(ALARM_TRIGGER_TYPES | SLEEP_TRIGGER_TYPES)}
)


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, Any]]:
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)

    if device is None:
        return []

    # Alarm devices have (DOMAIN, phone_id, alarm_id) identifiers.
    is_phone = any(i[0] == DOMAIN and len(i) == 2 for i in device.identifiers)
    trigger_types = (
        ALARM_TRIGGER_TYPES | SLEEP_TRIGGER_TYPES if is_phone else ALARM_TRIGGER_TYPES
    )

    entry = hass.config_entries.async_get_entry(device.config_entry_id)
    if entry is None or entry.domain != DOMAIN:
        return []
    return [
        {
            "platform": "device",
            "domain": DOMAIN,
            "device_id": device_id,
            "type": trigger_type,
        }
        for trigger_type in trigger_types
    ]


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: Any,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    event_config = event_trigger.TRIGGER_SCHEMA(
        {
            event_trigger.CONF_PLATFORM: "event",
            event_trigger.CONF_EVENT_TYPE: f"{DOMAIN}_{config['type']}",
            event_trigger.CONF_EVENT_DATA: {
                "device_id": config["device_id"],
            },
        }
    )
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )
