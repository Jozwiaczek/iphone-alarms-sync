from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import IPhoneAlarmsSyncConfigEntry, IPhoneAlarmsSyncCoordinator

BINARY_SENSOR_TYPES: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key="enabled",
        name="Enabled",
    ),
    BinarySensorEntityDescription(
        key="repeats",
        name="Repeats",
    ),
    BinarySensorEntityDescription(
        key="allows_snooze",
        name="Allows Snooze",
    ),
    BinarySensorEntityDescription(
        key="repeats_monday",
        name="Repeats Monday",
    ),
    BinarySensorEntityDescription(
        key="repeats_tuesday",
        name="Repeats Tuesday",
    ),
    BinarySensorEntityDescription(
        key="repeats_wednesday",
        name="Repeats Wednesday",
    ),
    BinarySensorEntityDescription(
        key="repeats_thursday",
        name="Repeats Thursday",
    ),
    BinarySensorEntityDescription(
        key="repeats_friday",
        name="Repeats Friday",
    ),
    BinarySensorEntityDescription(
        key="repeats_saturday",
        name="Repeats Saturday",
    ),
    BinarySensorEntityDescription(
        key="repeats_sunday",
        name="Repeats Sunday",
    ),
)


def _create_binary_sensor_entities(
    coordinator: IPhoneAlarmsSyncCoordinator,
    entry: IPhoneAlarmsSyncConfigEntry,
    phone_id: str,
    alarm_id: str,
) -> list[IPhoneAlarmsSyncBinarySensor]:
    entities = []
    for description in BINARY_SENSOR_TYPES:
        entities.append(
            IPhoneAlarmsSyncBinarySensor(
                coordinator,
                entry,
                phone_id,
                alarm_id,
                description,
            )
        )
    return entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IPhoneAlarmsSyncConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data.coordinator
    entities = []

    phone = coordinator.get_phone()
    if not phone:
        return

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(entry.entry_id, {})
    hass.data[DOMAIN][entry.entry_id]["binary_sensor_add_entities"] = async_add_entities

    for alarm_id, alarm in phone.alarms.items():
        entities.extend(
            _create_binary_sensor_entities(coordinator, entry, phone.phone_id, alarm_id)
        )

    async_add_entities(entities)


class IPhoneAlarmsSyncBinarySensor(
    CoordinatorEntity[IPhoneAlarmsSyncCoordinator], BinarySensorEntity
):
    def __init__(
        self,
        coordinator: IPhoneAlarmsSyncCoordinator,
        entry: IPhoneAlarmsSyncConfigEntry,
        phone_id: str,
        alarm_id: str,
        description: BinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._phone_id = phone_id
        self._alarm_id = alarm_id
        self._description = description
        self._attr_unique_id = (
            f"{entry.entry_id}_{phone_id}_{alarm_id}_{description.key}"
        )
        alarm = coordinator.get_alarm(alarm_id)
        if alarm is None:
            raise ValueError(f"Alarm {alarm_id} not found")
        phone = coordinator.get_phone()
        if phone is None:
            raise ValueError("Phone not found")
        self._attr_name = f"{phone.phone_name} {alarm.label} {description.name}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, phone_id, alarm_id)},
            name=f"{phone.phone_name} {alarm.label}",
            via_device=(DOMAIN, phone_id),
        )

    @property
    def is_on(self) -> bool | None:
        alarm = self.coordinator.get_alarm(self._alarm_id)
        if not alarm:
            return None
        if self._description.key == "enabled":
            return bool(alarm.enabled)
        if self._description.key == "repeats":
            return bool(alarm.repeats)
        if self._description.key == "allows_snooze":
            return bool(alarm.allows_snooze)
        if self._description.key == "repeats_monday":
            return "Monday" in alarm.repeat_days
        if self._description.key == "repeats_tuesday":
            return "Tuesday" in alarm.repeat_days
        if self._description.key == "repeats_wednesday":
            return "Wednesday" in alarm.repeat_days
        if self._description.key == "repeats_thursday":
            return "Thursday" in alarm.repeat_days
        if self._description.key == "repeats_friday":
            return "Friday" in alarm.repeat_days
        if self._description.key == "repeats_saturday":
            return "Saturday" in alarm.repeat_days
        if self._description.key == "repeats_sunday":
            return "Sunday" in alarm.repeat_days
        return None
