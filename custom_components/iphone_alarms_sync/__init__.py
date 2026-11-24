from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, cast

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
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

from .const import (
    ALARM_EVENTS,
    CONF_ALARM_ID,
    CONF_ALARMS,
    CONF_EVENT,
    CONF_PHONE_ID,
    DOCS_TROUBLESHOOTING_URL,
    DOMAIN,
    EVENT_ALARM_EVENT,
    EVENT_BEDTIME_STARTS,
    EVENT_GOES_OFF,
    EVENT_WAKING_UP,
    EVENT_WIND_DOWN_STARTS,
    MISSED_EVENT_GRACE,
    PLATFORMS,
    STALE_AFTER,
    STALE_CHECK_INTERVAL,
    TRIGGER_SUBTYPE_ALARM,
    TRIGGER_SUBTYPE_ANY,
    TRIGGER_SUBTYPE_WAKEUP,
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
    extract_alarm_uuid,
    normalize_weekday,
    rings_at,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

# Device event -> (scope reported as alarm_id, PhoneData field, event name).
DEVICE_EVENTS: dict[str, tuple[str, str, str]] = {
    **{
        f"{scope}_{e}": (scope, f"{scope}_last_event_{e}_at", e)
        for scope in (TRIGGER_SUBTYPE_WAKEUP, TRIGGER_SUBTYPE_ANY)
        for e in ALARM_EVENTS
    },
    EVENT_BEDTIME_STARTS: ("bedtime", "bedtime_last_event_at", EVENT_BEDTIME_STARTS),
    EVENT_WAKING_UP: ("waking_up", "waking_up_last_event_at", EVENT_WAKING_UP),
    EVENT_WIND_DOWN_STARTS: (
        "wind_down",
        "wind_down_last_event_at",
        EVENT_WIND_DOWN_STARTS,
    ),
}


def _label(value: Any) -> str:
    return str(value or "").strip()


# One alarm as the Sync shortcut sends it. A wrong type stored here would break
# every sensor of the phone, so it is rejected before anything is saved.
ALARM_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ALARM_ID): vol.All(cv.string, vol.Length(min=1)),
        vol.Optional("label"): _label,
        vol.Optional("enabled"): cv.boolean,
        vol.Optional("hour"): vol.All(vol.Coerce(int), vol.Range(0, 23)),
        vol.Optional("minute"): vol.All(vol.Coerce(int), vol.Range(0, 59)),
        vol.Optional("repeats"): cv.boolean,
        vol.Optional("repeat_days"): vol.All(
            cv.ensure_list, [vol.All(cv.string, normalize_weekday)]
        ),
        vol.Optional("allows_snooze"): cv.boolean,
    },
    extra=vol.REMOVE_EXTRA,
)

# Where users find the IDs their shortcuts need.
_OPTIONS = "Settings → Devices & services → iPhone Alarms Sync → Configure"
# Which step of the shortcut holds the Phone ID.
_PHONE_ID_STEP = "the second Text step of this shortcut (the first is Home Wi-Fi)"


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
        manufacturer="Apple",
        via_device_id=_mobile_app_device_id(registry, phone),
    )
    labels = [alarm.label for alarm in phone.alarms.values()]
    for alarm_id, alarm in phone.alarms.items():
        # HA builds entity ids from the device name once, so a time in it goes
        # stale when the alarm moves; add it only to tell apart an empty or
        # shared label (such as the default "Alarm").
        label = alarm.label
        if not label or labels.count(label) > 1:
            label = f"{alarm.hour:02d}:{alarm.minute:02d} {label}"
        registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, phone.phone_id, alarm_id)},  # type: ignore[arg-type]
            name=f"{phone.phone_name} {label}".strip(),
            manufacturer="Apple",
            model="Alarm",
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
            f"into {_PHONE_ID_STEP}."
        )
    entry: IPhoneAlarmsSyncConfigEntry | None = (
        hass.config_entries.async_entry_for_domain_unique_id(DOMAIN, phone_id)
    )
    if entry is None:
        raise ServiceValidationError(
            f"Unknown Phone ID '{phone_id}'. Copy the Phone ID from {_OPTIONS} → "
            f"Sync Shortcut Setup into {_PHONE_ID_STEP}."
        )
    if entry.state is not ConfigEntryState.LOADED:
        raise HomeAssistantError(
            f"iPhone Alarms Sync for '{phone_id}' is not loaded. "
            "Check it in Settings → Devices & services."
        )
    coordinator = entry.runtime_data.coordinator
    # The phone reached Home Assistant, so the shortcut chain works again.
    ir.async_delete_issue(hass, DOMAIN, _no_data_issue_id(entry))
    if coordinator.phone.missed_alarm_at:
        # Update now: the call may still be rejected and store nothing.
        coordinator.phone.missed_alarm_at = None
        coordinator.save()
        coordinator.async_set_updated_data(coordinator.phone)
    return entry, coordinator


