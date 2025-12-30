from __future__ import annotations

from datetime import datetime, time
from typing import cast

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import IPhoneAlarmsSyncConfigEntry, IPhoneAlarmsSyncCoordinator

ALARM_SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="last_event_goes_off_at",
        name="Last Event Goes Off At",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="last_event_snoozed_at",
        name="Last Event Snoozed At",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="last_event_stopped_at",
        name="Last Event Stopped At",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
)

PHONE_SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="last_sync",
        name="Last Sync",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="total_alarms",
        name="Total Alarms",
    ),
    SensorEntityDescription(
        key="enabled_alarms",
        name="Enabled Alarms",
    ),
    SensorEntityDescription(
        key="disabled_alarms",
        name="Disabled Alarms",
    ),
    SensorEntityDescription(
        key="next_alarm_label",
        name="Next Alarm Label",
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
        for description in ALARM_SENSOR_TYPES:
            entities.append(
                IPhoneAlarmsSyncAlarmSensor(
                    coordinator,
                    entry,
                    phone.phone_id,
                    alarm_id,
                    description,
                )
            )

    for description in PHONE_SENSOR_TYPES:
        entities.append(
            IPhoneAlarmsSyncPhoneSensor(
                coordinator,
                entry,
                phone.phone_id,
                description,
            )
        )

    async_add_entities(entities)


class IPhoneAlarmsSyncAlarmSensor(
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

        if self._description.key == "last_event_goes_off_at":
            return cast(str | None, alarm.last_event_goes_off_at)

        if self._description.key == "last_event_snoozed_at":
            return cast(str | None, alarm.last_event_snoozed_at)

        if self._description.key == "last_event_stopped_at":
            return cast(str | None, alarm.last_event_stopped_at)

        return None


class IPhoneAlarmsSyncPhoneSensor(
    CoordinatorEntity[IPhoneAlarmsSyncCoordinator], SensorEntity
):
    def __init__(
        self,
        coordinator: IPhoneAlarmsSyncCoordinator,
        entry: IPhoneAlarmsSyncConfigEntry,
        phone_id: str,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._phone_id = phone_id
        self._description = description
        self._attr_unique_id = f"{entry.entry_id}_{phone_id}_{description.key}"
        phone = coordinator.get_phone()
        if phone is None:
            raise ValueError("Phone not found")
        self._attr_name = f"{phone.phone_name} {description.name}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, phone_id)},
            name=phone.phone_name,
        )

    def _get_next_alarm(self) -> tuple[time | None, str | None]:
        phone = self.coordinator.get_phone()
        if not phone:
            return None, None

        now = datetime.now()
        current_time = now.time()
        current_weekday = now.weekday()

        next_alarm_time: time | None = None
        next_alarm_label: str | None = None
        min_days_ahead = 7

        weekday_map = {
            "Monday": 0,
            "Tuesday": 1,
            "Wednesday": 2,
            "Thursday": 3,
            "Friday": 4,
            "Saturday": 5,
            "Sunday": 6,
        }

        for alarm in phone.alarms.values():
            if not alarm.enabled:
                continue

            alarm_time = time(hour=alarm.hour, minute=alarm.minute)

            if alarm.repeats and alarm.repeat_days:
                for day_name in alarm.repeat_days:
                    day_num = weekday_map.get(day_name)
                    if day_num is None:
                        continue

                    days_ahead = (day_num - current_weekday) % 7
                    if days_ahead == 0 and alarm_time > current_time:
                        if next_alarm_time is None or alarm_time < next_alarm_time:
                            next_alarm_time = alarm_time
                            next_alarm_label = alarm.label
                            min_days_ahead = 0
                    elif days_ahead > 0:
                        if days_ahead < min_days_ahead or (
                            days_ahead == min_days_ahead
                            and (
                                next_alarm_time is None or alarm_time < next_alarm_time
                            )
                        ):
                            next_alarm_time = alarm_time
                            next_alarm_label = alarm.label
                            min_days_ahead = days_ahead
            else:
                if alarm_time > current_time:
                    if next_alarm_time is None or alarm_time < next_alarm_time:
                        next_alarm_time = alarm_time
                        next_alarm_label = alarm.label
                        min_days_ahead = 0

        return next_alarm_time, next_alarm_label

    @property
    def native_value(self) -> str | int | None:
        phone = self.coordinator.get_phone()
        if not phone:
            return None

        if self._description.key == "last_sync":
            return cast(str | None, phone.synced_at)

        if self._description.key == "total_alarms":
            return len(phone.alarms)

        if self._description.key == "enabled_alarms":
            return sum(1 for alarm in phone.alarms.values() if alarm.enabled)

        if self._description.key == "disabled_alarms":
            return sum(1 for alarm in phone.alarms.values() if not alarm.enabled)

        if self._description.key == "next_alarm_label":
            _, label = self._get_next_alarm()
            return label

        return None
