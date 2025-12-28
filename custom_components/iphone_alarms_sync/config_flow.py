from __future__ import annotations

import re
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import mobile_app
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import device_registry as dr

from .const import (
    CONF_MOBILE_APP_DEVICE,
    CONF_PHONE_ID,
    CONF_PHONE_NAME,
    DOMAIN,
)
from .coordinator import IPhoneAlarmsSyncConfigEntry

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_MOBILE_APP_DEVICE): vol.In([]),
        vol.Required(CONF_PHONE_NAME): str,
    }
)


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "_", text)
    return text.strip("_")


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    VERSION = 1

    def __init__(self) -> None:
        self.phone_name: str | None = None
        self.phone_id: str | None = None
        self.mobile_app_device_id: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is None:
            device_registry = dr.async_get(self.hass)
            mobile_app_devices = [
                device.id
                for device in device_registry.devices.values()
                if any(
                    entry.domain == mobile_app.DOMAIN
                    for entry_id in device.config_entries
                    if (entry := self.hass.config_entries.async_get_entry(entry_id))
                )
            ]

            schema = vol.Schema(
                {
                    vol.Optional(CONF_MOBILE_APP_DEVICE): vol.In(
                        {
                            device_id: device_registry.async_get(device_id).name
                            for device_id in mobile_app_devices
                        }
                        if mobile_app_devices
                        else {}
                    ),
                    vol.Required(CONF_PHONE_NAME): str,
                }
            )

            return self.async_show_form(step_id="user", data_schema=schema)

        self.phone_name = user_input[CONF_PHONE_NAME]
        self.mobile_app_device_id = user_input.get(CONF_MOBILE_APP_DEVICE)
        self.phone_id = slugify(self.phone_name)

        if self.mobile_app_device_id:
            device_registry = dr.async_get(self.hass)
            device = device_registry.async_get(self.mobile_app_device_id)
            if device:
                self.phone_name = device.name

        await self.async_set_unique_id(self.phone_id)
        self._abort_if_unique_id_configured()

        return await self.async_step_shortcuts()

    async def async_step_shortcuts(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="shortcuts",
                description_placeholders={
                    "phone_id": self.phone_id,
                },
            )

        return await self.async_step_wait_sync()

    async def async_step_wait_sync(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="wait_sync",
                description_placeholders={
                    "phone_id": self.phone_id,
                },
            )

        if user_input.get("skip"):
            return self.async_create_entry(
                title=self.phone_name,
                data={
                    CONF_PHONE_NAME: self.phone_name,
                    CONF_PHONE_ID: self.phone_id,
                    "mobile_app_device_id": self.mobile_app_device_id,
                },
            )

        return self.async_abort(reason="waiting_for_sync")

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: IPhoneAlarmsSyncConfigEntry,
    ) -> OptionsFlowHandler:
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: IPhoneAlarmsSyncConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "overview",
                "alarms",
                "events",
                "settings",
                "shortcuts",
                "delete",
            ],
        )

    async def async_step_overview(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        coordinator = self.config_entry.runtime_data.coordinator
        alarms = coordinator.get_all_alarms()
        last_sync = max(
            (alarm.synced_at for alarm in alarms.values() if alarm.synced_at),
            default=None,
        )
        recent_events = coordinator.get_events(limit=10)

        return self.async_show_form(
            step_id="overview",
            description_placeholders={
                "phone_name": self.config_entry.data[CONF_PHONE_NAME],
                "alarm_count": str(len(alarms)),
                "last_sync": last_sync or "Never",
                "recent_events": str(len(recent_events)),
            },
        )

    async def async_step_alarms(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        coordinator = self.config_entry.runtime_data.coordinator
        alarms = coordinator.get_all_alarms()

        if user_input is None:
            alarm_list = "\n".join(
                f"- {alarm.label} ({alarm_id})" for alarm_id, alarm in alarms.items()
            )
            return self.async_show_form(
                step_id="alarms",
                description_placeholders={"alarm_list": alarm_list or "No alarms"},
            )

        return await self.async_step_init()

    async def async_step_events(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        coordinator = self.config_entry.runtime_data.coordinator
        events = coordinator.get_events()

        if user_input is None:
            event_list = "\n".join(
                f"- {event.occurred_at}: {event.event} (alarm: {event.alarm_id})"
                for event in events[-20:]
            )
            return self.async_show_form(
                step_id="events",
                description_placeholders={"event_list": event_list or "No events"},
            )

        return await self.async_step_init()

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is None:
            device_registry = dr.async_get(self.hass)
            mobile_app_devices = {
                device.id: device.name
                for device in device_registry.devices.values()
                if any(
                    entry.domain == mobile_app.DOMAIN
                    for entry_id in device.config_entries
                    if (entry := self.hass.config_entries.async_get_entry(entry_id))
                )
            }

            schema = vol.Schema(
                {
                    vol.Required(
                        CONF_PHONE_NAME, default=self.config_entry.data[CONF_PHONE_NAME]
                    ): str,
                    vol.Optional(CONF_MOBILE_APP_DEVICE): vol.In(mobile_app_devices),
                }
            )

            return self.async_show_form(step_id="settings", data_schema=schema)

        updates = {CONF_PHONE_NAME: user_input[CONF_PHONE_NAME]}
        if CONF_MOBILE_APP_DEVICE in user_input:
            updates["mobile_app_device_id"] = user_input[CONF_MOBILE_APP_DEVICE]

        self.hass.config_entries.async_update_entry(self.config_entry, data=updates)
        return await self.async_step_init()

    async def async_step_shortcuts(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        return self.async_show_form(
            step_id="shortcuts",
            description_placeholders={
                "phone_id": self.config_entry.data[CONF_PHONE_ID],
            },
        )

    async def async_step_delete(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is None:
            return self.async_show_form(step_id="delete")

        if user_input.get("confirm"):
            await self.hass.config_entries.async_remove(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        return await self.async_step_init()

