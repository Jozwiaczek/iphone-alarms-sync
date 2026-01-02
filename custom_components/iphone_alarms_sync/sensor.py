from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import cast

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import IPhoneAlarmsSyncConfigEntry, IPhoneAlarmsSyncCoordinator
from .utils import calculate_next_alarm_datetime, calculate_next_occurrence

ALARM_SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="next_occurrence_datetime",
        name="Next Occurrence",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="last_occurrence_datetime",
        name="Last Occurrence",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
)

ALARM_EVENT_SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="last_event_goes_off_at",
        name="Last Goes Off At",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="last_event_snoozed_at",
        name="Last Snoozed At",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="last_event_stopped_at",
        name="Last Stopped At",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
)

PHONE_EVENT_SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="wakeup_last_event_goes_off_at",
        name="Wake-Up Last Goes Off At",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="wakeup_last_event_snoozed_at",
        name="Wake-Up Last Snoozed At",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="wakeup_last_event_stopped_at",
        name="Wake-Up Last Stopped At",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="any_last_event_goes_off_at",
        name="Any Last Goes Off At",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="any_last_event_snoozed_at",
        name="Any Last Snoozed At",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="any_last_event_stopped_at",
        name="Any Last Stopped At",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="bedtime_last_event_at",
        name="Bedtime Last At",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="waking_up_last_event_at",
        name="Waking Up Last At",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="wind_down_last_event_at",
        name="Wind Down Last At",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
)

PHONE_SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="next_alarm_datetime",
        name="Next Alarm",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="next_alarm_label",
        name="Next Alarm Label",
    ),
    SensorEntityDescription(
        key="last_alarm_datetime",
        name="Last Alarm",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="last_sync",
        name="Last Sync",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="enabled_alarms",
        name="Enabled Alarms",
    ),
    SensorEntityDescription(
        key="total_alarms",
        name="Total Alarms",
    ),
    SensorEntityDescription(
        key="disabled_alarms",
        name="Disabled Alarms",
    ),
)


def _create_alarm_sensor_entities(
    coordinator: IPhoneAlarmsSyncCoordinator,
    entry: IPhoneAlarmsSyncConfigEntry,
    phone_id: str,
    alarm_id: str,
) -> list[IPhoneAlarmsSyncAlarmSensor]:
    entities = []
    for description in ALARM_SENSOR_TYPES:
        entities.append(
            IPhoneAlarmsSyncAlarmSensor(
                coordinator,
                entry,
                phone_id,
                alarm_id,
                description,
            )
        )
    alarm = coordinator.get_alarm(alarm_id)
    if alarm:
        for description in ALARM_EVENT_SENSOR_TYPES:
            has_value = False
            if (
                description.key == "last_event_goes_off_at"
                and alarm.last_event_goes_off_at
            ):
                has_value = True
            elif (
                description.key == "last_event_snoozed_at"
                and alarm.last_event_snoozed_at
            ):
                has_value = True
            elif (
                description.key == "last_event_stopped_at"
                and alarm.last_event_stopped_at
            ):
                has_value = True
            if has_value:
                entities.append(
                    IPhoneAlarmsSyncAlarmSensor(
                        coordinator,
                        entry,
                        phone_id,
                        alarm_id,
                        description,
                    )
                )
    return entities


def _create_phone_sensor_entities(
    coordinator: IPhoneAlarmsSyncCoordinator,
    entry: IPhoneAlarmsSyncConfigEntry,
    phone_id: str,
) -> list[IPhoneAlarmsSyncPhoneSensor]:
    entities = []
    for description in PHONE_SENSOR_TYPES:
        entities.append(
            IPhoneAlarmsSyncPhoneSensor(
                coordinator,
                entry,
                phone_id,
                description,
            )
        )
    return entities


