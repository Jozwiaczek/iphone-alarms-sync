from __future__ import annotations

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_ALARM_ID,
    CONF_ALARMS,
    CONF_EVENT,
    CONF_PHONE_ID,
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
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: IPhoneAlarmsSyncConfigEntry
) -> bool:
    coordinator = IPhoneAlarmsSyncCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = IPhoneAlarmsSyncData(coordinator=coordinator)

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, coordinator.phone_id)},
        name=coordinator.phone_name,
        via_device=(
            (DOMAIN, coordinator.mobile_app_device_id)
            if coordinator.mobile_app_device_id
            else None
        ),
    )

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    async def handle_sync_alarms(call: ServiceCall) -> None:
        phone_id = call.data[CONF_PHONE_ID]
        alarms = call.data[CONF_ALARMS]

        for entry in hass.config_entries.async_entries(DOMAIN):
            if entry.data[CONF_PHONE_ID] == phone_id:
                coordinator = entry.runtime_data.coordinator
                device_registry = dr.async_get(hass)
                phone_device = device_registry.async_get_device(
                    identifiers={(DOMAIN, phone_id)}
                )

                coordinator.sync_alarms(alarms)
                await coordinator.async_request_refresh()

                for alarm_dict in alarms:
                    alarm_id = alarm_dict[CONF_ALARM_ID]
                    device_registry.async_get_or_create(
                        config_entry_id=entry.entry_id,
                        identifiers={(DOMAIN, phone_id, alarm_id)},
                        name=(
                            f"{coordinator.phone_name} "
                            f"{alarm_dict.get('label', alarm_id)}"
                        ),
                        via_device=(DOMAIN, phone_id) if phone_device else None,
                    )

                for platform in PLATFORMS:
                    await hass.config_entries.async_reload(entry.entry_id)
                break

    async def handle_report_alarm_event(call: ServiceCall) -> None:
        phone_id = call.data[CONF_PHONE_ID]
        alarm_id = call.data[CONF_ALARM_ID]
        event = call.data[CONF_EVENT]

        for entry in hass.config_entries.async_entries(DOMAIN):
            if entry.data[CONF_PHONE_ID] == phone_id:
                coordinator = entry.runtime_data.coordinator
                event_obj = coordinator.report_alarm_event(alarm_id, event)
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
                break

    hass.services.async_register(DOMAIN, "sync_alarms", handle_sync_alarms)
    hass.services.async_register(
        DOMAIN, "report_alarm_event", handle_report_alarm_event
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: IPhoneAlarmsSyncConfigEntry
) -> bool:
    unload_ok: bool = await hass.config_entries.async_unload_platforms(  # type: ignore[no-any-return]
        entry, PLATFORMS
    )
    if unload_ok:
        hass.services.async_remove(DOMAIN, "sync_alarms")
        hass.services.async_remove(DOMAIN, "report_alarm_event")
    return unload_ok

