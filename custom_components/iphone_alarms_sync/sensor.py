from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AlarmData, IPhoneAlarmsSyncConfigEntry, PhoneData
from .entity import AlarmEntity, PhoneEntity, async_add_alarm_entities, parse_timestamp
from .utils import calculate_next_alarm_datetime, calculate_next_occurrence

type SensorValue = datetime | str | int | None


@dataclass(frozen=True, kw_only=True)
class PhoneSensorDescription(SensorEntityDescription):
    value_fn: Callable[[PhoneData], SensorValue]


@dataclass(frozen=True, kw_only=True)
class AlarmSensorDescription(SensorEntityDescription):
    value_fn: Callable[[AlarmData], SensorValue]


def _next_alarm_label(phone: PhoneData) -> str | None:
    _, alarm_id = calculate_next_alarm_datetime(phone)
    alarm = phone.alarms.get(alarm_id) if alarm_id else None
    return alarm.label if alarm else None


def _phone_timestamp(key: str, name: str) -> PhoneSensorDescription:
    return PhoneSensorDescription(
        key=key,
        name=name,
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda phone: parse_timestamp(getattr(phone, key)),
    )


def _alarm_timestamp(key: str, name: str) -> AlarmSensorDescription:
    return AlarmSensorDescription(
        key=key,
        name=name,
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda alarm: parse_timestamp(getattr(alarm, key)),
    )


PHONE_SENSORS: tuple[PhoneSensorDescription, ...] = (
    PhoneSensorDescription(
        key="next_alarm_datetime",
        name="Next Alarm",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda phone: calculate_next_alarm_datetime(phone)[0],
    ),
    PhoneSensorDescription(
        key="next_alarm_label", name="Next Alarm Label", value_fn=_next_alarm_label
    ),
    _phone_timestamp("last_alarm_datetime", "Last Alarm"),
    PhoneSensorDescription(
        key="last_sync",
        name="Last Sync",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda phone: parse_timestamp(phone.synced_at),
    ),
    PhoneSensorDescription(
        key="enabled_alarms",
        name="Enabled Alarms",
        value_fn=lambda phone: sum(a.enabled for a in phone.alarms.values()),
    ),
    PhoneSensorDescription(
        key="total_alarms",
        name="Total Alarms",
        value_fn=lambda phone: len(phone.alarms),
    ),
    PhoneSensorDescription(
        key="disabled_alarms",
        name="Disabled Alarms",
        value_fn=lambda phone: sum(not a.enabled for a in phone.alarms.values()),
    ),
    _phone_timestamp("wakeup_last_event_goes_off_at", "Wake-Up Last Goes Off At"),
    _phone_timestamp("wakeup_last_event_snoozed_at", "Wake-Up Last Snoozed At"),
    _phone_timestamp("wakeup_last_event_stopped_at", "Wake-Up Last Stopped At"),
    _phone_timestamp("any_last_event_goes_off_at", "Any Last Goes Off At"),
    _phone_timestamp("any_last_event_snoozed_at", "Any Last Snoozed At"),
    _phone_timestamp("any_last_event_stopped_at", "Any Last Stopped At"),
    _phone_timestamp("bedtime_last_event_at", "Bedtime Last At"),
    _phone_timestamp("waking_up_last_event_at", "Waking Up Last At"),
    _phone_timestamp("wind_down_last_event_at", "Wind Down Last At"),
)

ALARM_SENSORS: tuple[AlarmSensorDescription, ...] = (
    AlarmSensorDescription(
        key="alarm_id", name="ID", value_fn=lambda alarm: alarm.alarm_id
    ),
    AlarmSensorDescription(
        key="next_occurrence_datetime",
        name="Next Occurrence",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=calculate_next_occurrence,
    ),
    _alarm_timestamp("last_occurrence_datetime", "Last Occurrence"),
    _alarm_timestamp("last_event_goes_off_at", "Last Goes Off At"),
    _alarm_timestamp("last_event_snoozed_at", "Last Snoozed At"),
    _alarm_timestamp("last_event_stopped_at", "Last Stopped At"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IPhoneAlarmsSyncConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities(PhoneSensor(coordinator, d) for d in PHONE_SENSORS)
    async_add_alarm_entities(
        entry,
        async_add_entities,
        lambda alarm_id: (AlarmSensor(coordinator, alarm_id, d) for d in ALARM_SENSORS),
    )


class PhoneSensor(PhoneEntity, SensorEntity):
    entity_description: PhoneSensorDescription

    @property
    def native_value(self) -> SensorValue:
        return self.entity_description.value_fn(self.coordinator.phone)


class AlarmSensor(AlarmEntity, SensorEntity):
    entity_description: AlarmSensorDescription

    @property
    def native_value(self) -> SensorValue:
        alarm = self.alarm
        return self.entity_description.value_fn(alarm) if alarm else None

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        if self.entity_description.key != "alarm_id":
            return None

        alarm = self.alarm
        if alarm is None:
            return None

        return {
            "label": alarm.label,
            "time": f"{alarm.hour:02d}:{alarm.minute:02d}",
            "hour": alarm.hour,
            "minute": alarm.minute,
            "enabled": alarm.enabled,
            "repeats": alarm.repeats,
            "repeat_days": list(alarm.repeat_days),
            "allows_snooze": alarm.allows_snooze,
            "snooze_time": alarm.snooze_time if alarm.allows_snooze else None,
        }
