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
    VERSION = 3

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required("method"): vol.In(
                            {
                                "mobile_app": "Select from Mobile App devices",
                                "custom": "Enter custom device name",
                            }
                        ),
                    }
                ),
            )

        method = user_input.get("method")
        if method == "mobile_app":
            return await self.async_step_select_mobile_app()
        elif method == "custom":
            return await self.async_step_custom_name()

        return self.async_abort(reason="unknown")

    async def async_step_select_mobile_app(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
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

        if not mobile_app_devices:
            return self.async_abort(reason="no_mobile_app_devices")

        device_options = {}
        for device_id in mobile_app_devices:
            device = device_registry.async_get(device_id)
            if device:
                device_options[device.id] = device.name

        errors: dict[str, str] = {}

        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Required(CONF_MOBILE_APP_DEVICE_ID): vol.In(device_options),
                    vol.Optional(CONF_PHONE_NAME): str,
                }
            )
            return self.async_show_form(
                step_id="select_mobile_app", data_schema=schema, errors=errors
            )

        mobile_app_device_id = user_input.get(CONF_MOBILE_APP_DEVICE_ID)
        phone_name = user_input.get(CONF_PHONE_NAME, "").strip()

        device = device_registry.async_get(mobile_app_device_id)
        if not device:
            errors["base"] = "device_not_found"
            schema = vol.Schema(
                {
                    vol.Required(CONF_MOBILE_APP_DEVICE_ID): vol.In(device_options),
                    vol.Optional(CONF_PHONE_NAME): str,
                }
            )
            return self.async_show_form(
                step_id="select_mobile_app", data_schema=schema, errors=errors
            )

        if not phone_name:
            phone_name = device.name

        return await self._async_create_entry_from_name(
            phone_name, mobile_app_device_id
        )

    async def async_step_custom_name(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Required(CONF_PHONE_NAME): str,
                }
            )
            return self.async_show_form(
                step_id="custom_name", data_schema=schema, errors=errors
            )

        phone_name = user_input.get(CONF_PHONE_NAME, "").strip()
        if not phone_name:
            errors["base"] = "required"
            schema = vol.Schema(
                {
                    vol.Required(CONF_PHONE_NAME): str,
                }
            )
            return self.async_show_form(
                step_id="custom_name", data_schema=schema, errors=errors
            )

        return await self._async_create_entry_from_name(phone_name, None)

    async def _async_create_entry_from_name(
        self, phone_name: str, mobile_app_device_id: str | None
    ) -> FlowResult:
        phone_id = slugify(phone_name)

        await self.async_set_unique_id(phone_id)
        self._abort_if_unique_id_configured()

        return await self.async_step_confirm(
            phone_id=phone_id,
            phone_name=phone_name,
            mobile_app_device_id=mobile_app_device_id,
        )

    async def async_step_confirm(
        self,
        phone_id: str,
        phone_name: str,
        mobile_app_device_id: str | None,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="confirm",
                description_placeholders={
                    "phone_name": phone_name,
                    "phone_id": phone_id,
                },
            )

        return self.async_create_entry(
            title=phone_name,
            data={
                CONF_PHONE_ID: phone_id,
                CONF_PHONE_NAME: phone_name,
                CONF_MOBILE_APP_DEVICE_ID: mobile_app_device_id,
            },
            options={"alarms": {}},
        )

    async def async_step_import(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is None:
            return self.async_abort(reason="invalid_import_data")

        phone_id = user_input.get(CONF_PHONE_ID)
        phone_name = user_input.get(CONF_PHONE_NAME)
        mobile_app_device_id = user_input.get(CONF_MOBILE_APP_DEVICE_ID)

        if not phone_id or not phone_name:
            return self.async_abort(reason="invalid_import_data")

        await self.async_set_unique_id(phone_id)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=phone_name,
            data={
                CONF_PHONE_ID: phone_id,
                CONF_PHONE_NAME: phone_name,
                CONF_MOBILE_APP_DEVICE_ID: mobile_app_device_id,
            },
            options={"alarms": {}},
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: IPhoneAlarmsSyncConfigEntry,
    ) -> OptionsFlowHandler:
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlowWithConfigEntry):
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
                "edit_device",
                "overview",
                "events",
                "shortcuts",
            ],
        )

    async def async_step_edit_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        coordinator = self._get_coordinator()
        if coordinator is None:
            return self.async_abort(reason="integration_not_ready")

        phone = coordinator.get_phone()
        if not phone:
            return self.async_abort(reason="phone_not_found")

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
        if mobile_app_device_id == "None" or mobile_app_device_id is None:
            mobile_app_device_id = None

        old_phone_id = phone.phone_id
        new_phone_id = slugify(phone_name)

        if new_phone_id != old_phone_id:
            existing_entries = self.hass.config_entries.async_entries(DOMAIN)
            for entry in existing_entries:
                if (
                    entry.unique_id == new_phone_id
                    and entry.entry_id != self.config_entry.entry_id
                ):
                    errors["base"] = "phone_id_exists"
                    schema = vol.Schema(
                        {
                            vol.Required(CONF_PHONE_NAME, default=phone_name): str,
                            vol.Optional(
                                CONF_MOBILE_APP_DEVICE_ID,
                                default=mobile_app_device_id or None,
                            ): vol.In(device_options),
                        }
                    )
                    return self.async_show_form(
                        step_id="edit_device", data_schema=schema, errors=errors
                    )

        coordinator.update_phone(phone_name, mobile_app_device_id)
        if new_phone_id != old_phone_id:
            new_data = dict(self.config_entry.data)
            new_data[CONF_PHONE_ID] = new_phone_id
            new_data[CONF_PHONE_NAME] = phone_name
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                unique_id=new_phone_id,
                title=phone_name,
                data=new_data,
            )
        await self.hass.config_entries.async_reload(self.config_entry.entry_id)
        return await self.async_step_init()

    async def async_step_overview(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        coordinator = self._get_coordinator()
        if coordinator is None:
            return self.async_abort(reason="integration_not_ready")
        phone = coordinator.get_phone()
        if not phone:
            return self.async_abort(reason="phone_not_found")

        all_alarms = coordinator.get_all_alarms()
        recent_events = coordinator.get_events(limit=10)

        last_sync = None
        for alarm in phone.alarms.values():
            if alarm.synced_at:
                if last_sync is None or alarm.synced_at > last_sync:
                    last_sync = alarm.synced_at

        alarm_count = len(all_alarms)

        return self.async_show_form(
            step_id="overview",
            description_placeholders={
                "phone_name": phone.phone_name,
                "phone_id": phone.phone_id,
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
                    f"(alarm: {event.alarm_id})"
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
        phone = coordinator.get_phone()
        if not phone:
            return self.async_abort(reason="phone_not_found")

        return self.async_show_form(
            step_id="shortcuts",
            description_placeholders={
                "phone_name": phone.phone_name,
                "phone_id": phone.phone_id,
            },
        )
