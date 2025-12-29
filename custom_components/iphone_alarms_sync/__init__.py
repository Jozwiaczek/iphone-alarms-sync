from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_ALARM_ID,
    CONF_ALARMS,
    CONF_EVENT,
    CONF_LABEL,
    CONF_MOBILE_APP_DEVICE_ID,
    CONF_PHONE_ID,
    CONF_PHONE_NAME,
    DOMAIN,
    EVENT_ALARM_EVENT,
    PLATFORMS,
)
from .coordinator import (
    IPhoneAlarmsSyncConfigEntry,
    IPhoneAlarmsSyncCoordinator,
    IPhoneAlarmsSyncData,
)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {})

    async def handle_sync_alarms(call: ServiceCall) -> None:
        phone_id = call.data[CONF_PHONE_ID]
        alarms = call.data[CONF_ALARMS]

        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            return

        entry = entries[0]
        if not hasattr(entry, "runtime_data") or not entry.runtime_data:
            return
        coordinator = entry.runtime_data.coordinator
        phone = coordinator.get_phone(phone_id)
        if not phone:
            return

        device_registry = dr.async_get(hass)
        phone_device = device_registry.async_get_device(
            identifiers={(DOMAIN, phone_id)}
        )

        if not phone_device:
            phone_device = device_registry.async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={(DOMAIN, phone_id)},
                name=phone.phone_name,
                via_device=(
                    (DOMAIN, phone.mobile_app_device_id)
                    if phone.mobile_app_device_id
                    else None
                ),
            )

        coordinator.sync_alarms(phone_id, alarms)
        await coordinator.async_request_refresh()

        for alarm_dict in alarms:
            alarm_id = alarm_dict[CONF_ALARM_ID]
            device_registry.async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={(DOMAIN, phone_id, alarm_id)},
                name=f"{phone.phone_name} {alarm_dict.get(CONF_LABEL, alarm_id)}",
                via_device=(DOMAIN, phone_id),
            )

        await hass.config_entries.async_reload(entry.entry_id)

    async def handle_report_alarm_event(call: ServiceCall) -> None:
        phone_id = call.data[CONF_PHONE_ID]
        alarm_id = call.data[CONF_ALARM_ID]
        event = call.data[CONF_EVENT]

        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            return

        entry = entries[0]
        if not hasattr(entry, "runtime_data") or not entry.runtime_data:
            return
        coordinator = entry.runtime_data.coordinator
        event_obj = coordinator.report_alarm_event(phone_id, alarm_id, event)
        await coordinator.async_request_refresh()

        hass.bus.async_fire(
            EVENT_ALARM_EVENT,
            {
                "phone_id": phone_id,
                "alarm_id": alarm_id,
                "event": event,
                "event_id": event_obj.event_id,
                "occurred_at": event_obj.occurred_at,
            },
        )

        device_registry = dr.async_get(hass)
        device = device_registry.async_get_device(
            identifiers={(DOMAIN, phone_id, alarm_id)}
        )
        if device:
            hass.bus.async_fire(
                f"{DOMAIN}_{event}",
                {
                    "device_id": device.id,
                },
            )

    hass.services.async_register(DOMAIN, "sync_alarms", handle_sync_alarms)
    hass.services.async_register(
        DOMAIN, "report_alarm_event", handle_report_alarm_event
    )

    return True


async def async_migrate_entry(
    hass: HomeAssistant, config_entry: IPhoneAlarmsSyncConfigEntry
) -> bool:
    if config_entry.version == 1:
        if CONF_PHONE_ID in config_entry.data:
            phone_id = config_entry.data[CONF_PHONE_ID]
            phone_name = config_entry.data.get(CONF_PHONE_NAME, phone_id)
            mobile_app_device_id = config_entry.data.get(CONF_MOBILE_APP_DEVICE_ID)
            alarms_data = config_entry.options.get(CONF_ALARMS, {})

            phones_dict = {
                phone_id: {
                    CONF_PHONE_ID: phone_id,
                    CONF_PHONE_NAME: phone_name,
                    CONF_MOBILE_APP_DEVICE_ID: mobile_app_device_id,
                    "alarms": alarms_data,
                }
            }

            other_entries = [
                e
                for e in hass.config_entries.async_entries(DOMAIN)
                if e.entry_id != config_entry.entry_id and CONF_PHONE_ID in e.data
            ]

            for other_entry in other_entries:
                other_phone_id = other_entry.data[CONF_PHONE_ID]
                other_phone_name = other_entry.data.get(CONF_PHONE_NAME, other_phone_id)
                other_mobile_app_device_id = other_entry.data.get(
                    CONF_MOBILE_APP_DEVICE_ID
                )
                other_alarms_data = other_entry.options.get(CONF_ALARMS, {})

                if other_phone_id not in phones_dict:
                    phones_dict[other_phone_id] = {
                        CONF_PHONE_ID: other_phone_id,
                        CONF_PHONE_NAME: other_phone_name,
                        CONF_MOBILE_APP_DEVICE_ID: other_mobile_app_device_id,
                        "alarms": other_alarms_data,
                    }

            new_data: dict[str, Any] = {}
            new_options = {"phones": phones_dict}

            hass.config_entries.async_update_entry(
                config_entry, data=new_data, options=new_options, version=2
            )

            for other_entry in other_entries:
                await hass.config_entries.async_remove(other_entry.entry_id)

    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: IPhoneAlarmsSyncConfigEntry
) -> bool:
    coordinator = IPhoneAlarmsSyncCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = IPhoneAlarmsSyncData(coordinator=coordinator)

    device_registry = dr.async_get(hass)
    phones = coordinator.get_all_phones()
    for phone_id, phone in phones.items():
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, phone_id)},
            name=phone.phone_name,
            via_device=(
                (DOMAIN, phone.mobile_app_device_id)
                if phone.mobile_app_device_id
                else None
            ),
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: IPhoneAlarmsSyncConfigEntry
) -> bool:
    unload_ok: bool = await hass.config_entries.async_unload_platforms(  # type: ignore[no-any-return]
        entry, PLATFORMS
    )
    return unload_ok
