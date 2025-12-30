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
    CONF_SYNC_DISABLED_ALARMS,
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

    def __init__(self):
        super().__init__()
        self._phone_id: str | None = None
        self._phone_name: str | None = None
        self._mobile_app_device_id: str | None = None

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
                }
            )
            return self.async_show_form(
                step_id="select_mobile_app", data_schema=schema, errors=errors
            )

        mobile_app_device_id = user_input.get(CONF_MOBILE_APP_DEVICE_ID)

        device = device_registry.async_get(mobile_app_device_id)
        if not device:
            errors["base"] = "device_not_found"
            schema = vol.Schema(
                {
                    vol.Required(CONF_MOBILE_APP_DEVICE_ID): vol.In(device_options),
                }
            )
            return self.async_show_form(
                step_id="select_mobile_app", data_schema=schema, errors=errors
            )

        phone_name = f"{device.name} Alarms"

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

        self._phone_id = phone_id
        self._phone_name = phone_name
        self._mobile_app_device_id = mobile_app_device_id

        await self.async_set_unique_id(phone_id)

        existing_entries = self.hass.config_entries.async_entries(DOMAIN)
        for entry in existing_entries:
            if entry.unique_id == phone_id:
                return await self.async_step_already_configured(entry)

        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if self._phone_id is None or self._phone_name is None:
            return self.async_abort(reason="unknown")

        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Required(CONF_SYNC_DISABLED_ALARMS, default=True): bool,
                }
            )
            return self.async_show_form(
                step_id="confirm",
                data_schema=schema,
                description_placeholders={
                    "phone_name": self._phone_name,
                    "phone_id": self._phone_id,
                },
            )

        sync_disabled_alarms = user_input.get(CONF_SYNC_DISABLED_ALARMS, True)

        return self.async_create_entry(
            title=self._phone_name,
            data={
                CONF_PHONE_ID: self._phone_id,
                CONF_PHONE_NAME: self._phone_name,
                CONF_MOBILE_APP_DEVICE_ID: self._mobile_app_device_id,
                CONF_SYNC_DISABLED_ALARMS: sync_disabled_alarms,
            },
            options={"alarms": {}},
        )

    async def async_step_already_configured(
        self,
        existing_entry: config_entries.ConfigEntry,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        if self._phone_id is None or self._phone_name is None:
            return self.async_abort(reason="unknown")

        if user_input is None:
            return self.async_show_form(
                step_id="already_configured",
                data_schema=vol.Schema(
                    {
                        vol.Required("action"): vol.In(
                            {
                                "new_name": "Use different name",
                            }
                        ),
                    }
                ),
                description_placeholders={
                    "phone_name": self._phone_name,
                    "phone_id": self._phone_id,
                    "existing_title": existing_entry.title,
                },
            )

        action = user_input.get("action")
        if action == "new_name":
            self._phone_id = None
            self._phone_name = None
            self._mobile_app_device_id = None
            return await self.async_step_user()

        return self.async_abort(reason="unknown")

    async def async_step_import(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is None:
            return self.async_abort(reason="invalid_import_data")

        phone_id = user_input.get(CONF_PHONE_ID)
        phone_name = user_input.get(CONF_PHONE_NAME)
        mobile_app_device_id = user_input.get(CONF_MOBILE_APP_DEVICE_ID)
        sync_disabled_alarms = user_input.get(CONF_SYNC_DISABLED_ALARMS, True)

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
                CONF_SYNC_DISABLED_ALARMS: sync_disabled_alarms,
            },
            options={"alarms": {}},
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: IPhoneAlarmsSyncConfigEntry,
    ) -> OptionsFlowHandler:
        return OptionsFlowHandler(config_entry)


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
                    vol.Required(
                        CONF_SYNC_DISABLED_ALARMS,
                        default=phone.sync_disabled_alarms,
                    ): bool,
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
                    vol.Required(
                        CONF_SYNC_DISABLED_ALARMS,
                        default=phone.sync_disabled_alarms,
                    ): bool,
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
                            vol.Required(
                                CONF_SYNC_DISABLED_ALARMS,
                                default=phone.sync_disabled_alarms,
                            ): bool,
                        }
                    )
                    return self.async_show_form(
                        step_id="edit_device", data_schema=schema, errors=errors
                    )

        sync_disabled_alarms = user_input.get(CONF_SYNC_DISABLED_ALARMS, True)

        coordinator.update_phone(phone_name, mobile_app_device_id, sync_disabled_alarms)
        if (
            new_phone_id != old_phone_id
            or sync_disabled_alarms != phone.sync_disabled_alarms
        ):
            new_data = dict(self.config_entry.data)
            new_data[CONF_PHONE_ID] = new_phone_id
            new_data[CONF_PHONE_NAME] = phone_name
            new_data[CONF_SYNC_DISABLED_ALARMS] = sync_disabled_alarms
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                unique_id=new_phone_id,
                title=phone_name,
                data=new_data,
            )

        device_registry = dr.async_get(self.hass)
        phone_device = device_registry.async_get_device(
            identifiers={(DOMAIN, old_phone_id)}
        )
        if phone_device:
            via_device = None
            if mobile_app_device_id:
                mobile_app_device = device_registry.async_get(mobile_app_device_id)
                if mobile_app_device and mobile_app_device.identifiers:
                    via_device = next(iter(mobile_app_device.identifiers))
            device_registry.async_update_device(
                phone_device.id,
                via_device=via_device,
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

        last_sync = phone.synced_at

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
                    f"- {event.occurred_at}: {event.event} (alarm: {event.alarm_id})"
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
