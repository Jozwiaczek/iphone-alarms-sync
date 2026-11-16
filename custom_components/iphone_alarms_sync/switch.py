from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import IPhoneAlarmsSyncConfigEntry
from .entity import AlarmEntity, async_add_alarm_entities

ESTIMATE_GOES_OFF = SwitchEntityDescription(
    key="estimate_goes_off",
    translation_key="estimate_goes_off",
    entity_category=EntityCategory.CONFIG,
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
        lambda alarm_id: [
            EstimateGoesOffSwitch(coordinator, alarm_id, ESTIMATE_GOES_OFF)
        ],
    )


class EstimateGoesOffSwitch(AlarmEntity, SwitchEntity):
    """Fire "goes off" at the alarm's time, without an event shortcut."""

    @property
    def is_on(self) -> bool | None:
        alarm = self.alarm
        return alarm.estimate_goes_off if alarm else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._set(False)

    def _set(self, value: bool) -> None:
        if alarm := self.alarm:
            alarm.estimate_goes_off = value
            self.coordinator.save()
            self.coordinator.async_set_updated_data(self.coordinator.phone)
