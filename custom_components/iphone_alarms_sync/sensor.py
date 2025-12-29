from __future__ import annotations

import json

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import IPhoneAlarmsSyncConfigEntry, IPhoneAlarmsSyncCoordinator

SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="time",
        name="Time",
        native_unit_of_measurement=None,
    ),
    SensorEntityDescription(
        key="repeat_days",
        name="Repeat Days",
        native_unit_of_measurement=None,
    ),
    SensorEntityDescription(
        key="last_sync",
        name="Last Sync",
        native_unit_of_measurement=None,
    ),
    SensorEntityDescription(
        key="last_event",
        name="Last Event",
        native_unit_of_measurement=None,
    ),
    SensorEntityDescription(
        key="last_event_at",
        name="Last Event At",
        native_unit_of_measurement=None,
    ),
    SensorEntityDescription(
        key="shortcut_snippet",
        name="Shortcut Snippet",
        native_unit_of_measurement=None,
    ),
)


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
        for description in SENSOR_TYPES:
            entities.append(
                IPhoneAlarmsSyncSensor(
                    coordinator,
                    entry,
                    phone.phone_id,
                    alarm_id,
                    description,
                )
            )

    async_add_entities(entities)


class IPhoneAlarmsSyncSensor(
    CoordinatorEntity[IPhoneAlarmsSyncCoordinator], SensorEntity
):
    def __init__(
        self,
        coordinator: IPhoneAlarmsSyncCoordinator,
        entry: IPhoneAlarmsSyncConfigEntry,
        phone_id: str,
        alarm_id: str,
        description: SensorEntityDescription,
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
    def native_value(self) -> str | None:
        alarm = self.coordinator.get_alarm(self._alarm_id)
        if not alarm:
            return None

        if self._description.key == "time":
            return f"{alarm.hour:02d}:{alarm.minute:02d}"

        if self._description.key == "repeat_days":
            return ",".join(alarm.repeat_days) if alarm.repeat_days else ""

        if self._description.key == "last_sync":
            return alarm.synced_at or None

        if self._description.key == "last_event":
            return alarm.last_event or None

        if self._description.key == "last_event_at":
            return alarm.last_event_at or None

        if self._description.key == "shortcut_snippet":
            payloads = {
                "sync_alarms": {
                    "phone_id": self._phone_id,
                    "alarms": [
                        {
                            "alarm_id": alarm.alarm_id,
                            "label": alarm.label,
                            "enabled": alarm.enabled,
                            "hour": alarm.hour,
                            "minute": alarm.minute,
                            "repeats": alarm.repeats,
                            "repeat_days": alarm.repeat_days,
                            "allows_snooze": alarm.allows_snooze,
                        }
                    ],
                },
                "report_alarm_event": {
                    "phone_id": self._phone_id,
                    "alarm_id": alarm.alarm_id,
                    "event": "goes_off",
                },
            }
            return json.dumps(payloads, indent=2)

        return None
