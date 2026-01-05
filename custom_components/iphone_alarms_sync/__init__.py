from __future__ import annotations

import logging
from typing import Any, cast

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .binary_sensor import _create_binary_sensor_entities
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
    EVENT_BEDTIME_STARTS,
    EVENT_WAKING_UP,
    EVENT_WIND_DOWN_STARTS,
    PLATFORMS,
)
from .coordinator import (
    IPhoneAlarmsSyncConfigEntry,
    IPhoneAlarmsSyncCoordinator,
    IPhoneAlarmsSyncData,
)
from .number import _create_number_entities
from .sensor import (
    _create_alarm_sensor_entities,
    _create_phone_event_sensor_entities,
)
from .utils import extract_alarm_uuid

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


def _get_via_device_from_device_id(
    device_registry: dr.DeviceRegistry, device_id: str | None
) -> tuple[str, ...] | None:
    if not device_id:
        return None
    device = device_registry.async_get(device_id)
    if not device or not device.identifiers:
        return None
    identifier = next(iter(device.identifiers))
    return cast(tuple[str, ...], identifier)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {})

    async def handle_sync_alarms(call: ServiceCall) -> None:
        phone_id = call.data[CONF_PHONE_ID]
        alarms = call.data[CONF_ALARMS]

        entries = hass.config_entries.async_entries(DOMAIN)
        entry = None
        for e in entries:
            if e.unique_id == phone_id:
                entry = e
                break

        if not entry:
            return

        if not hasattr(entry, "runtime_data") or not entry.runtime_data:
            return
        coordinator = entry.runtime_data.coordinator
        phone = coordinator.get_phone()
        if not phone:
            return

        device_registry = dr.async_get(hass)
        phone_device = device_registry.async_get_device(
            identifiers={(DOMAIN, phone_id)}
        )

        via_device = _get_via_device_from_device_id(
            device_registry, phone.mobile_app_device_id
        )

        if not phone_device:
            phone_device = device_registry.async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={(DOMAIN, phone_id)},
                name=phone.phone_name,
                via_device=via_device,
            )
        else:
            current_via_device = (
                _get_via_device_from_device_id(
                    device_registry,
                    phone_device.via_device_id,
                )
                if phone_device.via_device_id
                else None
            )
            if current_via_device != via_device:
                device_registry.async_update_device(
                    phone_device.id,
                    via_device=via_device,
                )

        for alarm_dict in alarms:
            original_alarm_id = alarm_dict[CONF_ALARM_ID]
            alarm_dict[CONF_ALARM_ID] = extract_alarm_uuid(original_alarm_id)

        new_alarm_ids, has_changes = coordinator.sync_alarms(alarms)

        for alarm_dict in alarms:
            alarm_id = alarm_dict[CONF_ALARM_ID]
            device_registry.async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={(DOMAIN, phone_id, alarm_id)},
                name=f"{phone.phone_name} {alarm_dict.get(CONF_LABEL, alarm_id)}",
                via_device=(DOMAIN, phone_id),
            )

        if new_alarm_ids:
            entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
            for alarm_id in new_alarm_ids:
                if sensor_add := entry_data.get("sensor_add_entities"):
                    sensor_entities = _create_alarm_sensor_entities(
                        coordinator, entry, phone_id, alarm_id
                    )
                    sensor_add(sensor_entities)
                if binary_sensor_add := entry_data.get("binary_sensor_add_entities"):
                    binary_sensor_entities = _create_binary_sensor_entities(
                        coordinator, entry, phone_id, alarm_id
                    )
                    binary_sensor_add(binary_sensor_entities)
                if number_add := entry_data.get("number_add_entities"):
                    number_entities = _create_number_entities(
                        coordinator, entry, phone_id, alarm_id
                    )
                    number_add(number_entities)

        if has_changes:
            phone = coordinator.get_phone()
            if phone:
                coordinator.async_set_updated_data(phone)

    async def handle_report_alarm_event(call: ServiceCall) -> None:
        phone_id = call.data[CONF_PHONE_ID]
        alarm_id = extract_alarm_uuid(call.data[CONF_ALARM_ID])
        event = call.data[CONF_EVENT]

        entries = hass.config_entries.async_entries(DOMAIN)
        entry = None
        for e in entries:
            if e.unique_id == phone_id:
                entry = e
                break

        if not entry:
            return

        if not hasattr(entry, "runtime_data") or not entry.runtime_data:
            return
        coordinator = entry.runtime_data.coordinator
        phone = coordinator.get_phone()
        if not phone:
            return

        alarm = coordinator.get_alarm(alarm_id)
        was_first_event = False
        if alarm:
            if event == "goes_off" and not alarm.last_event_goes_off_at:
                was_first_event = True
            elif event == "snoozed" and not alarm.last_event_snoozed_at:
                was_first_event = True
            elif event == "stopped" and not alarm.last_event_stopped_at:
                was_first_event = True

        event_obj = coordinator.report_alarm_event(alarm_id, event)
        phone = coordinator.get_phone()
        if phone:
            coordinator.async_set_updated_data(phone)

        if was_first_event:
            entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
            if sensor_add := entry_data.get("sensor_add_entities"):
                sensor_entities = _create_alarm_sensor_entities(
                    coordinator, entry, phone_id, alarm_id
                )
                target_key = f"last_event_{event}_at"
                new_entities = [
                    e for e in sensor_entities if e.entity_description.key == target_key
                ]
                if new_entities:
                    sensor_add(new_entities)

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

    async def handle_report_device_event(call: ServiceCall) -> None:
        phone_id = call.data.get(CONF_PHONE_ID)
        event = call.data.get(CONF_EVENT)

        if not phone_id or not event:
            _LOGGER.error(
                "Missing required fields in report_device_event: phone_id=%s, event=%s",
                phone_id,
                event,
            )
            return

        entries = hass.config_entries.async_entries(DOMAIN)
        entry = None
        for e in entries:
            if e.unique_id == phone_id:
                entry = e
                break

        if not entry:
            return

        if not hasattr(entry, "runtime_data") or not entry.runtime_data:
            return
        coordinator = entry.runtime_data.coordinator
        phone = coordinator.get_phone()
        if not phone:
            return

        if event.startswith("wakeup_"):
            event_name = event.replace("wakeup_", "")
            was_first_event = False
            if event_name == "goes_off" and not phone.wakeup_last_event_goes_off_at:
                was_first_event = True
            elif event_name == "snoozed" and not phone.wakeup_last_event_snoozed_at:
                was_first_event = True
            elif event_name == "stopped" and not phone.wakeup_last_event_stopped_at:
                was_first_event = True

            event_obj = coordinator.report_wakeup_event(event_name)
            phone = coordinator.get_phone()
            if phone:
                coordinator.async_set_updated_data(phone)

            if was_first_event:
                entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
                if sensor_add := entry_data.get("sensor_add_entities"):
                    sensor_entities = _create_phone_event_sensor_entities(
                        coordinator, entry, phone_id
                    )
                    target_key = f"wakeup_last_event_{event_name}_at"
                    new_entities = [
                        e
                        for e in sensor_entities
                        if e.entity_description.key == target_key
                    ]
                    if new_entities:
                        sensor_add(new_entities)

            hass.bus.async_fire(
                EVENT_ALARM_EVENT,
                {
                    "phone_id": phone_id,
                    "alarm_id": "wakeup",
                    "event": event_name,
                    "event_id": event_obj.event_id,
                    "occurred_at": event_obj.occurred_at,
                },
            )

            device_registry = dr.async_get(hass)
            device = device_registry.async_get_device(identifiers={(DOMAIN, phone_id)})
            if device:
                hass.bus.async_fire(
                    f"{DOMAIN}_{event_name}",
                    {
                        "device_id": device.id,
                    },
                )

        elif event.startswith("any_"):
            event_name = event.replace("any_", "")
            was_first_event = False
            if event_name == "goes_off" and not phone.any_last_event_goes_off_at:
                was_first_event = True
            elif event_name == "snoozed" and not phone.any_last_event_snoozed_at:
                was_first_event = True
            elif event_name == "stopped" and not phone.any_last_event_stopped_at:
                was_first_event = True

            event_obj = coordinator.report_any_event(event_name)
            phone = coordinator.get_phone()
            if phone:
                coordinator.async_set_updated_data(phone)

            if was_first_event:
                entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
                if sensor_add := entry_data.get("sensor_add_entities"):
                    sensor_entities = _create_phone_event_sensor_entities(
                        coordinator, entry, phone_id
                    )
                    target_key = f"any_last_event_{event_name}_at"
                    new_entities = [
                        e
                        for e in sensor_entities
                        if e.entity_description.key == target_key
                    ]
                    if new_entities:
                        sensor_add(new_entities)

            hass.bus.async_fire(
                EVENT_ALARM_EVENT,
                {
                    "phone_id": phone_id,
                    "alarm_id": "any",
                    "event": event_name,
                    "event_id": event_obj.event_id,
                    "occurred_at": event_obj.occurred_at,
                },
            )

            device_registry = dr.async_get(hass)
            device = device_registry.async_get_device(identifiers={(DOMAIN, phone_id)})
            if device:
                hass.bus.async_fire(
                    f"{DOMAIN}_{event_name}",
                    {
                        "device_id": device.id,
                    },
                )

        elif event == "bedtime_starts":
            was_first_event = not phone.bedtime_last_event_at

            event_obj = coordinator.report_bedtime_event()
            phone = coordinator.get_phone()
            if phone:
                coordinator.async_set_updated_data(phone)

            if was_first_event:
                entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
                if sensor_add := entry_data.get("sensor_add_entities"):
                    sensor_entities = _create_phone_event_sensor_entities(
                        coordinator, entry, phone_id
                    )
                    target_key = "bedtime_last_event_at"
                    new_entities = [
                        e
                        for e in sensor_entities
                        if e.entity_description.key == target_key
                    ]
                    if new_entities:
                        sensor_add(new_entities)

            hass.bus.async_fire(
                EVENT_ALARM_EVENT,
                {
                    "phone_id": phone_id,
                    "alarm_id": "bedtime",
                    "event": EVENT_BEDTIME_STARTS,
                    "event_id": event_obj.event_id,
                    "occurred_at": event_obj.occurred_at,
                },
            )

            device_registry = dr.async_get(hass)
            device = device_registry.async_get_device(identifiers={(DOMAIN, phone_id)})
            if device:
                hass.bus.async_fire(
                    f"{DOMAIN}_{EVENT_BEDTIME_STARTS}",
                    {
                        "device_id": device.id,
                    },
                )

        elif event == "waking_up":
            was_first_event = not phone.waking_up_last_event_at

            event_obj = coordinator.report_waking_up_event()
            phone = coordinator.get_phone()
            if phone:
                coordinator.async_set_updated_data(phone)

            if was_first_event:
                entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
                if sensor_add := entry_data.get("sensor_add_entities"):
                    sensor_entities = _create_phone_event_sensor_entities(
                        coordinator, entry, phone_id
                    )
                    target_key = "waking_up_last_event_at"
                    new_entities = [
                        e
                        for e in sensor_entities
                        if e.entity_description.key == target_key
                    ]
                    if new_entities:
                        sensor_add(new_entities)

            hass.bus.async_fire(
                EVENT_ALARM_EVENT,
                {
                    "phone_id": phone_id,
                    "alarm_id": "waking_up",
                    "event": EVENT_WAKING_UP,
                    "event_id": event_obj.event_id,
                    "occurred_at": event_obj.occurred_at,
                },
            )

            device_registry = dr.async_get(hass)
            device = device_registry.async_get_device(identifiers={(DOMAIN, phone_id)})
            if device:
                hass.bus.async_fire(
                    f"{DOMAIN}_{EVENT_WAKING_UP}",
                    {
                        "device_id": device.id,
                    },
                )

        elif event == "wind_down_starts":
            was_first_event = not phone.wind_down_last_event_at

            event_obj = coordinator.report_wind_down_event()
            phone = coordinator.get_phone()
            if phone:
                coordinator.async_set_updated_data(phone)

            if was_first_event:
                entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
                if sensor_add := entry_data.get("sensor_add_entities"):
                    sensor_entities = _create_phone_event_sensor_entities(
                        coordinator, entry, phone_id
                    )
                    target_key = "wind_down_last_event_at"
                    new_entities = [
                        e
                        for e in sensor_entities
                        if e.entity_description.key == target_key
                    ]
                    if new_entities:
                        sensor_add(new_entities)

            hass.bus.async_fire(
                EVENT_ALARM_EVENT,
                {
                    "phone_id": phone_id,
                    "alarm_id": "wind_down",
                    "event": EVENT_WIND_DOWN_STARTS,
                    "event_id": event_obj.event_id,
                    "occurred_at": event_obj.occurred_at,
                },
            )

            device_registry = dr.async_get(hass)
            device = device_registry.async_get_device(identifiers={(DOMAIN, phone_id)})
            if device:
                hass.bus.async_fire(
                    f"{DOMAIN}_{EVENT_WIND_DOWN_STARTS}",
                    {
                        "device_id": device.id,
                    },
                )

    hass.services.async_register(DOMAIN, "sync_alarms", handle_sync_alarms)
    hass.services.async_register(
        DOMAIN, "report_alarm_event", handle_report_alarm_event
    )
    hass.services.async_register(
        DOMAIN, "report_device_event", handle_report_device_event
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

    if config_entry.version == 2:
        phones_dict = config_entry.options.get("phones", {})
        if not phones_dict:
            hass.config_entries.async_update_entry(config_entry, version=3)
            return True

        first_phone_id = next(iter(phones_dict))
        first_phone = phones_dict[first_phone_id]

        hass.config_entries.async_update_entry(
            config_entry,
            unique_id=first_phone_id,
            title=first_phone[CONF_PHONE_NAME],
            data={
                CONF_PHONE_ID: first_phone_id,
                CONF_PHONE_NAME: first_phone[CONF_PHONE_NAME],
                CONF_MOBILE_APP_DEVICE_ID: first_phone.get(CONF_MOBILE_APP_DEVICE_ID),
            },
            options={"alarms": first_phone.get("alarms", {})},
            version=3,
        )

        for phone_id, phone_data in phones_dict.items():
            if phone_id == first_phone_id:
                continue

            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "import"},
                data={
                    CONF_PHONE_ID: phone_id,
                    CONF_PHONE_NAME: phone_data[CONF_PHONE_NAME],
                    CONF_MOBILE_APP_DEVICE_ID: phone_data.get(
                        CONF_MOBILE_APP_DEVICE_ID
                    ),
                },
            )
            if (
                hasattr(result, "type")
                and result.type == "create_entry"  # type: ignore[attr-defined]
                and hasattr(result, "result")
            ):
                new_entry = result.result  # type: ignore[attr-defined]
                hass.config_entries.async_update_entry(
                    new_entry,
                    options={"alarms": phone_data.get("alarms", {})},
                )

    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: IPhoneAlarmsSyncConfigEntry
) -> bool:
    coordinator = IPhoneAlarmsSyncCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = IPhoneAlarmsSyncData(coordinator=coordinator)

    device_registry = dr.async_get(hass)
    phone = coordinator.get_phone()
    if phone:
        via_device = _get_via_device_from_device_id(
            device_registry, phone.mobile_app_device_id
        )
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, phone.phone_id)},
            name=phone.phone_name,
            via_device=via_device,
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: IPhoneAlarmsSyncConfigEntry
) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    return bool(unload_ok)
