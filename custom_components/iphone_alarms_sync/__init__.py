from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import cast

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import (
    async_track_point_in_time,
    async_track_time_interval,
)
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ALARM_ID,
    CONF_ALARMS,
    CONF_EVENT,
    CONF_PHONE_ID,
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
    AlarmEvent,
    IPhoneAlarmsSyncConfigEntry,
    IPhoneAlarmsSyncCoordinator,
    IPhoneAlarmsSyncData,
    PhoneData,
)
from .utils import (
    calculate_next_alarm_datetime,
    calculate_next_occurrence,
    extract_alarm_uuid,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

ALARM_EVENTS = (EVENT_GOES_OFF, EVENT_SNOOZED, EVENT_STOPPED)
# Device event -> (scope reported as alarm_id, PhoneData field, event name).
DEVICE_EVENTS: dict[str, tuple[str, str, str]] = {
    **{f"wakeup_{e}": ("wakeup", f"wakeup_last_event_{e}_at", e) for e in ALARM_EVENTS},
    **{f"any_{e}": ("any", f"any_last_event_{e}_at", e) for e in ALARM_EVENTS},
    EVENT_BEDTIME_STARTS: ("bedtime", "bedtime_last_event_at", EVENT_BEDTIME_STARTS),
    EVENT_WAKING_UP: ("waking_up", "waking_up_last_event_at", EVENT_WAKING_UP),
    EVENT_WIND_DOWN_STARTS: (
        "wind_down",
        "wind_down_last_event_at",
        EVENT_WIND_DOWN_STARTS,
    ),
}

# Where users find the IDs their shortcuts need.
_OPTIONS = "Settings → Devices & services → iPhone Alarms Sync → Configure"


def _mobile_app_device_id(
    device_registry: dr.DeviceRegistry, phone: PhoneData
) -> str | None:
    """The phone's mobile_app device id, if that device still exists."""
    device_id = phone.mobile_app_device_id
    if device_id and device_registry.async_get(device_id):
        return device_id
    return None


@callback
def _async_update_devices(
    hass: HomeAssistant, entry: IPhoneAlarmsSyncConfigEntry, phone: PhoneData
) -> None:
    """Create the phone and alarm devices; remove devices of deleted alarms."""
    registry = dr.async_get(hass)
    phone_device = registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, phone.phone_id)},
        name=phone.phone_name,
        via_device_id=_mobile_app_device_id(registry, phone),
    )
    for alarm_id, alarm in phone.alarms.items():
        registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, phone.phone_id, alarm_id)},  # type: ignore[arg-type]
            name=f"{phone.phone_name} {alarm.label or alarm_id}",
            via_device_id=phone_device.id,
        )
    # Alarms gone from the phone take their device and entities with them.
    for device in dr.async_entries_for_config_entry(registry, entry.entry_id):
        if any(
            len(identifier) == 3
            and identifier[:2] == (DOMAIN, phone.phone_id)
            and identifier[2] not in phone.alarms  # type: ignore[misc]
            for identifier in device.identifiers
        ):
            registry.async_remove_device(device.id)


def _log_call(call: ServiceCall) -> None:
    # Logged before validation so a rejected call still shows it reached HA.
    _LOGGER.debug(
        "%s called for phone_id=%s", call.service, call.data.get(CONF_PHONE_ID)
    )


def _require_event(call: ServiceCall, allowed: tuple[str, ...]) -> str:
    event = call.data.get(CONF_EVENT)
    if event not in allowed:
        raise ServiceValidationError(
            f"Unknown event '{event or ''}'. In the shortcut, set Event Type "
            f"Number to a number from its list. Valid events: {', '.join(allowed)}"
        )
    return cast(str, event)


def _no_data_issue_id(entry: IPhoneAlarmsSyncConfigEntry) -> str:
    return f"no_data_{entry.entry_id}"


