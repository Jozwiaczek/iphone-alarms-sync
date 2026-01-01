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
    CONF_ALLOWS_SNOOZE,
    CONF_ENABLED,
    CONF_HOUR,
    CONF_ICON,
    CONF_LABEL,
    CONF_LAST_ALARM_DATETIME,
    CONF_LAST_ALARM_ID,
    CONF_LAST_EVENT_GOES_OFF_AT,
    CONF_LAST_EVENT_SNOOZED_AT,
    CONF_LAST_EVENT_STOPPED_AT,
    CONF_LAST_OCCURRENCE_DATETIME,
    CONF_MINUTE,
    CONF_MOBILE_APP_DEVICE_ID,
    CONF_PHONE_ID,
    CONF_PHONE_NAME,
    CONF_REPEAT_DAYS,
    CONF_REPEATS,
    CONF_SYNC_DISABLED_ALARMS,
    CONF_SYNCED_AT,
    EVENT_GOES_OFF,
    EVENT_SNOOZED,
    EVENT_STOPPED,
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
    last_event_goes_off_at: str | None = None
    last_event_snoozed_at: str | None = None
    last_event_stopped_at: str | None = None
    last_occurrence_datetime: str | None = None
    icon: str = "mdi:alarm"


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
    synced_at: str | None = None
    sync_disabled_alarms: bool = True
    last_alarm_datetime: str | None = None
    last_alarm_id: str | None = None


@dataclass
class IPhoneAlarmsSyncData:
    coordinator: IPhoneAlarmsSyncCoordinator


if TYPE_CHECKING:
    IPhoneAlarmsSyncConfigEntry = ConfigEntry[IPhoneAlarmsSyncData]
else:
    IPhoneAlarmsSyncConfigEntry = Any


