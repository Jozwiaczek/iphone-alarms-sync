from __future__ import annotations

from typing import Any

from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType, VolSchemaType

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
PHONE_IDENTIFIER_LENGTH = 2

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        "type": str,
    }
)


def _is_phone_device(device: dr.DeviceEntry) -> bool:
    for identifier in device.identifiers:
        if identifier[0] == DOMAIN:
            return len(identifier) == PHONE_IDENTIFIER_LENGTH
    return False


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, Any]]:
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)

    if device is None:
        return []

    is_phone = _is_phone_device(device)
    trigger_types = (
        ALARM_TRIGGER_TYPES | SLEEP_TRIGGER_TYPES if is_phone else ALARM_TRIGGER_TYPES
    )

    triggers = []
    for entry_id in device.config_entries:
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry and entry.domain == DOMAIN:
            for trigger_type in trigger_types:
                triggers.append(
                    {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": device_id,
                        "type": trigger_type,
                    }
                )
            break

    return triggers


async def async_get_trigger_capabilities(
    hass: HomeAssistant, config: ConfigType
) -> dict[str, VolSchemaType]:
    return {
        "extra_fields": event_trigger.TRIGGER_SCHEMA.schema,
    }


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: Any,
    trigger_info: dict[str, Any],
) -> callback.CALLBACK_TYPE:
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
