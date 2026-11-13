from __future__ import annotations

import logging
import uuid
from collections import deque
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ALARM_ID,
    CONF_ALARMS,
    CONF_ENABLED,
    CONF_MOBILE_APP_DEVICE_ID,
    CONF_PHONE_ID,
    CONF_PHONE_NAME,
    CONF_SYNC_DISABLED_ALARMS,
    DEFAULT_SNOOZE_TIME,
    DOMAIN,
)
from .utils import calculate_next_occurrence, extract_alarm_uuid

_LOGGER = logging.getLogger(__name__)

# The options flow lists this many recent events; older ones are not kept.
MAX_EVENTS = 20


@dataclass
class AlarmData:
    alarm_id: str
    label: str = ""
    enabled: bool = False
    hour: int = 0
    minute: int = 0
    repeats: bool = False
    repeat_days: list[str] = field(default_factory=list)
    allows_snooze: bool = False
    snooze_time: int = DEFAULT_SNOOZE_TIME
    last_event_goes_off_at: str | None = None
    last_event_snoozed_at: str | None = None
    last_event_stopped_at: str | None = None
    last_occurrence_datetime: str | None = None


ALARM_FIELDS = frozenset(f.name for f in fields(AlarmData))
ALARM_EVENT_FIELDS = (
    "last_event_goes_off_at",
    "last_event_snoozed_at",
    "last_event_stopped_at",
)
# Fields the Sync shortcut sends; snooze_time is only taken for a new alarm,
# afterwards it belongs to the Snooze Time number entity.
SYNCED_FIELDS = (
    "label",
    "enabled",
    "hour",
    "minute",
    "repeats",
    "repeat_days",
    "allows_snooze",
)


@dataclass
class AlarmEvent:
    event_id: str
    alarm_id: str
    phone_id: str
    event: str
    occurred_at: str


@dataclass
class PhoneData:
    phone_id: str
    phone_name: str
    mobile_app_device_id: str | None
    alarms: dict[str, AlarmData]
    sync_disabled_alarms: bool = True
    synced_at: str | None = None
    last_alarm_datetime: str | None = None
    wakeup_last_event_goes_off_at: str | None = None
    wakeup_last_event_snoozed_at: str | None = None
    wakeup_last_event_stopped_at: str | None = None
    any_last_event_goes_off_at: str | None = None
    any_last_event_snoozed_at: str | None = None
    any_last_event_stopped_at: str | None = None
    bedtime_last_event_at: str | None = None
    waking_up_last_event_at: str | None = None
    wind_down_last_event_at: str | None = None
    missed_alarm_at: str | None = None


PHONE_EVENT_FIELDS = (
    "wakeup_last_event_goes_off_at",
    "wakeup_last_event_snoozed_at",
    "wakeup_last_event_stopped_at",
    "any_last_event_goes_off_at",
    "any_last_event_snoozed_at",
    "any_last_event_stopped_at",
    "bedtime_last_event_at",
    "waking_up_last_event_at",
    "wind_down_last_event_at",
)
# Runtime state kept in entry.options under the same keys as the field names.
PHONE_STATE_FIELDS = (
    "synced_at",
    "last_alarm_datetime",
    *PHONE_EVENT_FIELDS,
    "missed_alarm_at",
)


@dataclass
class IPhoneAlarmsSyncData:
    coordinator: IPhoneAlarmsSyncCoordinator


type IPhoneAlarmsSyncConfigEntry = ConfigEntry[IPhoneAlarmsSyncData]


def _alarm_from_options(key: str, stored: dict[str, Any]) -> AlarmData:
    values = {k: v for k, v in stored.items() if k in ALARM_FIELDS}
    values[CONF_ALARM_ID] = extract_alarm_uuid(stored.get(CONF_ALARM_ID, key))
    return AlarmData(**values)


