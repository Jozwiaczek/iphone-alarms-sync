from __future__ import annotations

import re
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntryState,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_MOBILE_APP_DEVICE_ID,
    CONF_PHONE_ID,
    CONF_PHONE_NAME,
    CONF_SYNC_DISABLED_ALARMS,
    DOCS_TROUBLESHOOTING_URL,
    DOMAIN,
    SHORTCUT_ALARM_EVENT_URL,
    SHORTCUT_DEVICE_EVENT_URL,
    SHORTCUT_SYNC_URL,
)
from .coordinator import IPhoneAlarmsSyncConfigEntry, IPhoneAlarmsSyncCoordinator
from .qr_code import generate_qr_code_data_url

# HA 2026.9+ types data_schema as probatio (API-compatible with voluptuous), which
# 2026.8 lacks; hence the arg-type ignores on async_show_form.
# Domain of the Home Assistant app integration; importing it would load its platforms.
MOBILE_APP_DOMAIN = "mobile_app"
# Shown in the device select for "no linked Mobile App device".
NO_DEVICE = "none"


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "_", text)
    return text.strip("_")


def _mobile_app_devices(hass: HomeAssistant) -> dict[str, str]:
    """Names of the devices of all Home Assistant app (mobile_app) entries."""
    device_registry = dr.async_get(hass)
    return {
        device.id: device.name or device.id
        for entry in hass.config_entries.async_entries(MOBILE_APP_DOMAIN)
        for device in dr.async_entries_for_config_entry(device_registry, entry.entry_id)
    }


def _shortcut_placeholders() -> dict[str, str]:
    return {
        "sync_qr_code": generate_qr_code_data_url(SHORTCUT_SYNC_URL),
        "sync_shortcut_url": SHORTCUT_SYNC_URL,
        "alarm_event_qr_code": generate_qr_code_data_url(SHORTCUT_ALARM_EVENT_URL),
        "alarm_event_shortcut_url": SHORTCUT_ALARM_EVENT_URL,
        "device_event_qr_code": generate_qr_code_data_url(SHORTCUT_DEVICE_EVENT_URL),
        "device_event_shortcut_url": SHORTCUT_DEVICE_EVENT_URL,
        "troubleshooting_url": DOCS_TROUBLESHOOTING_URL,
    }


async def _async_migrate_phone_id(
    hass: HomeAssistant, entry: IPhoneAlarmsSyncConfigEntry, old: str, new: str
) -> None:
    """Move devices and entities to a new Phone ID so history and automations stay."""
    device_registry = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(device_registry, entry.entry_id):
        identifiers = {
            (i[0], new, *i[2:]) if i[:2] == (DOMAIN, old) else i
            for i in device.identifiers
        }
        if identifiers != device.identifiers:
            device_registry.async_update_device(
                device.id,
                new_identifiers=identifiers,  # type: ignore[arg-type]
            )

    old_prefix = f"{entry.entry_id}_{old}_"

    @callback
    def _migrate(entity: er.RegistryEntry) -> dict[str, Any] | None:
        if not entity.unique_id.startswith(old_prefix):
            return None
        key = entity.unique_id.removeprefix(old_prefix)
        return {"new_unique_id": f"{entry.entry_id}_{new}_{key}"}

    await er.async_migrate_entries(hass, entry.entry_id, _migrate)


class IPhoneAlarmsSyncConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 3

    def __init__(self) -> None:
        self._phone_id = ""
        self._phone_name = ""
        self._mobile_app_device_id: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="user", menu_options=["select_mobile_app", "custom_name"]
        )

    async def async_step_select_mobile_app(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        devices = _mobile_app_devices(self.hass)
        if not devices:
            return self.async_abort(reason="no_mobile_app_devices")
        if user_input is not None:
            device_id = user_input[CONF_MOBILE_APP_DEVICE_ID]
            return await self._async_set_phone(
                f"{devices[device_id]} Alarms", device_id
            )
        return self.async_show_form(
            step_id="select_mobile_app",
            data_schema=vol.Schema(  # type: ignore[arg-type]
                {vol.Required(CONF_MOBILE_APP_DEVICE_ID): vol.In(devices)}
            ),
        )

    async def async_step_custom_name(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            phone_name = user_input[CONF_PHONE_NAME].strip()
            if slugify(phone_name):
                return await self._async_set_phone(phone_name, None)
            errors["base"] = "required"
        return self.async_show_form(
            step_id="custom_name",
            data_schema=vol.Schema({vol.Required(CONF_PHONE_NAME): str}),  # type: ignore[arg-type]
            errors=errors,
        )

    async def _async_set_phone(
        self, phone_name: str, mobile_app_device_id: str | None
    ) -> ConfigFlowResult:
        self._phone_id = slugify(phone_name)
        self._phone_name = phone_name
        self._mobile_app_device_id = mobile_app_device_id
        await self.async_set_unique_id(self._phone_id)
        self._abort_if_unique_id_configured(
            description_placeholders={"phone_id": self._phone_id}
        )
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title=self._phone_name,
                data={
                    CONF_PHONE_ID: self._phone_id,
                    CONF_PHONE_NAME: self._phone_name,
                    CONF_MOBILE_APP_DEVICE_ID: self._mobile_app_device_id,
                    CONF_SYNC_DISABLED_ALARMS: user_input[CONF_SYNC_DISABLED_ALARMS],
                },
                options={"alarms": {}},
            )
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema(  # type: ignore[arg-type]
                {vol.Required(CONF_SYNC_DISABLED_ALARMS, default=True): bool}
            ),
            description_placeholders={
                "phone_name": self._phone_name,
                "phone_id": self._phone_id,
                **_shortcut_placeholders(),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: IPhoneAlarmsSyncConfigEntry,
    ) -> OptionsFlowHandler:
        return OptionsFlowHandler()


class OptionsFlowHandler(OptionsFlow):
    @property
    def _coordinator(self) -> IPhoneAlarmsSyncCoordinator:
        return self.config_entry.runtime_data.coordinator  # type: ignore[no-any-return]

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if self.config_entry.state is not ConfigEntryState.LOADED:
            return self.async_abort(reason="integration_not_ready")
        return self.async_show_menu(
            step_id="init",
            menu_options=["edit_device", "events", "sync_shortcut", "event_shortcuts"],
        )

    async def async_step_edit_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self.config_entry
        devices = {NO_DEVICE: "None"} | _mobile_app_devices(self.hass)
        errors: dict[str, str] = {}

        if user_input is not None:
            phone_name = user_input[CONF_PHONE_NAME].strip()
            old_phone_id = entry.data[CONF_PHONE_ID]
            new_phone_id = slugify(phone_name)
            existing = self.hass.config_entries.async_entry_for_domain_unique_id(
                DOMAIN, new_phone_id
            )
            if not new_phone_id:
                errors["base"] = "required"
            elif existing and existing.entry_id != entry.entry_id:
                errors["base"] = "phone_id_exists"
            else:
                device_id = user_input[CONF_MOBILE_APP_DEVICE_ID]
                if new_phone_id != old_phone_id:
                    await _async_migrate_phone_id(
                        self.hass, entry, old_phone_id, new_phone_id
                    )
                # entry.data is what the coordinator loads; HA skips an unchanged write.
                self.hass.config_entries.async_update_entry(
                    entry,
                    unique_id=new_phone_id,
                    title=phone_name,
                    data={
                        **entry.data,
                        CONF_PHONE_ID: new_phone_id,
                        CONF_PHONE_NAME: phone_name,
                        CONF_MOBILE_APP_DEVICE_ID: (
                            None if device_id == NO_DEVICE else device_id
                        ),
                        CONF_SYNC_DISABLED_ALARMS: user_input[
                            CONF_SYNC_DISABLED_ALARMS
                        ],
                    },
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return await self.async_step_init()

        values = user_input or {
            CONF_PHONE_NAME: entry.data[CONF_PHONE_NAME],
            CONF_MOBILE_APP_DEVICE_ID: entry.data.get(CONF_MOBILE_APP_DEVICE_ID),
            CONF_SYNC_DISABLED_ALARMS: entry.data.get(CONF_SYNC_DISABLED_ALARMS, True),
        }
        device_default = values[CONF_MOBILE_APP_DEVICE_ID]
        schema = vol.Schema(
            {
                vol.Required(CONF_PHONE_NAME, default=values[CONF_PHONE_NAME]): str,
                vol.Required(
                    CONF_MOBILE_APP_DEVICE_ID,
                    default=device_default if device_default in devices else NO_DEVICE,
                ): vol.In(devices),
                vol.Required(
                    CONF_SYNC_DISABLED_ALARMS,
                    default=values[CONF_SYNC_DISABLED_ALARMS],
                ): bool,
            }
        )
        return self.async_show_form(
            step_id="edit_device",
            data_schema=schema,  # type: ignore[arg-type]
            errors=errors,
            description_placeholders={"phone_id": entry.data[CONF_PHONE_ID]},
        )

    async def async_step_events(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return await self.async_step_init()
        events = self._coordinator.get_events()
        event_list = "\n".join(
            f"- {event.occurred_at}: {event.event} (alarm: {event.alarm_id})"
            for event in reversed(events)
        )
        return self.async_show_form(
            step_id="events",
            description_placeholders={
                "event_list": event_list
                or "No events since Home Assistant started. Events appear here "
                "when alarms go off, are snoozed, or stopped."
            },
        )

    async def async_step_sync_shortcut(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return await self.async_step_init()
        return self.async_show_form(
            step_id="sync_shortcut",
            description_placeholders={
                "phone_id": self._coordinator.phone.phone_id,
                **_shortcut_placeholders(),
            },
        )

    async def async_step_event_shortcuts(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return await self.async_step_init()
        phone = self._coordinator.phone
        alarms_list = "\n".join(
            f"- {alarm.label}: `{alarm_id}`" for alarm_id, alarm in phone.alarms.items()
        )
        return self.async_show_form(
            step_id="event_shortcuts",
            description_placeholders={
                "phone_id": phone.phone_id,
                "alarms_list": alarms_list or "No alarms synchronized yet.",
                **_shortcut_placeholders(),
            },
        )
