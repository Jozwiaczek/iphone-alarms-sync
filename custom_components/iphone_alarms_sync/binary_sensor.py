from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AlarmData, IPhoneAlarmsSyncConfigEntry
from .entity import AlarmEntity, PhoneEntity, async_add_alarm_entities
from .utils import WEEKDAY_MAP


@dataclass(frozen=True, kw_only=True)
class AlarmBinarySensorDescription(BinarySensorEntityDescription):
    is_on_fn: Callable[[AlarmData], bool]


def _repeats_on(day: str) -> AlarmBinarySensorDescription:
    return AlarmBinarySensorDescription(
        key=f"repeats_{day.lower()}",
        name=f"Repeats {day}",
        entity_registry_enabled_default=False,
        is_on_fn=lambda alarm: day in alarm.repeat_days,
    )


ALARM_BINARY_SENSORS: tuple[AlarmBinarySensorDescription, ...] = (
    AlarmBinarySensorDescription(
        key="enabled", name="Enabled", is_on_fn=lambda alarm: alarm.enabled
    ),
    AlarmBinarySensorDescription(
        key="repeats",
        name="Repeats",
        entity_registry_enabled_default=False,
        is_on_fn=lambda alarm: alarm.repeats,
    ),
    AlarmBinarySensorDescription(
        key="allows_snooze",
        name="Allows Snooze",
        is_on_fn=lambda alarm: alarm.allows_snooze,
    ),
    *(_repeats_on(day) for day in WEEKDAY_MAP),
)

MISSED_EVENT = BinarySensorEntityDescription(
    key="alarm_event_missed",
    name="Alarm Event Missed",
    device_class=BinarySensorDeviceClass.PROBLEM,
    entity_category=EntityCategory.DIAGNOSTIC,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IPhoneAlarmsSyncConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities([MissedEventSensor(coordinator, MISSED_EVENT)])
    async_add_alarm_entities(
        entry,
        async_add_entities,
        lambda alarm_id: (
            AlarmBinarySensor(coordinator, alarm_id, d) for d in ALARM_BINARY_SENSORS
        ),
    )


class AlarmBinarySensor(AlarmEntity, BinarySensorEntity):
    entity_description: AlarmBinarySensorDescription

    @property
    def is_on(self) -> bool | None:
        alarm = self.alarm
        return bool(self.entity_description.is_on_fn(alarm)) if alarm else None


class MissedEventSensor(PhoneEntity, BinarySensorEntity):
    """On when an alarm rang but its "goes off" event never reached HA."""

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.phone.missed_alarm_at)