class IPhoneAlarmsSyncCoordinator(DataUpdateCoordinator[PhoneData]):
    """Holds one phone's alarms; the phone pushes data through the actions."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=None,
        )
        self.entry = entry
        self._events: deque[AlarmEvent] = deque(maxlen=MAX_EVENTS)
        options = entry.options
        self.phone = PhoneData(
            phone_id=entry.data.get(CONF_PHONE_ID, ""),
            phone_name=entry.data.get(CONF_PHONE_NAME, ""),
            mobile_app_device_id=entry.data.get(CONF_MOBILE_APP_DEVICE_ID),
            sync_disabled_alarms=entry.data.get(CONF_SYNC_DISABLED_ALARMS, True),
            alarms={
                extract_alarm_uuid(key): _alarm_from_options(key, stored)
                for key, stored in options.get(CONF_ALARMS, {}).items()
            },
            **{name: options.get(name) for name in PHONE_STATE_FIELDS},
        )

    async def _async_update_data(self) -> PhoneData:
        return self.phone

    def get_alarm(self, alarm_id: str) -> AlarmData | None:
        return self.phone.alarms.get(alarm_id)

    def get_events(self) -> list[AlarmEvent]:
        return list(self._events)

    def last_activity_at(self) -> datetime | None:
        """Return when the phone last sent anything (sync or event)."""
        phone = self.phone
        timestamps = [phone.synced_at]
        timestamps += [getattr(phone, name) for name in PHONE_EVENT_FIELDS]
        for alarm in phone.alarms.values():
            timestamps += [getattr(alarm, name) for name in ALARM_EVENT_FIELDS]
        parsed = [dt_util.parse_datetime(t) for t in timestamps if t]
        return max((t for t in parsed if t), default=None)

    def sync_alarms(self, alarms: list[dict[str, Any]]) -> None:
        """Store the alarms the phone sent."""
        phone = self.phone
        received_any = bool(alarms)
        if not phone.sync_disabled_alarms:
            alarms = [a for a in alarms if a.get(CONF_ENABLED, False)]

        for alarm_dict in alarms:
            alarm_id = alarm_dict[CONF_ALARM_ID]
            values = {k: alarm_dict[k] for k in SYNCED_FIELDS if k in alarm_dict}
            if alarm := phone.alarms.get(alarm_id):
                for name, value in values.items():
                    setattr(alarm, name, value)
                continue
            if "snooze_time" in alarm_dict:
                values["snooze_time"] = alarm_dict["snooze_time"]
            phone.alarms[alarm_id] = AlarmData(alarm_id=alarm_id, **values)

        # The shortcut sends every alarm, so a missing one was deleted on the device
        # (or disabled, when disabled alarms are not synced). An empty payload is more
        # likely a failed shortcut than a phone without alarms, so it removes nothing.
        if received_any:
            synced_ids = {a[CONF_ALARM_ID] for a in alarms}
            for alarm_id in [a for a in phone.alarms if a not in synced_ids]:
                del phone.alarms[alarm_id]

        # Record every sync, not only changes, so "Last Sync" shows the shortcut works.
        phone.synced_at = dt_util.utcnow().isoformat()
        self.save()

    def report_alarm_event(self, alarm_id: str, event: str) -> AlarmEvent:
        return self._record(
            self.phone.alarms[alarm_id], f"last_event_{event}_at", alarm_id, event
        )

    def report_device_event(self, scope: str, attr: str, event: str) -> AlarmEvent:
        return self._record(self.phone, attr, scope, event)

    def _record(self, target: Any, attr: str, alarm_id: str, event: str) -> AlarmEvent:
        event_obj = AlarmEvent(
            event_id=str(uuid.uuid4()),
            alarm_id=alarm_id,
            phone_id=self.phone.phone_id,
            event=event,
            occurred_at=dt_util.utcnow().isoformat(),
        )
        self._events.append(event_obj)
        setattr(target, attr, event_obj.occurred_at)
        self.save()
        self.async_set_updated_data(self.phone)
        return event_obj

    def record_alarm_time(self, at: datetime) -> None:
        """Mark the alarms scheduled for `at` as rung (Last Alarm, Last Occurrence)."""
        before = at - timedelta(minutes=1)
        rang = [
            alarm
            for alarm in self.phone.alarms.values()
            if calculate_next_occurrence(alarm, before) == at
        ]
        if not rang:
            return
        self.phone.last_alarm_datetime = at.isoformat()
        for alarm in rang:
            alarm.last_occurrence_datetime = at.isoformat()
        self.save()
        self.async_set_updated_data(self.phone)

    def save(self) -> None:
        """Persist the runtime state; HA skips the write when nothing changed."""
        phone = self.phone
        options = {
            CONF_ALARMS: {
                alarm_id: asdict(alarm) for alarm_id, alarm in phone.alarms.items()
            },
            **{name: getattr(phone, name) for name in PHONE_STATE_FIELDS},
        }
        self.hass.config_entries.async_update_entry(self.entry, options=options)
