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
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IPhoneAlarmsSyncConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data.coordinator
    entities = []

    for alarm_id, alarm in coordinator.get_all_alarms().items():
        for description in BINARY_SENSOR_TYPES:
            entities.append(
                IPhoneAlarmsSyncBinarySensor(
                    coordinator,
                    entry,
                    alarm_id,
                    description,
                )
            )

    async_add_entities(entities)


class IPhoneAlarmsSyncBinarySensor(
    CoordinatorEntity[IPhoneAlarmsSyncCoordinator], BinarySensorEntity
):
    def __init__(
        self,
        coordinator: IPhoneAlarmsSyncCoordinator,
        entry: IPhoneAlarmsSyncConfigEntry,
        alarm_id: str,
        description: BinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._alarm_id = alarm_id
        self._description = description
        self._attr_unique_id = f"{entry.entry_id}_{alarm_id}_{description.key}"
        alarm = coordinator.get_alarm(alarm_id)
        if alarm is None:
            raise ValueError(f"Alarm {alarm_id} not found")
        self._attr_name = f"{coordinator.phone_name} {alarm.label} {description.name}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.phone_id, alarm_id)},
            name=f"{coordinator.phone_name} {alarm.label}",
            via_device=(DOMAIN, coordinator.phone_id),
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
        return None
