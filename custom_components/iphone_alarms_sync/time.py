from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import IPhoneAlarmsSyncConfigEntry, IPhoneAlarmsSyncCoordinator
from .utils import calculate_next_alarm_datetime


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

    for alarm_id, alarm in phone.alarms.items():
        entities.append(
            IPhoneAlarmsSyncAlarmTime(
                coordinator,
                entry,
                phone.phone_id,
                alarm_id,
            )
        )

    entities.append(
        IPhoneAlarmsSyncPhoneNextAlarmTime(
            coordinator,
            entry,
            phone.phone_id,
        )
    )

    async_add_entities(entities)


class IPhoneAlarmsSyncAlarmTime(
    CoordinatorEntity[IPhoneAlarmsSyncCoordinator], TimeEntity
):
    def __init__(
        self,
        coordinator: IPhoneAlarmsSyncCoordinator,
        entry: IPhoneAlarmsSyncConfigEntry,
        phone_id: str,
        alarm_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._phone_id = phone_id
        self._alarm_id = alarm_id
        self._attr_unique_id = f"{entry.entry_id}_{phone_id}_{alarm_id}_time"
        self._attr_assumed_state = False
        alarm = coordinator.get_alarm(alarm_id)
        if alarm is None:
            raise ValueError(f"Alarm {alarm_id} not found")
        phone = coordinator.get_phone()
        if phone is None:
            raise ValueError("Phone not found")
        self._attr_name = f"{phone.phone_name} {alarm.label} Time"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, phone_id, alarm_id)},
            name=f"{phone.phone_name} {alarm.label}",
            via_device=(DOMAIN, phone_id),
        )

    @property
    def native_value(self) -> time | None:
        alarm = self.coordinator.get_alarm(self._alarm_id)
        if not alarm:
            return None
        return time(hour=alarm.hour, minute=alarm.minute)


class IPhoneAlarmsSyncPhoneNextAlarmTime(
    CoordinatorEntity[IPhoneAlarmsSyncCoordinator], TimeEntity
):
    def __init__(
        self,
        coordinator: IPhoneAlarmsSyncCoordinator,
        entry: IPhoneAlarmsSyncConfigEntry,
        phone_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._phone_id = phone_id
        self._attr_unique_id = f"{entry.entry_id}_{phone_id}_next_alarm_time"
        self._attr_assumed_state = False
        phone = coordinator.get_phone()
        if phone is None:
            raise ValueError("Phone not found")
        self._attr_name = f"{phone.phone_name} Next Alarm Time"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, phone_id)},
            name=phone.phone_name,
        )

    def _get_next_alarm_time(self) -> time | None:
        phone = self.coordinator.get_phone()
        if not phone:
            return None

        next_dt, _ = calculate_next_alarm_datetime(phone)
        if next_dt is None:
            return None

        return next_dt.time()

    @property
    def native_value(self) -> time | None:
        return self._get_next_alarm_time()