def _resolve_call(
    hass: HomeAssistant, call: ServiceCall
) -> tuple[IPhoneAlarmsSyncConfigEntry, IPhoneAlarmsSyncCoordinator]:
    """Find the loaded entry for phone_id or raise an error the shortcut shows."""
    phone_id = call.data.get(CONF_PHONE_ID)
    if not phone_id:
        raise ServiceValidationError(
            f"Phone ID is missing. Copy it from {_OPTIONS} → Sync Shortcut Setup "
            "into the first Text step of this shortcut."
        )
    entry: IPhoneAlarmsSyncConfigEntry | None = (
        hass.config_entries.async_entry_for_domain_unique_id(DOMAIN, phone_id)
    )
    if entry is None:
        raise ServiceValidationError(
            f"Unknown Phone ID '{phone_id}'. Copy the Phone ID from {_OPTIONS} → "
            "Sync Shortcut Setup into the first Text step of this shortcut."
        )
    if entry.state is not ConfigEntryState.LOADED:
        raise HomeAssistantError(
            f"iPhone Alarms Sync for '{phone_id}' is not loaded. "
            "Check it in Settings → Devices & services."
        )
    coordinator = entry.runtime_data.coordinator
    # The phone reached Home Assistant, so the shortcut chain works again.
    ir.async_delete_issue(hass, DOMAIN, _no_data_issue_id(entry))
    coordinator.phone.missed_alarm_at = None
    return entry, coordinator


def _fire_events(
    hass: HomeAssistant,
    entry: IPhoneAlarmsSyncConfigEntry,
    event: AlarmEvent,
    device_identifier: tuple[str, ...],
) -> None:
    """Fire the generic alarm event and the device trigger event."""
    hass.bus.async_fire(
        EVENT_ALARM_EVENT,
        {
            "phone_id": event.phone_id,
            "alarm_id": event.alarm_id,
            "event": event.event,
            "event_id": event.event_id,
            "occurred_at": event.occurred_at,
        },
    )
    device = dr.async_get(hass).async_get_device_by_identifier(
        device_identifier,  # type: ignore[arg-type]
        entry.entry_id,
    )
    if device:
        hass.bus.async_fire(f"{DOMAIN}_{event.event}", {"device_id": device.id})


@callback
def _async_check_missed_event(
    hass: HomeAssistant,
    entry: IPhoneAlarmsSyncConfigEntry,
    alarm_at: datetime,
    alarm_id: str | None,
) -> None:
    """Flag the phone when an alarm rang but its "goes off" never arrived."""
    coordinator = entry.runtime_data.coordinator
    phone = coordinator.phone
    alarm = phone.alarms.get(alarm_id) if alarm_id else None
    if alarm is None:
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
    # created this alarm) proves the connection; _resolve_call clears the flag too.
    last = coordinator.last_activity_at()
    # iOS may run the automation a few seconds before the scheduled minute.
    missed = last is None or last < alarm_at - timedelta(minutes=1)
    phone.missed_alarm_at = alarm_at.isoformat() if missed else None
    coordinator.save()
    coordinator.async_set_updated_data(phone)


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
        entry, coordinator = _resolve_call(hass, call)
        alarms = [
            {**a, CONF_ALARM_ID: extract_alarm_uuid(a[CONF_ALARM_ID])} for a in alarms
        ]
        coordinator.sync_alarms(alarms)
        _async_update_devices(hass, entry, coordinator.phone)
        # Always push: "Last Sync" changes on every call, and the platforms add
        # entities for new alarms.
        coordinator.async_set_updated_data(coordinator.phone)

    async def handle_report_alarm_event(call: ServiceCall) -> None:
        _log_call(call)
        event = _require_event(call, ALARM_EVENTS)
        if not call.data.get(CONF_ALARM_ID):
            raise ServiceValidationError(
                f"Alarm ID is missing. Copy it from {_OPTIONS} → Event Shortcuts "
                "Setup into the second Text step of this shortcut."
            )
        alarm_id = extract_alarm_uuid(call.data[CONF_ALARM_ID])
        entry, coordinator = _resolve_call(hass, call)
        if coordinator.get_alarm(alarm_id) is None:
            raise ServiceValidationError(
                f"Unknown Alarm ID '{alarm_id}'. Run the Sync shortcut, then copy "
                f"the Alarm ID from {_OPTIONS} → Event Shortcuts Setup."
            )
        event_obj = coordinator.report_alarm_event(alarm_id, event)
        _fire_events(
            hass, entry, event_obj, (DOMAIN, coordinator.phone.phone_id, alarm_id)
        )

    async def handle_report_device_event(call: ServiceCall) -> None:
        _log_call(call)
        scope, attr, event = DEVICE_EVENTS[_require_event(call, tuple(DEVICE_EVENTS))]
        entry, coordinator = _resolve_call(hass, call)
        event_obj = coordinator.report_device_event(scope, attr, event)
        _fire_events(hass, entry, event_obj, (DOMAIN, coordinator.phone.phone_id))

    hass.services.async_register(DOMAIN, "sync_alarms", handle_sync_alarms)
    hass.services.async_register(
        DOMAIN, "report_alarm_event", handle_report_alarm_event
    )
    hass.services.async_register(
        DOMAIN, "report_device_event", handle_report_device_event
    )

    return True


