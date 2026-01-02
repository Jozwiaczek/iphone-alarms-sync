from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import IPhoneAlarmsSyncConfigEntry, IPhoneAlarmsSyncCoordinator

NUMBER_SENSOR_TYPES: tuple[NumberEntityDescription, ...] = (
    NumberEntityDescription(
        key="snooze_time",
        name="Snooze Time",
        native_min_value=1,
        native_max_value=30,
        native_step=1,
        native_unit_of_measurement="min",
    ),
)


def _create_number_entities(
    coordinator: IPhoneAlarmsSyncCoordinator,
    entry: IPhoneAlarmsSyncConfigEntry,
    phone_id: str,
    alarm_id: str,
) -> list[IPhoneAlarmsSyncSnoozeNumber]:
    entities = []
    for description in NUMBER_SENSOR_TYPES:
        entities.append(
            IPhoneAlarmsSyncSnoozeNumber(
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
    hass.data[DOMAIN][entry.entry_id]["number_add_entities"] = async_add_entities

    for alarm_id, alarm in phone.alarms.items():
        entities.extend(
            _create_number_entities(coordinator, entry, phone.phone_id, alarm_id)
        )

    async_add_entities(entities)


class IPhoneAlarmsSyncSnoozeNumber(
    CoordinatorEntity[IPhoneAlarmsSyncCoordinator], NumberEntity
):
    def __init__(
        self,
        coordinator: IPhoneAlarmsSyncCoordinator,
        entry: IPhoneAlarmsSyncConfigEntry,
        phone_id: str,
        alarm_id: str,
        description: NumberEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._phone_id = phone_id
        self._alarm_id = alarm_id
        self.entity_description = description
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
        self._attr_mode = "box"

    @property
    def native_value(self) -> int | None:
        alarm = self.coordinator.get_alarm(self._alarm_id)
        if not alarm:
            return None
        if not alarm.allows_snooze:
            return None
        return int(alarm.snooze_time)

    async def async_set_native_value(self, value: float) -> None:
        alarm = self.coordinator.get_alarm(self._alarm_id)
        if not alarm:
            return
        if not alarm.allows_snooze:
            return
        self.coordinator.update_alarm_snooze_time(self._alarm_id, int(value))
        phone = self.coordinator.get_phone()
        if phone:
            self.coordinator.async_set_updated_data(phone)
        self.async_write_ha_state()
