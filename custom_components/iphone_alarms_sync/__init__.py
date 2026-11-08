from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, cast

from homeassistant.const import STATE_HOME, STATE_UNAVAILABLE, STATE_UNKNOWN, Platform
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import (
    async_track_point_in_time,
    async_track_time_interval,
)
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .binary_sensor import _create_binary_sensor_entities
from .const import (
    CONF_ALARM_ID,
    CONF_ALARMS,
    CONF_EVENT,
    CONF_LABEL,
    CONF_MISSED_EVENT_ONLY_HOME,
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
    MISSED_EVENT_GRACE,
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
from .utils import (
    calculate_next_alarm_datetime,
    calculate_next_occurrence,
    extract_alarm_uuid,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


def _mobile_app_device_id(
    device_registry: dr.DeviceRegistry, phone: PhoneData
) -> str | None:
    """The phone's mobile_app device id, if that device still exists."""
    device_id = phone.mobile_app_device_id
    if device_id and device_registry.async_get(device_id):
        return device_id
    return None


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


# Where users find the IDs their shortcuts need.
_OPTIONS = "Settings → Devices & services → iPhone Alarms Sync → Configure"


def _require_event(call: ServiceCall, allowed: tuple[str, ...]) -> str:
    event = call.data.get(CONF_EVENT)
    if event not in allowed:
        raise ServiceValidationError(
            f"Unknown event '{event or ''}'. In the shortcut, set Event Type "
            f"Number to a number from its list. Valid events: {', '.join(allowed)}"
        )
    return cast(str, event)


def _resolve_call(
    hass: HomeAssistant, call: ServiceCall
) -> tuple[IPhoneAlarmsSyncConfigEntry, IPhoneAlarmsSyncCoordinator, PhoneData]:
    """Find the loaded entry for phone_id or raise an error the shortcut shows."""
    phone_id = call.data.get(CONF_PHONE_ID)
    if not phone_id:
        raise ServiceValidationError(
            f"Phone ID is missing. Copy it from {_OPTIONS} → Sync Shortcut Setup "
            "into the first Text step of this shortcut."
        )
    entry = next(
        (
            e
            for e in hass.config_entries.async_entries(DOMAIN)
            if e.unique_id == phone_id
        ),
        None,
    )
    if entry is None:
        raise ServiceValidationError(
            f"Unknown Phone ID '{phone_id}'. Copy the Phone ID from {_OPTIONS} → "
            "Sync Shortcut Setup into the first Text step of this shortcut."
        )
    if not getattr(entry, "runtime_data", None):
        raise HomeAssistantError(
            f"iPhone Alarms Sync for '{phone_id}' is not loaded. "
            "Check it in Settings → Devices & services."
        )
    coordinator = entry.runtime_data.coordinator
    phone = coordinator.get_phone()
    if phone is None:
        raise HomeAssistantError(
            f"iPhone Alarms Sync for '{phone_id}' has no data. "
            "Reload it in Settings → Devices & services."
        )
    # The phone reached Home Assistant, so the shortcut chain works again.
    ir.async_delete_issue(hass, DOMAIN, _no_data_issue_id(entry))
    ir.async_delete_issue(hass, DOMAIN, _missed_event_issue_id(entry))
    return entry, coordinator, phone


def _no_data_issue_id(entry: IPhoneAlarmsSyncConfigEntry) -> str:
    return f"no_data_{entry.entry_id}"


def _missed_event_issue_id(entry: IPhoneAlarmsSyncConfigEntry) -> str:
    return f"missed_event_{entry.entry_id}"


def _phone_away(hass: HomeAssistant, phone: PhoneData) -> bool:
    """Whether the phone's Home Assistant app tracker says it is not at home."""
    if not phone.mobile_app_device_id:
        return False
    entity_registry = er.async_get(hass)
    for reg_entry in er.async_entries_for_device(
        entity_registry, phone.mobile_app_device_id
    ):
        if reg_entry.domain == Platform.DEVICE_TRACKER:
            # A disabled or unknown tracker must not silence the issue.
            state = hass.states.get(reg_entry.entity_id)
            return state is not None and state.state not in (
                STATE_HOME,
                STATE_UNKNOWN,
                STATE_UNAVAILABLE,
            )
    return False


@callback
def _async_check_missed_event(
    hass: HomeAssistant,
    entry: IPhoneAlarmsSyncConfigEntry,
    alarm_at: datetime,
    alarm_id: str | None,
) -> None:
    """Raise a repair issue when an alarm rang but its "goes off" never arrived."""
    phone = entry.runtime_data.coordinator.get_phone()
    alarm = phone.alarms.get(alarm_id) if phone and alarm_id else None
    if phone is None or alarm is None:
        return
    # Only expect an event when this phone reports "any alarm" or this very alarm.
    if not (phone.any_last_event_goes_off_at or alarm.last_event_goes_off_at):
        return
    # iOS turns a one-time alarm off after it rings, but HA learns that only on the
    # next sync, so check only its first ring after the last sync.
    synced_at = dt_util.parse_datetime(phone.synced_at or "")
    if not (alarm.repeats and alarm.repeat_days) and (
        synced_at is None or calculate_next_occurrence(alarm, synced_at) != alarm_at
    ):
        return
    # Anything from the phone since the alarm (an event, or a sync that may also have
    # created this alarm) proves the connection; _resolve_call clears the issue too.
    last = entry.runtime_data.coordinator.last_activity_at()
    issue_id = _missed_event_issue_id(entry)
    # iOS may run the automation a few seconds before the scheduled minute.
    if last is not None and last >= alarm_at - timedelta(minutes=1):
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return
    # A phone that reaches HA only at home is expected to miss events elsewhere.
    if entry.data.get(CONF_MISSED_EVENT_ONLY_HOME) and _phone_away(hass, phone):
        return
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="missed_event",
        translation_placeholders={
            "phone_name": entry.title,
            "time": dt_util.as_local(alarm_at).strftime("%H:%M"),
        },
        learn_more_url=DOCS_TROUBLESHOOTING_URL,
    )


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
                "The shortcut sent no valid alarm list (each alarm needs an "
                f"'alarm_id'). Re-import it from {_OPTIONS} → Sync Shortcut Setup."
            )
        entry, coordinator, phone = _resolve_call(hass, call)
        phone_id = call.data[CONF_PHONE_ID]

        device_registry = dr.async_get(hass)
        phone_device = device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, phone_id)},
            name=phone.phone_name,
            via_device_id=_mobile_app_device_id(device_registry, phone),
        )

        for alarm_dict in alarms:
            original_alarm_id = alarm_dict[CONF_ALARM_ID]
            alarm_dict[CONF_ALARM_ID] = extract_alarm_uuid(original_alarm_id)

        new_alarm_ids = coordinator.sync_alarms(alarms)

        for alarm_dict in alarms:
            alarm_id = alarm_dict[CONF_ALARM_ID]
            if alarm_id not in phone.alarms:  # filtered out (disabled, not synced)
                continue
            device_registry.async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={(DOMAIN, phone_id, alarm_id)},
                name=f"{phone.phone_name} {alarm_dict.get(CONF_LABEL, alarm_id)}",
                via_device_id=phone_device.id,
            )

        # Alarms gone from the phone take their device and entities with them.
        for device in dr.async_entries_for_config_entry(
            device_registry, entry.entry_id
        ):
            for identifier in device.identifiers:
                if (
                    len(identifier) == 3
                    and identifier[:2] == (DOMAIN, phone_id)
                    and identifier[2] not in phone.alarms
                ):
                    device_registry.async_remove_device(device.id)
                    break

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
            raise ServiceValidationError(
                f"Alarm ID is missing. Copy it from {_OPTIONS} → Event Shortcuts "
                "Setup into the second Text step of this shortcut."
            )
        alarm_id = extract_alarm_uuid(call.data[CONF_ALARM_ID])
        entry, coordinator, phone = _resolve_call(hass, call)
        phone_id = call.data[CONF_PHONE_ID]

        alarm = coordinator.get_alarm(alarm_id)
        if alarm is None:
            raise ServiceValidationError(
                f"Unknown Alarm ID '{alarm_id}'. Run the Sync shortcut, then copy "
                f"the Alarm ID from {_OPTIONS} → Event Shortcuts Setup."
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
        device = device_registry.async_get_device_by_identifier(
            (DOMAIN, phone_id, alarm_id), entry.entry_id
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
            device = device_registry.async_get_device_by_identifier(
                (DOMAIN, phone_id), entry.entry_id
            )
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
            device = device_registry.async_get_device_by_identifier(
                (DOMAIN, phone_id), entry.entry_id
            )
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
            device = device_registry.async_get_device_by_identifier(
                (DOMAIN, phone_id), entry.entry_id
            )
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
            device = device_registry.async_get_device_by_identifier(
                (DOMAIN, phone_id), entry.entry_id
            )
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
            device = device_registry.async_get_device_by_identifier(
                (DOMAIN, phone_id), entry.entry_id
            )
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
        phone_device = device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, phone.phone_id)},
            name=phone.phone_name,
            via_device_id=_mobile_app_device_id(device_registry, phone),
        )
        # Entities only describe alarm devices; link them to the phone here.
        for alarm_id, alarm in phone.alarms.items():
            device_registry.async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={(DOMAIN, phone.phone_id, alarm_id)},
                name=f"{phone.phone_name} {alarm.label}",
                via_device_id=phone_device.id,
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

    check_at: datetime | None = None
    cancel_check: CALLBACK_TYPE | None = None

    @callback
    def _schedule_missed_check() -> None:
        nonlocal check_at, cancel_check
        # A pending check owns the alarm that just rang; it reschedules itself.
        if check_at is not None and check_at <= dt_util.utcnow():
            return
        phone = coordinator.get_phone()
        # Look back one grace period so an alarm that rang a moment ago (a second
        # alarm minutes after the first, or an HA restart) still gets its check.
        next_at, alarm_id = (
            calculate_next_alarm_datetime(phone, dt_util.utcnow() - MISSED_EVENT_GRACE)
            if phone
            else (None, None)
        )
        if next_at == check_at:
            return
        if cancel_check:
            cancel_check()
            cancel_check = None
        check_at = next_at
        if next_at is None:
            return

        @callback
        def _check(_now: datetime) -> None:
            nonlocal check_at, cancel_check
            check_at = cancel_check = None
            # The next alarm is already later, so check the one remembered here.
            _async_check_missed_event(hass, entry, next_at, alarm_id)
            _schedule_missed_check()

        _LOGGER.debug("Next missed-event check for alarm at %s", next_at)
        cancel_check = async_track_point_in_time(
            hass, _check, next_at + MISSED_EVENT_GRACE
        )

    @callback
    def _cancel_missed_check() -> None:
        if cancel_check:
            cancel_check()
        ir.async_delete_issue(hass, DOMAIN, _missed_event_issue_id(entry))

    _schedule_missed_check()
    entry.async_on_unload(coordinator.async_add_listener(_schedule_missed_check))
    entry.async_on_unload(_cancel_missed_check)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: IPhoneAlarmsSyncConfigEntry
) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    return bool(unload_ok)