@callback
def _async_track_alarm_times(
    hass: HomeAssistant,
    entry: IPhoneAlarmsSyncConfigEntry,
    coordinator: IPhoneAlarmsSyncCoordinator,
) -> None:
    """At each alarm's time, record it so Last Alarm and Last Occurrence update."""
    tick_at: datetime | None = None
    cancel_tick: CALLBACK_TYPE | None = None

    @callback
    def _schedule() -> None:
        nonlocal tick_at, cancel_tick
        next_at, _ = calculate_next_alarm_datetime(coordinator.phone)
        if next_at == tick_at:
            return
        if cancel_tick:
            cancel_tick()
            cancel_tick = None
        tick_at = next_at
        if next_at is None:
            return

        @callback
        def _tick(_now: datetime) -> None:
            nonlocal tick_at, cancel_tick
            tick_at = cancel_tick = None
            coordinator.record_alarm_time(next_at)
            _schedule()

        cancel_tick = async_track_point_in_time(hass, _tick, next_at)

    @callback
    def _cancel() -> None:
        if cancel_tick:
            cancel_tick()

    _schedule()
    entry.async_on_unload(coordinator.async_add_listener(_schedule))
    entry.async_on_unload(_cancel)


@callback
def _async_track_missed_events(
    hass: HomeAssistant,
    entry: IPhoneAlarmsSyncConfigEntry,
    coordinator: IPhoneAlarmsSyncCoordinator,
) -> None:
    """Shortly after each alarm, check that its "goes off" event arrived."""
    check_at: datetime | None = None
    cancel_check: CALLBACK_TYPE | None = None

    @callback
    def _schedule() -> None:
        nonlocal check_at, cancel_check
        # A pending check owns the alarm that just rang; it reschedules itself.
        if check_at is not None and check_at <= dt_util.utcnow():
            return
        # Look back one grace period so an alarm that rang a moment ago (a second
        # alarm minutes after the first, or an HA restart) still gets its check.
        next_at, alarm_id = calculate_next_alarm_datetime(
            coordinator.phone, dt_util.utcnow() - MISSED_EVENT_GRACE
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
            _schedule()

        _LOGGER.debug("Next missed-event check for alarm at %s", next_at)
        cancel_check = async_track_point_in_time(
            hass, _check, next_at + MISSED_EVENT_GRACE
        )

    @callback
    def _cancel() -> None:
        if cancel_check:
            cancel_check()

    _schedule()
    entry.async_on_unload(coordinator.async_add_listener(_schedule))
    entry.async_on_unload(_cancel)


async def async_setup_entry(
    hass: HomeAssistant, entry: IPhoneAlarmsSyncConfigEntry
) -> bool:
    coordinator = IPhoneAlarmsSyncCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = IPhoneAlarmsSyncData(coordinator=coordinator)

    # Entities only describe alarm devices; link them to the phone here.
    _async_update_devices(hass, entry, coordinator.phone)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # v1.3.0 raised a repair instead of the Alarm Event Missed sensor.
    ir.async_delete_issue(hass, DOMAIN, f"missed_event_{entry.entry_id}")

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

    _async_track_alarm_times(hass, entry, coordinator)
    _async_track_missed_events(hass, entry, coordinator)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: IPhoneAlarmsSyncConfigEntry
) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
