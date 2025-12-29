from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
else:
    ConfigEntry = Any

from .const import (
    CONF_ALARM_ID,
    CONF_ALARMS,
    CONF_ALLOWS_SNOOZE,
    CONF_ENABLED,
    CONF_HOUR,
    CONF_LABEL,
    CONF_LAST_EVENT,
    CONF_LAST_EVENT_AT,
    CONF_MINUTE,
    CONF_PHONE_ID,
    CONF_PHONE_NAME,
    CONF_REPEAT_DAYS,
    CONF_REPEATS,
    CONF_SYNCED_AT,
)


@dataclass
class AlarmData:
    alarm_id: str
    label: str
    enabled: bool
    hour: int
    minute: int
    repeats: bool
    repeat_days: list[str]
    allows_snooze: bool
    synced_at: str | None = None
    last_event: str | None = None
    last_event_at: str | None = None
    icon: str = "mdi:alarm"


@dataclass
class AlarmEvent:
    event_id: str
    alarm_id: str
    event: str
    occurred_at: str


@dataclass
class IPhoneAlarmsSyncData:
    coordinator: IPhoneAlarmsSyncCoordinator


if TYPE_CHECKING:
    IPhoneAlarmsSyncConfigEntry = ConfigEntry[IPhoneAlarmsSyncData]
else:
    IPhoneAlarmsSyncConfigEntry = Any


class IPhoneAlarmsSyncCoordinator(DataUpdateCoordinator[dict[str, AlarmData]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name=entry.domain,
            update_interval=None,
        )
        self.entry = entry
        self.phone_id: str = entry.data[CONF_PHONE_ID]
        self.phone_name: str = entry.data[CONF_PHONE_NAME]
        self.mobile_app_device_id: str | None = entry.data.get("mobile_app_device_id")
        self._alarms: dict[str, AlarmData] = {}
        self._events: list[AlarmEvent] = []
        self._load_from_config()

    def _load_from_config(self) -> None:
        if alarms_data := self.entry.options.get("alarms", {}):
            for alarm_id, alarm_dict in alarms_data.items():
                self._alarms[alarm_id] = AlarmData(**alarm_dict)

    async def _async_update_data(self) -> dict[str, AlarmData]:
        return self._alarms

    def sync_alarms(self, alarms: list[dict[str, Any]]) -> None:
        synced_at = dt_util.utcnow().isoformat()
        for alarm_dict in alarms:
            alarm_id = alarm_dict[CONF_ALARM_ID]
            if alarm_id not in self._alarms:
                self._alarms[alarm_id] = AlarmData(
                    alarm_id=alarm_id,
                    label=alarm_dict.get(CONF_LABEL, ""),
                    enabled=alarm_dict.get(CONF_ENABLED, False),
                    hour=alarm_dict.get(CONF_HOUR, 0),
                    minute=alarm_dict.get(CONF_MINUTE, 0),
                    repeats=alarm_dict.get(CONF_REPEATS, False),
                    repeat_days=alarm_dict.get(CONF_REPEAT_DAYS, []),
                    allows_snooze=alarm_dict.get(CONF_ALLOWS_SNOOZE, False),
                    synced_at=synced_at,
                )
            else:
                alarm = self._alarms[alarm_id]
                alarm.label = alarm_dict.get(CONF_LABEL, alarm.label)
                alarm.enabled = alarm_dict.get(CONF_ENABLED, alarm.enabled)
                alarm.hour = alarm_dict.get(CONF_HOUR, alarm.hour)
                alarm.minute = alarm_dict.get(CONF_MINUTE, alarm.minute)
                alarm.repeats = alarm_dict.get(CONF_REPEATS, alarm.repeats)
                alarm.repeat_days = alarm_dict.get(CONF_REPEAT_DAYS, alarm.repeat_days)
                alarm.allows_snooze = alarm_dict.get(
                    CONF_ALLOWS_SNOOZE, alarm.allows_snooze
                )
                alarm.synced_at = synced_at
        self._save_to_config()

    def report_alarm_event(self, alarm_id: str, event: str) -> AlarmEvent:
        if alarm_id not in self._alarms:
            raise ValueError(f"Alarm {alarm_id} not found")
        event_obj = AlarmEvent(
            event_id=str(uuid.uuid4()),
            alarm_id=alarm_id,
            event=event,
            occurred_at=dt_util.utcnow().isoformat(),
        )
        self._events.append(event_obj)
        alarm = self._alarms[alarm_id]
        alarm.last_event = event
        alarm.last_event_at = event_obj.occurred_at
        self._save_to_config()
        return event_obj

    def get_alarm(self, alarm_id: str) -> AlarmData | None:
        return self._alarms.get(alarm_id)

    def get_all_alarms(self) -> dict[str, AlarmData]:
        return self._alarms.copy()

    def delete_alarm(self, alarm_id: str) -> None:
        if alarm_id in self._alarms:
            del self._alarms[alarm_id]
            self._save_to_config()

    def update_alarm_metadata(
        self, alarm_id: str, label: str | None = None, icon: str | None = None
    ) -> None:
        if alarm_id not in self._alarms:
            raise ValueError(f"Alarm {alarm_id} not found")
        alarm = self._alarms[alarm_id]
        if label is not None:
            alarm.label = label
        if icon is not None:
            alarm.icon = icon
        self._save_to_config()

    def get_events(
        self, alarm_id: str | None = None, limit: int | None = None
    ) -> list[AlarmEvent]:
        events = self._events
        if alarm_id:
            events = [e for e in events if e.alarm_id == alarm_id]
        if limit:
            events = events[-limit:]
        return events

    def _save_to_config(self) -> None:
        alarms_dict = {}
        for alarm_id, alarm in self._alarms.items():
            alarms_dict[alarm_id] = {
                CONF_ALARM_ID: alarm.alarm_id,
                CONF_LABEL: alarm.label,
                CONF_ENABLED: alarm.enabled,
                CONF_HOUR: alarm.hour,
                CONF_MINUTE: alarm.minute,
                CONF_REPEATS: alarm.repeats,
                CONF_REPEAT_DAYS: alarm.repeat_days,
                CONF_ALLOWS_SNOOZE: alarm.allows_snooze,
                CONF_SYNCED_AT: alarm.synced_at,
                CONF_LAST_EVENT: alarm.last_event,
                CONF_LAST_EVENT_AT: alarm.last_event_at,
                "icon": alarm.icon,
            }
        self.hass.config_entries.async_update_entry(
            self.entry,
            options={CONF_ALARMS: alarms_dict},
        )
