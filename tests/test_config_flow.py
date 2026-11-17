"""Config and options flows."""

from __future__ import annotations

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant.common import MockConfigEntry

from custom_components.iphone_alarms_sync.const import DOMAIN

from .conftest import ALARM_ID, PHONE_ID


async def _start_flow(hass: HomeAssistant, step: str) -> dict:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": step}
    )


async def test_custom_name_creates_entry(hass: HomeAssistant) -> None:
    result = await _start_flow(hass, "custom_name")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"phone_name": "  !!  "}
    )
    assert result["errors"] == {"base": "required"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"phone_name": "Jane's iPhone"}
    )
    assert result["step_id"] == "confirm"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"sync_disabled_alarms": False}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == "janes_iphone"
    assert result["data"]["sync_disabled_alarms"] is False


async def test_duplicate_name_aborts(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    result = await _start_flow(hass, "custom_name")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"phone_name": "John iPhone"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def _edit_device(
    hass: HomeAssistant, entry: MockConfigEntry, **user_input: object
) -> None:
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "edit_device"}
    )
    assert result["step_id"] == "edit_device"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "phone_name": "John iPhone",
            "mobile_app_device_id": "none",
            "sync_disabled_alarms": True,
            **user_input,
        },
    )
    assert result["type"] is FlowResultType.MENU
    await hass.async_block_till_done()


async def test_edit_device_keeps_sync_disabled_alarms(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """The toggle survives the reload (hacs/default#13677)."""
    await _edit_device(hass, entry, sync_disabled_alarms=False)

    assert entry.data["sync_disabled_alarms"] is False
    assert entry.runtime_data.coordinator.phone.sync_disabled_alarms is False


async def test_edit_device_keeps_new_name_with_same_phone_id(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    await _edit_device(hass, entry, phone_name="John IPHONE")

    assert entry.unique_id == PHONE_ID
    assert entry.title == "John IPHONE"
    assert entry.runtime_data.coordinator.phone.phone_name == "John IPHONE"


async def test_edit_device_new_phone_id_moves_devices_and_entities(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    alarm_device = device_registry.async_get_device_by_identifier(
        (DOMAIN, PHONE_ID, ALARM_ID), entry.entry_id
    )
    assert alarm_device
    entity_id = "sensor.john_iphone_07_00_wake_next_occurrence"
    assert entity_registry.async_get(entity_id)

    await _edit_device(hass, entry, phone_name="Jane iPhone")

    assert entry.unique_id == "jane_iphone"
    assert entry.data["phone_id"] == "jane_iphone"
    moved = device_registry.async_get_device_by_identifier(
        (DOMAIN, "jane_iphone", ALARM_ID), entry.entry_id
    )
    assert moved and moved.id == alarm_device.id
    assert not device_registry.async_get_device_by_identifier(
        (DOMAIN, PHONE_ID), entry.entry_id
    )
    entity = entity_registry.async_get(entity_id)
    assert entity
    assert entity.unique_id.startswith(f"{entry.entry_id}_jane_iphone_{ALARM_ID}_")
    assert hass.states.get(entity_id) is not None
    old_prefix = f"{entry.entry_id}_{PHONE_ID}_"
    assert not [
        e
        for e in er.async_entries_for_config_entry(entity_registry, entry.entry_id)
        if e.unique_id.startswith(old_prefix)
    ]


async def test_edit_device_rejects_taken_phone_id(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    other = MockConfigEntry(domain=DOMAIN, unique_id="jane_iphone", data={})
    other.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "edit_device"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "phone_name": "Jane iPhone",
            "mobile_app_device_id": "none",
            "sync_disabled_alarms": True,
        },
    )
    assert result["errors"] == {"base": "phone_id_exists"}
    assert entry.unique_id == PHONE_ID


async def test_events_history_shows_local_time_and_names(
    hass: HomeAssistant, entry: MockConfigEntry, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-11-14 08:33:02+00:00")
    for service, data in (
        ("report_device_event", {"event": "any_stopped"}),
        ("report_device_event", {"event": "bedtime_starts"}),
        ("report_alarm_event", {"alarm_id": ALARM_ID, "event": "goes_off"}),
    ):
        await hass.services.async_call(
            DOMAIN, service, {"phone_id": PHONE_ID, **data}, blocking=True
        )
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "events"}
    )
    # Europe/Warsaw is UTC+1 in November; newest first.
    assert result["description_placeholders"]["event_list"] == (
        "- 2026-11-14 09:33:02 · Wake: Goes off\n"
        "- 2026-11-14 09:33:02 · Bedtime starts\n"
        "- 2026-11-14 09:33:02 · Any alarm: Stopped"
    )


async def test_event_shortcuts_lists_alarm_time_label_and_id(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "event_shortcuts"}
    )
    assert result["description_placeholders"]["alarms_list"] == (
        f"- 07:00 Wake: `{ALARM_ID}`"
    )


async def test_mobile_app_device_creates_entry(hass: HomeAssistant) -> None:
    mobile_app = MockConfigEntry(domain="mobile_app")
    mobile_app.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=mobile_app.entry_id,
        identifiers={("mobile_app", "jane")},
        name="Jane's iPhone",
    )

    result = await _start_flow(hass, "select_mobile_app")
    assert result["step_id"] == "select_mobile_app"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"mobile_app_device_id": device.id}
    )
    assert result["step_id"] == "confirm"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"sync_disabled_alarms": True}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Jane's iPhone Alarms"
    assert result["result"].unique_id == "janes_iphone_alarms"
    assert result["data"]["mobile_app_device_id"] == device.id


async def test_mobile_app_step_aborts_without_devices(hass: HomeAssistant) -> None:
    result = await _start_flow(hass, "select_mobile_app")
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_mobile_app_devices"


async def test_options_abort_when_not_loaded(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=PHONE_ID, data={})
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "integration_not_ready"


async def test_edit_device_rejects_empty_name(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "edit_device"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "phone_name": "  !!  ",
            "mobile_app_device_id": "none",
            "sync_disabled_alarms": True,
        },
    )
    assert result["errors"] == {"base": "required"}
    assert entry.unique_id == PHONE_ID


async def test_edit_device_leaves_other_entities(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    other = er.async_get(hass).async_get_or_create(
        "sensor", DOMAIN, "not_this_phone", config_entry=entry
    )
    await _edit_device(hass, entry, phone_name="Jane Phone")

    assert entry.unique_id == "jane_phone"
    assert er.async_get(hass).async_get(other.entity_id).unique_id == "not_this_phone"


@pytest.mark.parametrize("step", ["events", "sync_shortcut", "event_shortcuts"])
async def test_info_steps_return_to_menu(
    hass: HomeAssistant, entry: MockConfigEntry, step: str
) -> None:
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": step}
    )
    assert result["step_id"] == step
    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"
