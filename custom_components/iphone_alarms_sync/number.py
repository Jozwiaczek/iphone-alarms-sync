from __future__ import annotations

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import IPhoneAlarmsSyncConfigEntry
from .entity import AlarmEntity, async_add_alarm_entities

SNOOZE_TIME = NumberEntityDescription(
    key="snooze_time",
    name="Snooze Time",
    native_min_value=1,
    native_max_value=30,
    native_step=1,
    native_unit_of_measurement=UnitOfTime.MINUTES,
    mode=NumberMode.BOX,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IPhoneAlarmsSyncConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_alarm_entities(
        entry,
        async_add_entities,
        lambda alarm_id: [SnoozeTimeNumber(coordinator, alarm_id, SNOOZE_TIME)],
    )


class SnoozeTimeNumber(AlarmEntity, NumberEntity):
    @property
    def native_value(self) -> int | None:
        alarm = self.alarm
        if alarm is None or not alarm.allows_snooze:
            return None
        return int(alarm.snooze_time)

    async def async_set_native_value(self, value: float) -> None:
        alarm = self.alarm
        if alarm is None or not alarm.allows_snooze:
            raise ServiceValidationError(
                "This alarm does not allow snooze; turn on Snooze for it on the "
                "phone and run the Sync shortcut."
            )
        alarm.snooze_time = int(value)
        self.coordinator.save()
        self.coordinator.async_set_updated_data(self.coordinator.phone)
