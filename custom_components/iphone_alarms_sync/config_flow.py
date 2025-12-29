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
    CONF_MOBILE_APP_DEVICE_ID,
    CONF_PHONE_ID,
    CONF_PHONE_NAME,
    DOMAIN,
)
from .coordinator import (
    IPhoneAlarmsSyncConfigEntry,
    IPhoneAlarmsSyncCoordinator,
)


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "_", text)
    return text.strip("_")


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors: dict[str, str] = {}

        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_PHONE_NAME): str,
                    }
                ),
                errors=errors,
            )

        phone_name = user_input.get(CONF_PHONE_NAME, "").strip()
        if not phone_name:
            errors["base"] = "required"
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_PHONE_NAME): str,
                    }
                ),
                errors=errors,
            )

        phone_id = slugify(phone_name)
        phones_dict = {
            phone_id: {
                CONF_PHONE_ID: phone_id,
                CONF_PHONE_NAME: phone_name,
                CONF_MOBILE_APP_DEVICE_ID: None,
                "alarms": {},
            }
        }

        return self.async_create_entry(
            title="iPhone Alarms Sync",
            data={},
            options={"phones": phones_dict},
            description_placeholders={"phone_id": phone_id},
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: IPhoneAlarmsSyncConfigEntry,
    ) -> OptionsFlowHandler:
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlowWithConfigEntry):
    def __init__(self) -> None:
        super().__init__()
        self.selected_phone_id: str | None = None

    def _get_coordinator(self) -> IPhoneAlarmsSyncCoordinator | None:
        if (
            not hasattr(self.config_entry, "runtime_data")
            or not self.config_entry.runtime_data
        ):
            return None
        return self.config_entry.runtime_data.coordinator  # type: ignore[no-any-return]

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        coordinator = self._get_coordinator()
        if coordinator is None:
            return self.async_abort(reason="integration_not_ready")
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "manage_devices",
                "overview",
                "events",
                "shortcuts",
            ],
        )

    async def async_step_manage_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        coordinator = self._get_coordinator()
        if coordinator is None:
            return self.async_abort(reason="integration_not_ready")
        phones = coordinator.get_all_phones()

        if not phones:
            return await self.async_step_add_device()

        menu_options = {"add_device": "Add New Device"}
        for phone_id, phone in phones.items():
            menu_options[f"edit_{phone_id}"] = f"Edit: {phone.phone_name}"
            menu_options[f"delete_{phone_id}"] = f"Delete: {phone.phone_name}"

        if user_input is None:
            phone_list = "\n".join(
                f"- {phone.phone_name} ({phone_id})"
                for phone_id, phone in phones.items()
            )
            return self.async_show_menu(
                step_id="manage_devices",
                menu_options=menu_options,
                description_placeholders={"phone_list": phone_list},
            )

        selected = user_input.get("next_step_id")
        if selected == "add_device":
            return await self.async_step_add_device()
        elif selected and selected.startswith("edit_"):
            self.selected_phone_id = selected.replace("edit_", "")
            return await self.async_step_edit_device()
        elif selected and selected.startswith("delete_"):
            self.selected_phone_id = selected.replace("delete_", "")
            return await self.async_step_delete_device()

        return await self.async_step_init()

    async def async_step_add_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        coordinator = self._get_coordinator()
        if coordinator is None:
            return self.async_abort(reason="integration_not_ready")
        existing_phones = coordinator.get_all_phones()

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

        device_options = {None: "None"}
        for device_id in mobile_app_devices:
            device = device_registry.async_get(device_id)
            if device:
                device_options[device.id] = device.name

        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Required(CONF_PHONE_NAME): str,
                    vol.Optional(CONF_MOBILE_APP_DEVICE_ID, default=None): vol.In(
                        device_options
                    ),
                }
            )
            return self.async_show_form(
                step_id="add_device", data_schema=schema, errors=errors
            )

        phone_name = user_input.get(CONF_PHONE_NAME, "").strip()
        if not phone_name:
            errors["base"] = "required"
            schema = vol.Schema(
                {
                    vol.Required(CONF_PHONE_NAME): str,
                    vol.Optional(CONF_MOBILE_APP_DEVICE_ID, default=None): vol.In(
                        device_options
                    ),
                }
            )
            return self.async_show_form(
                step_id="add_device", data_schema=schema, errors=errors
            )

        phone_id = slugify(phone_name)
        if phone_id in existing_phones:
            errors["base"] = "already_exists"
            schema = vol.Schema(
                {
                    vol.Required(CONF_PHONE_NAME): str,
                    vol.Optional(CONF_MOBILE_APP_DEVICE_ID, default=None): vol.In(
                        device_options
                    ),
                }
            )
            return self.async_show_form(
                step_id="add_device", data_schema=schema, errors=errors
            )

        mobile_app_device_id = user_input.get(CONF_MOBILE_APP_DEVICE_ID)
        if mobile_app_device_id == "None":
            mobile_app_device_id = None

        coordinator.add_phone(phone_id, phone_name, mobile_app_device_id)
        await self.hass.config_entries.async_reload(self.config_entry.entry_id)
        return await self.async_step_manage_devices()

    async def async_step_edit_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        coordinator = self._get_coordinator()
        if coordinator is None:
            return self.async_abort(reason="integration_not_ready")

        if self.selected_phone_id is None:
            return await self.async_step_manage_devices()

        phone = coordinator.get_phone(self.selected_phone_id)
        if not phone:
            return await self.async_step_manage_devices()

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

        device_options = {None: "None"}
        for device_id in mobile_app_devices:
            device = device_registry.async_get(device_id)
            if device:
                device_options[device.id] = device.name

        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Required(CONF_PHONE_NAME, default=phone.phone_name): str,
                    vol.Optional(
                        CONF_MOBILE_APP_DEVICE_ID,
                        default=phone.mobile_app_device_id or None,
                    ): vol.In(device_options),
                }
            )
            return self.async_show_form(
                step_id="edit_device", data_schema=schema, errors=errors
            )

        phone_name = user_input.get(CONF_PHONE_NAME, "").strip()
        if not phone_name:
            errors["base"] = "required"
            schema = vol.Schema(
                {
                    vol.Required(CONF_PHONE_NAME, default=phone.phone_name): str,
                    vol.Optional(
                        CONF_MOBILE_APP_DEVICE_ID,
                        default=phone.mobile_app_device_id or None,
                    ): vol.In(device_options),
                }
            )
            return self.async_show_form(
                step_id="edit_device", data_schema=schema, errors=errors
            )

        mobile_app_device_id = user_input.get(CONF_MOBILE_APP_DEVICE_ID)
        if mobile_app_device_id == "None":
            mobile_app_device_id = None

        coordinator.update_phone(
            self.selected_phone_id, phone_name, mobile_app_device_id
        )
        await self.hass.config_entries.async_reload(self.config_entry.entry_id)
        self.selected_phone_id = None
        return await self.async_step_manage_devices()

    async def async_step_delete_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        coordinator = self._get_coordinator()
        if coordinator is None:
            return self.async_abort(reason="integration_not_ready")

        if self.selected_phone_id is None:
            return await self.async_step_manage_devices()

        phone = coordinator.get_phone(self.selected_phone_id)
        if not phone:
            return await self.async_step_manage_devices()

        if user_input is None:
            return self.async_show_form(
                step_id="delete_device",
                description_placeholders={"phone_name": phone.phone_name},
            )

        if user_input.get("confirm"):
            coordinator.delete_phone(self.selected_phone_id)
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
        self.selected_phone_id = None
        return await self.async_step_manage_devices()

    async def async_step_overview(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        coordinator = self._get_coordinator()
        if coordinator is None:
            return self.async_abort(reason="integration_not_ready")
        phones = coordinator.get_all_phones()
        all_alarms = coordinator.get_all_alarms()
        recent_events = coordinator.get_events(limit=10)

        last_sync = None
        for phone in phones.values():
            for alarm in phone.alarms.values():
                if alarm.synced_at:
                    if last_sync is None or alarm.synced_at > last_sync:
                        last_sync = alarm.synced_at

        phone_count = len(phones)
        alarm_count = len(all_alarms)

        return self.async_show_form(
            step_id="overview",
            description_placeholders={
                "phone_count": str(phone_count),
                "alarm_count": str(alarm_count),
                "last_sync": last_sync or "Never",
                "recent_events": str(len(recent_events)),
            },
        )

    async def async_step_events(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        coordinator = self._get_coordinator()
        if coordinator is None:
            return self.async_abort(reason="integration_not_ready")
        events = coordinator.get_events(limit=20)

        if user_input is None:
            if events:
                event_list = "\n".join(
                    f"- {event.occurred_at}: {event.event} "
                    f"(phone: {event.phone_id}, alarm: {event.alarm_id})"
                    for event in events
                )
            else:
                event_list = (
                    "No events recorded yet. "
                    "Events will appear here when alarms go off, "
                    "are snoozed, or stopped."
                )
            return self.async_show_form(
                step_id="events",
                description_placeholders={"event_list": event_list},
            )

        return await self.async_step_init()

    async def async_step_shortcuts(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        coordinator = self._get_coordinator()
        if coordinator is None:
            return self.async_abort(reason="integration_not_ready")
        phones = coordinator.get_all_phones()
        phone_ids = "\n".join(
            f"- {phone.phone_name}: `{phone_id}`" for phone_id, phone in phones.items()
        )
        return self.async_show_form(
            step_id="shortcuts",
            description_placeholders={
                "phone_ids": phone_ids or "No devices added yet."
            },
        )
