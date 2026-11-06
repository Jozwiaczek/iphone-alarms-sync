from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, cast

from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .binary_sensor import _create_binary_sensor_entities
from .const import (
    CONF_ALARM_ID,
    CONF_ALARMS,
    CONF_EVENT,
    CONF_LABEL,
    CONF_MOBILE_APP_DEVICE_ID,
    CONF_PHONE_ID,
    CONF_PHONE_NAME,
    DOCS_TROUBLESHOOTING_URL,
    DOMAIN,
    EVENT_ALARM_EVENT,
    EVENT_BEDTIME_STARTS,
    EVENT_GOES_OFF,
    EVENT_SNOOZED,
    EVENT_STOPPED,
    EVENT_WAKING_UP,
    EVENT_WIND_DOWN_STARTS,
    PLATFORMS,
    STALE_AFTER,
    STALE_CHECK_INTERVAL,
)
from .coordinator import (
    IPhoneAlarmsSyncConfigEntry,
    IPhoneAlarmsSyncCoordinator,
    IPhoneAlarmsSyncData,
    PhoneData,
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


ALARM_EVENTS = (EVENT_GOES_OFF, EVENT_SNOOZED, EVENT_STOPPED)
DEVICE_EVENTS = (
    *(f"wakeup_{e}" for e in ALARM_EVENTS),
    *(f"any_{e}" for e in ALARM_EVENTS),
    EVENT_BEDTIME_STARTS,
    EVENT_WAKING_UP,
    EVENT_WIND_DOWN_STARTS,
)


def _log_call(call: ServiceCall) -> None:
    # Logged before validation so a rejected call still shows it reached HA.
    _LOGGER.debug(
        "%s called for phone_id=%s", call.service, call.data.get(CONF_PHONE_ID)
    )


def _require_event(call: ServiceCall, allowed: tuple[str, ...]) -> str:
    event = call.data.get(CONF_EVENT)
    if event not in allowed:
        raise ServiceValidationError(
            f"Invalid event '{event}'. Expected one of: {', '.join(allowed)}"
        )
    return cast(str, event)


def _resolve_call(
    hass: HomeAssistant, call: ServiceCall
) -> tuple[IPhoneAlarmsSyncConfigEntry, IPhoneAlarmsSyncCoordinator, PhoneData]:
    """Find the loaded entry for phone_id or raise an error the shortcut shows."""
    phone_id = call.data.get(CONF_PHONE_ID)
    entry = next(
        (
            e
            for e in hass.config_entries.async_entries(DOMAIN)
            if phone_id and e.unique_id == phone_id
        ),
        None,
    )
    if entry is None:
        raise ServiceValidationError(
            f"Unknown phone_id '{phone_id}'. Copy the Phone ID from the "
            "iPhone Alarms Sync options into your shortcut."
        )
    if not getattr(entry, "runtime_data", None):
        raise HomeAssistantError(f"iPhone Alarms Sync for '{phone_id}' is not loaded")
    coordinator = entry.runtime_data.coordinator
    phone = coordinator.get_phone()
    if phone is None:
        raise HomeAssistantError(f"iPhone Alarms Sync for '{phone_id}' has no data")
    # The phone reached Home Assistant, so the shortcut chain works again.
    ir.async_delete_issue(hass, DOMAIN, _no_data_issue_id(entry))
    return entry, coordinator, phone


def _no_data_issue_id(entry: IPhoneAlarmsSyncConfigEntry) -> str:
    return f"no_data_{entry.entry_id}"


@callback
def _async_check_stale(hass: HomeAssistant, entry: IPhoneAlarmsSyncConfigEntry) -> None:
    """Raise a repair issue when the phone stopped sending data."""
    last = entry.runtime_data.coordinator.last_activity_at()
    issue_id = _no_data_issue_id(entry)
    if last is None or dt_util.utcnow() - last < STALE_AFTER:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="no_data",
        translation_placeholders={
            "phone_name": entry.title,
            "days": str((dt_util.utcnow() - last).days),
        },
        learn_more_url=DOCS_TROUBLESHOOTING_URL,
    )


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {})

    async def handle_sync_alarms(call: ServiceCall) -> None:
        _log_call(call)
        alarms = call.data.get(CONF_ALARMS)
        if not isinstance(alarms, list) or not all(
            isinstance(a, dict) and a.get(CONF_ALARM_ID) for a in alarms
        ):
            raise ServiceValidationError(
                "'alarms' must be a list of objects, each with an 'alarm_id'"
            )
        entry, coordinator, phone = _resolve_call(hass, call)
        phone_id = call.data[CONF_PHONE_ID]

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

        new_alarm_ids = coordinator.sync_alarms(alarms)

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

        # Always push: "Last Sync" changes on every call.
        coordinator.async_set_updated_data(phone)

    async def handle_report_alarm_event(call: ServiceCall) -> None:
        _log_call(call)
        event = _require_event(call, ALARM_EVENTS)
        if not call.data.get(CONF_ALARM_ID):
            raise ServiceValidationError("'alarm_id' is required")
        alarm_id = extract_alarm_uuid(call.data[CONF_ALARM_ID])
        entry, coordinator, phone = _resolve_call(hass, call)
        phone_id = call.data[CONF_PHONE_ID]

        alarm = coordinator.get_alarm(alarm_id)
        if alarm is None:
            raise ServiceValidationError(
                f"Unknown alarm_id '{alarm_id}'. Run the Sync shortcut first."
            )
        was_first_event = not getattr(alarm, f"last_event_{event}_at")

        event_obj = coordinator.report_alarm_event(alarm_id, event)
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
        _log_call(call)
        event = _require_event(call, DEVICE_EVENTS)
        entry, coordinator, phone = _resolve_call(hass, call)
        phone_id = call.data[CONF_PHONE_ID]

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

    @callback
    def _check_stale(_now: datetime | None = None) -> None:
        _async_check_stale(hass, entry)

    _check_stale()
    entry.async_on_unload(
        async_track_time_interval(hass, _check_stale, STALE_CHECK_INTERVAL)
    )
    entry.async_on_unload(
        lambda: ir.async_delete_issue(hass, DOMAIN, _no_data_issue_id(entry))
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: IPhoneAlarmsSyncConfigEntry
) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    return bool(unload_ok)