def _fire_events(
    hass: HomeAssistant,
    entry: IPhoneAlarmsSyncConfigEntry,
    event: AlarmEvent,
    device_identifier: tuple[str, ...],
    subtype: str,
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
            "estimated": event.estimated,
        },
    )
    device = dr.async_get(hass).async_get_device_by_identifier(
        device_identifier,  # type: ignore[arg-type]
        entry.entry_id,
    )
    if device:
        hass.bus.async_fire(
            f"{DOMAIN}_{event.event}", {"device_id": device.id, "subtype": subtype}
        )


def _fire_alarm_events(
    hass: HomeAssistant, entry: IPhoneAlarmsSyncConfigEntry, event: AlarmEvent
) -> None:
    """Fire the events of one alarm (not of the phone)."""
    _fire_events(
        hass,
        entry,
        event,
        (DOMAIN, event.phone_id, event.alarm_id),
        TRIGGER_SUBTYPE_ALARM,
    )


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
    if not rings_at(alarm, alarm_at, dt_util.parse_datetime(phone.synced_at or "")):
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
        try:
            alarms = vol.Schema([ALARM_SCHEMA])(call.data.get(CONF_ALARMS))
        except vol.Invalid as err:
            raise ServiceValidationError(
                "The shortcut sent no valid alarm list (each alarm needs an "
                f"'alarm_id'; {err}). Re-import it from {_OPTIONS} → Sync "
                "Shortcut Setup."
            ) from err
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
                "Setup into the last Text step of this shortcut."
            )
        alarm_id = extract_alarm_uuid(call.data[CONF_ALARM_ID])
        entry, coordinator = _resolve_call(hass, call)
        alarm = coordinator.get_alarm(alarm_id)
        if alarm is None:
            raise ServiceValidationError(
                f"Unknown Alarm ID '{alarm_id}'. Run the Sync shortcut, then copy "
                f"the Alarm ID from {_OPTIONS} → Event Shortcuts Setup."
            )
        already_fired = False
        if event == EVENT_GOES_OFF and alarm.estimate_goes_off:
            # The shortcut works for this alarm, so stop estimating. An estimate
            # fired for this very ring already ran the automations.
            alarm.estimate_goes_off = False
            estimated_at = coordinator.estimated_at.get(alarm_id)
            already_fired = (
                estimated_at is not None
                and dt_util.utcnow() - estimated_at < MISSED_EVENT_GRACE
            )
        event_obj = coordinator.report_alarm_event(alarm_id, event)
        if not already_fired:
            _fire_alarm_events(hass, entry, event_obj)

    async def handle_report_device_event(call: ServiceCall) -> None:
        _log_call(call)
        scope, attr, event = DEVICE_EVENTS[_require_event(call, tuple(DEVICE_EVENTS))]
        entry, coordinator = _resolve_call(hass, call)
        event_obj = coordinator.report_device_event(scope, attr, event)
        _fire_events(
            hass, entry, event_obj, (DOMAIN, coordinator.phone.phone_id), scope
        )

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
    """At each alarm's time, record it and fire the estimated "goes off"."""
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
            for alarm in coordinator.record_alarm_time(next_at):
                if alarm.estimate_goes_off:
                    coordinator.estimated_at[alarm.alarm_id] = next_at
                    _fire_alarm_events(
                        hass,
                        entry,
                        coordinator.new_event(
                            alarm.alarm_id, EVENT_GOES_OFF, estimated=True
                        ),
                    )
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
    # The Snooze time number was removed after v1.6.0: iOS never shared the length.
    registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity.domain == "number":
            registry.async_remove(entity.entity_id)
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
