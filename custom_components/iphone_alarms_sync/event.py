"""Event entities: one per alarm, plus Any alarm, Wake-Up alarm and Sleep."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.event import EventEntity, EventEntityDescription
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    ALARM_EVENTS,
    EVENT_ALARM_EVENT,
    SLEEP_EVENTS,
    TRIGGER_SUBTYPE_ANY,
    TRIGGER_SUBTYPE_WAKEUP,
)
from .coordinator import IPhoneAlarmsSyncConfigEntry, IPhoneAlarmsSyncCoordinator
from .entity import AlarmEntity, PhoneEntity, async_add_alarm_entities


@dataclass(frozen=True, kw_only=True)
class PhoneEventDescription(EventEntityDescription):
    # The alarm_id the phone reports these events with; None takes any.
    scope: str | None


PHONE_EVENTS = (
    PhoneEventDescription(
        key="any_alarm",
        translation_key="any_alarm",
        event_types=list(ALARM_EVENTS),
        scope=TRIGGER_SUBTYPE_ANY,
    ),
    PhoneEventDescription(
        key="wakeup_alarm",
        translation_key="wakeup_alarm",
        event_types=list(ALARM_EVENTS),
        scope=TRIGGER_SUBTYPE_WAKEUP,
    ),
    PhoneEventDescription(
        key="sleep",
        translation_key="sleep",
        event_types=list(SLEEP_EVENTS),
        scope=None,
    ),
)
ALARM_EVENT = EventEntityDescription(
    key="alarm", translation_key="alarm", event_types=list(ALARM_EVENTS)
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IPhoneAlarmsSyncConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities(PhoneEvent(coordinator, d) for d in PHONE_EVENTS)
    async_add_alarm_entities(
        entry,
        async_add_entities,
        lambda alarm_id: [AlarmEvent(coordinator, alarm_id, ALARM_EVENT)],
    )


def _listen(
    entity: PhoneEvent | AlarmEvent,
    coordinator: IPhoneAlarmsSyncCoordinator,
    scope: str | None,
) -> None:
    """Show each matching event the phone reports."""
    phone_id = coordinator.phone.phone_id

    @callback
    def _matches(data: dict[str, Any]) -> bool:
        return (
            data["phone_id"] == phone_id
            and data["event"] in entity.event_types
            and scope in (None, data["alarm_id"])
        )

    @callback
    def _handle(event: Event[dict[str, Any]]) -> None:
        entity._trigger_event(event.data["event"])  # noqa: SLF001
        entity.async_write_ha_state()

    entity.async_on_remove(
        entity.hass.bus.async_listen(EVENT_ALARM_EVENT, _handle, event_filter=_matches)
    )


class PhoneEvent(PhoneEntity, EventEntity):
    entity_description: PhoneEventDescription

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        _listen(self, self.coordinator, self.entity_description.scope)


class AlarmEvent(AlarmEntity, EventEntity):
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        _listen(self, self.coordinator, self._alarm_id)
