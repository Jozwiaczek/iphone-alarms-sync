"""Triggers like "Alarm goes off" for one or more alarms at once."""

from __future__ import annotations

from typing import override

from homeassistant.components.event import (
    DOMAIN as EVENT_DOMAIN,
)
from homeassistant.components.event import (
    EventEntityStateAttribute,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.automation import DomainSpec
from homeassistant.helpers.trigger import (
    NotTriggeredReasonReporter,
    StatelessEntityTriggerBase,
    Trigger,
)

from .const import ALARM_EVENTS, DOMAIN


def _alarm_trigger(event_type: str) -> type[Trigger]:
    class AlarmEventTrigger(StatelessEntityTriggerBase):
        _domain_specs = {EVENT_DOMAIN: DomainSpec()}

        @override
        def entity_filter(self, entities: set[str]) -> set[str]:
            # An area or label target may hold event entities of other integrations.
            registry = er.async_get(self._hass)
            return {
                entity_id
                for entity_id in super().entity_filter(entities)
                if (entry := registry.async_get(entity_id)) and entry.platform == DOMAIN
            }

        @override
        def is_valid_state(
            self, state: State, report_not_triggered: NotTriggeredReasonReporter
        ) -> bool:
            return (
                state.attributes.get(EventEntityStateAttribute.EVENT_TYPE) == event_type
            )

    return AlarmEventTrigger


TRIGGERS: dict[str, type[Trigger]] = {e: _alarm_trigger(e) for e in ALARM_EVENTS}


async def async_get_triggers(hass: HomeAssistant) -> dict[str, type[Trigger]]:
    return TRIGGERS