def _create_phone_event_sensor_entities(
    coordinator: IPhoneAlarmsSyncCoordinator,
    entry: IPhoneAlarmsSyncConfigEntry,
    phone_id: str,
) -> list[IPhoneAlarmsSyncPhoneSensor]:
    entities: list[IPhoneAlarmsSyncPhoneSensor] = []
    phone = coordinator.get_phone()
    if not phone:
        return entities
    for description in PHONE_EVENT_SENSOR_TYPES:
        has_value = False
        if (
            description.key == "wakeup_last_event_goes_off_at"
            and phone.wakeup_last_event_goes_off_at
        ):
            has_value = True
        elif (
            description.key == "wakeup_last_event_snoozed_at"
            and phone.wakeup_last_event_snoozed_at
        ):
            has_value = True
        elif (
            description.key == "wakeup_last_event_stopped_at"
            and phone.wakeup_last_event_stopped_at
        ):
            has_value = True
        elif (
            description.key == "any_last_event_goes_off_at"
            and phone.any_last_event_goes_off_at
        ):
            has_value = True
        elif (
            description.key == "any_last_event_snoozed_at"
            and phone.any_last_event_snoozed_at
        ):
            has_value = True
        elif (
            description.key == "any_last_event_stopped_at"
            and phone.any_last_event_stopped_at
        ):
            has_value = True
        elif description.key == "bedtime_last_event_at" and phone.bedtime_last_event_at:
            has_value = True
        elif (
            description.key == "waking_up_last_event_at"
            and phone.waking_up_last_event_at
        ):
            has_value = True
        elif (
            description.key == "wind_down_last_event_at"
            and phone.wind_down_last_event_at
        ):
            has_value = True
        if has_value:
            entities.append(
                IPhoneAlarmsSyncPhoneSensor(
                    coordinator,
                    entry,
                    phone_id,
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
    hass.data[DOMAIN][entry.entry_id]["sensor_add_entities"] = async_add_entities

    for alarm_id, alarm in phone.alarms.items():
        entities.extend(
            _create_alarm_sensor_entities(coordinator, entry, phone.phone_id, alarm_id)
        )

    entities.extend(_create_phone_sensor_entities(coordinator, entry, phone.phone_id))
    entities.extend(
        _create_phone_event_sensor_entities(coordinator, entry, phone.phone_id)
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
        self._unsub_refresh: callback.CALLBACK_TYPE | None = None
        self._is_refreshing = False
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

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self._description.key == "next_occurrence_datetime":
            self._setup_refresh_timer()

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub_refresh:
            self._unsub_refresh()
            self._unsub_refresh = None
        await super().async_will_remove_from_hass()

    @callback
    def _handle_coordinator_update(self) -> None:
        super()._handle_coordinator_update()
        if self._description.key == "next_occurrence_datetime":
            self._setup_refresh_timer()

    def _get_next_occurrence_datetime(self) -> datetime | None:
        alarm = self.coordinator.get_alarm(self._alarm_id)
        if not alarm:
            return None
        return calculate_next_occurrence(alarm)

    def _setup_refresh_timer(self) -> None:
        if self._is_refreshing:
            return
        if self._unsub_refresh:
            self._unsub_refresh()
            self._unsub_refresh = None

        next_dt = self._get_next_occurrence_datetime()
        if next_dt is None:
            return

        now = dt_util.utcnow()
        if next_dt <= now:
            self._update_last_occurrence(next_dt)
            self._is_refreshing = True
            delayed_time = now + timedelta(seconds=0.1)
            self._unsub_refresh = async_track_point_in_time(
                self.hass,
                self._delayed_refresh,
                delayed_time,
            )
            return

        self._unsub_refresh = async_track_point_in_time(
            self.hass,
            self._refresh_callback,
            next_dt,
        )

    @callback
    def _delayed_refresh(self, _now: datetime) -> None:
        self._is_refreshing = False
        self.async_write_ha_state()
        self._setup_refresh_timer()

    @callback
    def _refresh_callback(self, now: datetime) -> None:
        self._update_last_occurrence(now)
        self.async_write_ha_state()
        self._setup_refresh_timer()

    def _update_last_occurrence(self, alarm_time: datetime) -> None:
        alarm = self.coordinator.get_alarm(self._alarm_id)
        if alarm:
            alarm.last_occurrence_datetime = alarm_time.isoformat()
            self.coordinator._save_to_config()

    @property
    def native_value(self) -> datetime | None:
        alarm = self.coordinator.get_alarm(self._alarm_id)
        if not alarm:
            return None

        if self._description.key == "last_event_goes_off_at":
            timestamp_str = cast(str | None, alarm.last_event_goes_off_at)
            return dt_util.parse_datetime(timestamp_str) if timestamp_str else None

        if self._description.key == "last_event_snoozed_at":
            timestamp_str = cast(str | None, alarm.last_event_snoozed_at)
            return dt_util.parse_datetime(timestamp_str) if timestamp_str else None

        if self._description.key == "last_event_stopped_at":
            timestamp_str = cast(str | None, alarm.last_event_stopped_at)
            return dt_util.parse_datetime(timestamp_str) if timestamp_str else None

        if self._description.key == "next_occurrence_datetime":
            return self._get_next_occurrence_datetime()

        if self._description.key == "last_occurrence_datetime":
            timestamp_str = cast(str | None, alarm.last_occurrence_datetime)
            return dt_util.parse_datetime(timestamp_str) if timestamp_str else None

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
        self._unsub_refresh: callback.CALLBACK_TYPE | None = None
        self._scheduled_alarm_datetime: datetime | None = None
        self._scheduled_alarm_id: str | None = None
        self._is_refreshing = False
        phone = coordinator.get_phone()
        if phone is None:
            raise ValueError("Phone not found")
        self._attr_name = f"{phone.phone_name} {description.name}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, phone_id)},
            name=phone.phone_name,
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self._description.key == "next_alarm_datetime":
            self._setup_refresh_timer()

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub_refresh:
            self._unsub_refresh()
            self._unsub_refresh = None
        await super().async_will_remove_from_hass()

    @callback
    def _handle_coordinator_update(self) -> None:
        super()._handle_coordinator_update()
        if self._description.key == "next_alarm_datetime":
            self._setup_refresh_timer()

    def _get_next_alarm_datetime(self) -> tuple[datetime | None, str | None]:
        phone = self.coordinator.get_phone()
        if not phone:
            return None, None
        return calculate_next_alarm_datetime(phone)

    def _setup_refresh_timer(self) -> None:
        if self._is_refreshing:
            return
        if self._unsub_refresh:
            self._unsub_refresh()
            self._unsub_refresh = None

        next_dt, next_alarm_id = self._get_next_alarm_datetime()
        if next_dt is None:
            return

        now = dt_util.utcnow()
        if next_dt <= now:
            phone = self.coordinator.get_phone()
            if phone and next_alarm_id:
                phone.last_alarm_datetime = next_dt.isoformat()
                phone.last_alarm_id = next_alarm_id
                self.coordinator._save_to_config()
            self._is_refreshing = True
            delayed_time = now + timedelta(seconds=0.1)
            self._unsub_refresh = async_track_point_in_time(
                self.hass,
                self._delayed_refresh,
                delayed_time,
            )
            return

        self._scheduled_alarm_datetime = next_dt
        self._scheduled_alarm_id = next_alarm_id
        self._unsub_refresh = async_track_point_in_time(
            self.hass,
            self._refresh_callback,
            next_dt,
        )

    @callback
    def _delayed_refresh(self, _now: datetime) -> None:
        self._is_refreshing = False
        self.async_write_ha_state()
        self._setup_refresh_timer()

    @callback
    def _refresh_callback(self, now: datetime) -> None:
        phone = self.coordinator.get_phone()
        if phone and self._scheduled_alarm_id and self._scheduled_alarm_datetime:
            phone.last_alarm_datetime = self._scheduled_alarm_datetime.isoformat()
            phone.last_alarm_id = self._scheduled_alarm_id
            self.coordinator._save_to_config()
        self.async_write_ha_state()
        self._setup_refresh_timer()

    def _get_next_alarm(self) -> tuple[time | None, str | None]:
        phone = self.coordinator.get_phone()
        if not phone:
            return None, None

        now = dt_util.utcnow()
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
    def native_value(self) -> datetime | str | int | None:
        phone = self.coordinator.get_phone()
        if not phone:
            return None

        if self._description.key == "last_sync":
            timestamp_str = cast(str | None, phone.synced_at)
            return dt_util.parse_datetime(timestamp_str) if timestamp_str else None

        if self._description.key == "total_alarms":
            return len(phone.alarms)

        if self._description.key == "enabled_alarms":
            return sum(1 for alarm in phone.alarms.values() if alarm.enabled)

        if self._description.key == "disabled_alarms":
            return sum(1 for alarm in phone.alarms.values() if not alarm.enabled)

        if self._description.key == "next_alarm_label":
            _, label = self._get_next_alarm()
            return label

        if self._description.key == "next_alarm_datetime":
            next_dt, _ = self._get_next_alarm_datetime()
            return next_dt

        if self._description.key == "last_alarm_datetime":
            timestamp_str = cast(str | None, phone.last_alarm_datetime)
            return dt_util.parse_datetime(timestamp_str) if timestamp_str else None

        if self._description.key == "wakeup_last_event_goes_off_at":
            timestamp_str = cast(str | None, phone.wakeup_last_event_goes_off_at)
            return dt_util.parse_datetime(timestamp_str) if timestamp_str else None

        if self._description.key == "wakeup_last_event_snoozed_at":
            timestamp_str = cast(str | None, phone.wakeup_last_event_snoozed_at)
            return dt_util.parse_datetime(timestamp_str) if timestamp_str else None

        if self._description.key == "wakeup_last_event_stopped_at":
            timestamp_str = cast(str | None, phone.wakeup_last_event_stopped_at)
            return dt_util.parse_datetime(timestamp_str) if timestamp_str else None

        if self._description.key == "any_last_event_goes_off_at":
            timestamp_str = cast(str | None, phone.any_last_event_goes_off_at)
            return dt_util.parse_datetime(timestamp_str) if timestamp_str else None

        if self._description.key == "any_last_event_snoozed_at":
            timestamp_str = cast(str | None, phone.any_last_event_snoozed_at)
            return dt_util.parse_datetime(timestamp_str) if timestamp_str else None

        if self._description.key == "any_last_event_stopped_at":
            timestamp_str = cast(str | None, phone.any_last_event_stopped_at)
            return dt_util.parse_datetime(timestamp_str) if timestamp_str else None

        if self._description.key == "bedtime_last_event_at":
            timestamp_str = cast(str | None, phone.bedtime_last_event_at)
            return dt_util.parse_datetime(timestamp_str) if timestamp_str else None

        if self._description.key == "waking_up_last_event_at":
            timestamp_str = cast(str | None, phone.waking_up_last_event_at)
            return dt_util.parse_datetime(timestamp_str) if timestamp_str else None

        if self._description.key == "wind_down_last_event_at":
            timestamp_str = cast(str | None, phone.wind_down_last_event_at)
            return dt_util.parse_datetime(timestamp_str) if timestamp_str else None

        return None