class IPhoneAlarmsSyncCoordinator(DataUpdateCoordinator[PhoneData]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name=entry.domain,
            update_interval=None,
        )
        self.entry = entry
        self._phone: PhoneData | None = None
        self._events: list[AlarmEvent] = []
        self._load_from_config()

    def _load_from_config(self) -> None:
        phone_id = self.entry.data.get(CONF_PHONE_ID, "")
        phone_name = self.entry.data.get(CONF_PHONE_NAME, "")
        mobile_app_device_id = self.entry.data.get(CONF_MOBILE_APP_DEVICE_ID)
        sync_disabled_alarms = self.entry.data.get(CONF_SYNC_DISABLED_ALARMS, True)

        alarms_data = self.entry.options.get("alarms", {})
        alarms = {}
        for alarm_id, alarm_dict in alarms_data.items():
            alarms[alarm_id] = AlarmData(
                alarm_id=alarm_dict.get(CONF_ALARM_ID, alarm_id),
                label=alarm_dict.get(CONF_LABEL, ""),
                enabled=alarm_dict.get(CONF_ENABLED, False),
                hour=alarm_dict.get(CONF_HOUR, 0),
                minute=alarm_dict.get(CONF_MINUTE, 0),
                repeats=alarm_dict.get(CONF_REPEATS, False),
                repeat_days=alarm_dict.get(CONF_REPEAT_DAYS, []),
                allows_snooze=alarm_dict.get(CONF_ALLOWS_SNOOZE, False),
                last_event_goes_off_at=alarm_dict.get(CONF_LAST_EVENT_GOES_OFF_AT),
                last_event_snoozed_at=alarm_dict.get(CONF_LAST_EVENT_SNOOZED_AT),
                last_event_stopped_at=alarm_dict.get(CONF_LAST_EVENT_STOPPED_AT),
                last_occurrence_datetime=alarm_dict.get(CONF_LAST_OCCURRENCE_DATETIME),
                icon=alarm_dict.get(CONF_ICON, "mdi:alarm"),
            )

        synced_at = self.entry.options.get(CONF_SYNCED_AT)

        self._phone = PhoneData(
            phone_id=phone_id,
            phone_name=phone_name,
            mobile_app_device_id=mobile_app_device_id,
            alarms=alarms,
            synced_at=synced_at,
            sync_disabled_alarms=sync_disabled_alarms,
            last_alarm_datetime=self.entry.options.get(CONF_LAST_ALARM_DATETIME),
            last_alarm_id=self.entry.options.get(CONF_LAST_ALARM_ID),
        )

    async def _async_update_data(self) -> PhoneData:
        if self._phone is None:
            raise ValueError("Phone not initialized")
        return self._phone

    def update_phone(
        self,
        phone_name: str | None = None,
        mobile_app_device_id: str | None = None,
        sync_disabled_alarms: bool | None = None,
    ) -> None:
        if self._phone is None:
            raise ValueError("Phone not initialized")
        if phone_name is not None:
            self._phone.phone_name = phone_name
        if mobile_app_device_id is not None:
            self._phone.mobile_app_device_id = mobile_app_device_id
        if sync_disabled_alarms is not None:
            self._phone.sync_disabled_alarms = sync_disabled_alarms
        self._save_to_config()

    def get_phone(self) -> PhoneData | None:
        return self._phone

    def get_all_phones(self) -> dict[str, PhoneData]:
        if self._phone is None:
            return {}
        return {self._phone.phone_id: self._phone}

    def _alarm_data_changed(
        self,
        existing: AlarmData,
        new_dict: dict[str, Any],
    ) -> bool:
        return (
            existing.label != new_dict.get(CONF_LABEL)
            or existing.enabled != new_dict.get(CONF_ENABLED)
            or existing.hour != new_dict.get(CONF_HOUR)
            or existing.minute != new_dict.get(CONF_MINUTE)
            or existing.repeats != new_dict.get(CONF_REPEATS)
            or existing.repeat_days != new_dict.get(CONF_REPEAT_DAYS, [])
            or existing.allows_snooze != new_dict.get(CONF_ALLOWS_SNOOZE)
        )

    def sync_alarms(self, alarms: list[dict[str, Any]]) -> tuple[list[str], bool]:
        if self._phone is None:
            raise ValueError("Phone not initialized")

        has_changes = False
        synced_at = dt_util.utcnow().isoformat()
        new_alarm_ids: list[str] = []

        if not self._phone.sync_disabled_alarms:
            alarms = [a for a in alarms if a.get(CONF_ENABLED, False)]

        synced_alarm_ids = set()
        for alarm_dict in alarms:
            alarm_id = alarm_dict[CONF_ALARM_ID]
            synced_alarm_ids.add(alarm_id)
            if alarm_id not in self._phone.alarms:
                self._phone.alarms[alarm_id] = AlarmData(
                    alarm_id=alarm_id,
                    label=alarm_dict.get(CONF_LABEL, ""),
                    enabled=alarm_dict.get(CONF_ENABLED, False),
                    hour=alarm_dict.get(CONF_HOUR, 0),
                    minute=alarm_dict.get(CONF_MINUTE, 0),
                    repeats=alarm_dict.get(CONF_REPEATS, False),
                    repeat_days=alarm_dict.get(CONF_REPEAT_DAYS, []),
                    allows_snooze=alarm_dict.get(CONF_ALLOWS_SNOOZE, False),
                )
                new_alarm_ids.append(alarm_id)
                has_changes = True
            else:
                alarm = self._phone.alarms[alarm_id]
                if self._alarm_data_changed(alarm, alarm_dict):
                    alarm.label = alarm_dict.get(CONF_LABEL, alarm.label)
                    alarm.enabled = alarm_dict.get(CONF_ENABLED, alarm.enabled)
                    alarm.hour = alarm_dict.get(CONF_HOUR, alarm.hour)
                    alarm.minute = alarm_dict.get(CONF_MINUTE, alarm.minute)
                    alarm.repeats = alarm_dict.get(CONF_REPEATS, alarm.repeats)
                    alarm.repeat_days = alarm_dict.get(
                        CONF_REPEAT_DAYS, alarm.repeat_days
                    )
                    alarm.allows_snooze = alarm_dict.get(
                        CONF_ALLOWS_SNOOZE, alarm.allows_snooze
                    )
                    has_changes = True

        if not self._phone.sync_disabled_alarms:
            alarms_to_remove = [
                alarm_id
                for alarm_id in self._phone.alarms.keys()
                if alarm_id not in synced_alarm_ids
            ]
            for alarm_id in alarms_to_remove:
                del self._phone.alarms[alarm_id]
                has_changes = True

        if has_changes:
            self._phone.synced_at = synced_at
            self._save_to_config()

        return new_alarm_ids, has_changes

    def report_alarm_event(self, alarm_id: str, event: str) -> AlarmEvent:
        if self._phone is None:
            raise ValueError("Phone not initialized")
        if alarm_id not in self._phone.alarms:
            raise ValueError(f"Alarm {alarm_id} not found")
        event_obj = AlarmEvent(
            event_id=str(uuid.uuid4()),
            alarm_id=alarm_id,
            phone_id=self._phone.phone_id,
            event=event,
            occurred_at=dt_util.utcnow().isoformat(),
        )
        self._events.append(event_obj)
        alarm = self._phone.alarms[alarm_id]
        if event == EVENT_GOES_OFF:
            alarm.last_event_goes_off_at = event_obj.occurred_at
        elif event == EVENT_SNOOZED:
            alarm.last_event_snoozed_at = event_obj.occurred_at
        elif event == EVENT_STOPPED:
            alarm.last_event_stopped_at = event_obj.occurred_at
        self._save_to_config()
        return event_obj

    def get_alarm(self, alarm_id: str) -> AlarmData | None:
        if self._phone is None:
            return None
        return self._phone.alarms.get(alarm_id)

    def get_all_alarms(self) -> dict[str, AlarmData]:
        if self._phone is None:
            return {}
        return self._phone.alarms.copy()

    def delete_alarm(self, alarm_id: str) -> None:
        if self._phone is None:
            raise ValueError("Phone not initialized")
        if alarm_id in self._phone.alarms:
            del self._phone.alarms[alarm_id]
            self._save_to_config()

    def update_alarm_metadata(
        self,
        alarm_id: str,
        label: str | None = None,
        icon: str | None = None,
    ) -> None:
        if self._phone is None:
            raise ValueError("Phone not initialized")
        if alarm_id not in self._phone.alarms:
            raise ValueError(f"Alarm {alarm_id} not found")
        alarm = self._phone.alarms[alarm_id]
        if label is not None:
            alarm.label = label
        if icon is not None:
            alarm.icon = icon
        self._save_to_config()

    def get_events(
        self,
        alarm_id: str | None = None,
        limit: int | None = None,
    ) -> list[AlarmEvent]:
        events = self._events
        if alarm_id:
            events = [e for e in events if e.alarm_id == alarm_id]
        if limit:
            events = events[-limit:]
        return events

    def _save_to_config(self) -> None:
        if self._phone is None:
            return

        current_options = self.entry.options.copy()
        current_alarms = current_options.get("alarms", {})
        alarms_dict = {}
        has_changes = False

        for alarm_id, alarm in self._phone.alarms.items():
            alarm_data = {
                CONF_ALARM_ID: alarm.alarm_id,
                CONF_LABEL: alarm.label,
                CONF_ENABLED: alarm.enabled,
                CONF_HOUR: alarm.hour,
                CONF_MINUTE: alarm.minute,
                CONF_REPEATS: alarm.repeats,
                CONF_REPEAT_DAYS: alarm.repeat_days,
                CONF_ALLOWS_SNOOZE: alarm.allows_snooze,
                CONF_LAST_EVENT_GOES_OFF_AT: alarm.last_event_goes_off_at,
                CONF_LAST_EVENT_SNOOZED_AT: alarm.last_event_snoozed_at,
                CONF_LAST_EVENT_STOPPED_AT: alarm.last_event_stopped_at,
                CONF_LAST_OCCURRENCE_DATETIME: alarm.last_occurrence_datetime,
                CONF_ICON: alarm.icon,
            }

            if alarm_id not in current_alarms or current_alarms[alarm_id] != alarm_data:
                has_changes = True

            alarms_dict[alarm_id] = alarm_data

        if current_alarms.keys() != alarms_dict.keys():
            has_changes = True

        if self._phone.synced_at != current_options.get(CONF_SYNCED_AT):
            has_changes = True

        if self._phone.last_alarm_datetime != current_options.get(
            CONF_LAST_ALARM_DATETIME
        ):
            has_changes = True

        if self._phone.last_alarm_id != current_options.get(CONF_LAST_ALARM_ID):
            has_changes = True

        if has_changes:
            new_options = {
                "alarms": alarms_dict,
                CONF_SYNCED_AT: self._phone.synced_at,
                CONF_LAST_ALARM_DATETIME: self._phone.last_alarm_datetime,
                CONF_LAST_ALARM_ID: self._phone.last_alarm_id,
            }
            self.hass.config_entries.async_update_entry(
                self.entry,
                options=new_options,
            )
