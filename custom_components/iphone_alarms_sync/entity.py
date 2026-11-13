from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity, EntityDescription
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import (
    AlarmData,
    IPhoneAlarmsSyncConfigEntry,
    IPhoneAlarmsSyncCoordinator,
)


def parse_timestamp(value: str | None) -> datetime | None:
    return dt_util.parse_datetime(value) if value else None


class PhoneEntity(CoordinatorEntity[IPhoneAlarmsSyncCoordinator]):
    """Entity of the phone device."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: IPhoneAlarmsSyncCoordinator,
        description: EntityDescription,
    ) -> None:
        super().__init__(coordinator)
        entry_id = coordinator.entry.entry_id
        phone_id = coordinator.phone.phone_id
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{phone_id}_{description.key}"
        # The device itself is created in __init__.py.
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, phone_id)})


class AlarmEntity(CoordinatorEntity[IPhoneAlarmsSyncCoordinator]):
    """Entity of one alarm's device."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: IPhoneAlarmsSyncCoordinator,
        alarm_id: str,
        description: EntityDescription,
    ) -> None:
        super().__init__(coordinator)
        entry_id = coordinator.entry.entry_id
        phone_id = coordinator.phone.phone_id
        self._alarm_id = alarm_id
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{phone_id}_{alarm_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, phone_id, alarm_id)}  # type: ignore[arg-type]
        )

    @property
    def alarm(self) -> AlarmData | None:
        return self.coordinator.get_alarm(self._alarm_id)

    @property
    def available(self) -> bool:
        return super().available and self.alarm is not None


@callback
def async_add_alarm_entities(
    entry: IPhoneAlarmsSyncConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
    create: Callable[[str], Iterable[Entity]],
) -> None:
    """Add entities for every alarm now and for alarms a later sync adds."""
    coordinator = entry.runtime_data.coordinator
    known: set[str] = set()

    @callback
    def _add_new() -> None:
        alarms = coordinator.phone.alarms
        # A deleted alarm loses its device and entities; forget it so it can return.
        known.intersection_update(alarms)
        new = [alarm_id for alarm_id in alarms if alarm_id not in known]
        if not new:
            return
        known.update(new)
        async_add_entities([e for alarm_id in new for e in create(alarm_id)])

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))
