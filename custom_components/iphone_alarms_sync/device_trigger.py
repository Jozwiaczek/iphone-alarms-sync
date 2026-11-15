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
    ALARM_EVENTS,
    DOMAIN,
    SLEEP_EVENTS,
    TRIGGER_SUBTYPE_ALARM,
    TRIGGER_SUBTYPE_ANY,
    TRIGGER_SUBTYPE_WAKEUP,
)

CONF_SUBTYPE = "subtype"

# As in the iOS Alarm automation: "Any" or "Wake-Up" on the phone.
PHONE_ALARM_SUBTYPES = (TRIGGER_SUBTYPE_ANY, TRIGGER_SUBTYPE_WAKEUP)

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(ALARM_EVENTS + SLEEP_EVENTS),
        # Optional: phone triggers saved before subtypes fire for Any and Wake-Up.
        vol.Optional(CONF_SUBTYPE): vol.In(
            PHONE_ALARM_SUBTYPES + (TRIGGER_SUBTYPE_ALARM,)
        ),
    }
)


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, Any]]:
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)

    if device is None:
        return []

    entry = hass.config_entries.async_get_entry(device.config_entry_id)
    if entry is None or entry.domain != DOMAIN:
        return []

    # Alarm devices have (DOMAIN, phone_id, alarm_id) identifiers.
    is_phone = any(i[0] == DOMAIN and len(i) == 2 for i in device.identifiers)
    base = {"platform": "device", "domain": DOMAIN, "device_id": device_id}
    if not is_phone:
        return [
            {**base, CONF_TYPE: t, CONF_SUBTYPE: TRIGGER_SUBTYPE_ALARM}
            for t in ALARM_EVENTS
        ]
    return [
        {**base, CONF_TYPE: t, CONF_SUBTYPE: s}
        for s in PHONE_ALARM_SUBTYPES
        for t in ALARM_EVENTS
    ] + [{**base, CONF_TYPE: t} for t in SLEEP_EVENTS]


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: Any,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    event_config = event_trigger.TRIGGER_SCHEMA(
        {
            event_trigger.CONF_PLATFORM: "event",
            event_trigger.CONF_EVENT_TYPE: f"{DOMAIN}_{config[CONF_TYPE]}",
            # Event data must contain these keys, so a missing subtype matches all.
            event_trigger.CONF_EVENT_DATA: {
                k: config[k] for k in ("device_id", CONF_SUBTYPE) if k in config
            },
        }
    )
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )
