"""Config and options flows."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.iphone_alarms_sync.const import DOMAIN

from .conftest import ALARM_ID, PHONE_ID


async def test_custom_name_creates_entry(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "custom_name"}
    )
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
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "custom_name"}
    )
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
    entity_id = "sensor.john_iphone_wake_next_occurrence"
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
