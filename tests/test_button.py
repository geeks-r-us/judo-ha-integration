"""Tests for Judo iSoft action buttons."""

from dataclasses import dataclass, field
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.judo_isoft.button import (
    JudoiSoftActionButton,
    async_setup_entry,
)
from custom_components.judo_isoft.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations():
    """Override global autouse fixture for pure unit tests."""
    yield


@dataclass
class DummyConfigEntry:
    """Minimal config entry for entity tests."""

    entry_id: str = "entry-1"
    data: dict = field(default_factory=lambda: {"host": "device-1"})


class DummyCoordinator:
    """Minimal coordinator object compatible with CoordinatorEntity."""

    def __init__(self, data: dict) -> None:
        self.last_update_success = True
        self.data = data
        self.api = SimpleNamespace(execute_command=AsyncMock(return_value={"status": "ok"}))
        self.async_request_refresh = AsyncMock()

    def async_add_listener(self, update_callback):
        return lambda: None


@pytest.mark.asyncio
async def test_button_setup_uses_softener_fallback_when_capabilities_missing() -> None:
    """Action buttons should still be created for softener snapshots."""
    entry = DummyConfigEntry()
    coordinator = DummyCoordinator(
        {
            "capabilities": [],
            "device_info": {"family": "unknown", "device_id": "abc"},
            "fields_by_key": {"salt_level_pct": {"value": 77.0}},
            "system_status": {"online": True},
        }
    )
    hass = SimpleNamespace(data={DOMAIN: {entry.entry_id: coordinator}})
    created = []

    await async_setup_entry(hass, entry, created.extend)

    assert len(created) == 3
    assert all(isinstance(entity, JudoiSoftActionButton) for entity in created)


@pytest.mark.asyncio
async def test_button_press_executes_command_and_refreshes() -> None:
    """Pressing an action button should dispatch command and refresh snapshot."""
    entry = DummyConfigEntry()
    coordinator = DummyCoordinator(
        {
            "device_info": {"device_id": "abc"},
            "system_status": {"online": True},
            "fields_by_key": {"salt_level_pct": {"value": 70}},
        }
    )
    button = JudoiSoftActionButton(
        coordinator,
        entry,
        SimpleNamespace(
            key="start_regeneration",
            name="Start Regeneration",
            icon="mdi:refresh",
            command_id=0x35,
            value=0,
        ),
    )

    await button.async_press()

    coordinator.api.execute_command.assert_awaited_once_with(
        device_id="abc",
        command=0x35,
        value=0,
        transport="auto",
    )
    coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_button_setup_generates_payloadless_capability_actions() -> None:
    """Writable payload-less capabilities should produce generated buttons."""
    entry = DummyConfigEntry()
    coordinator = DummyCoordinator(
        {
            "capabilities": [
                {
                    "command_id": 0x54,
                    "name": "Start Sleep",
                    "direction": "write",
                    "payload_length": 0,
                }
            ],
            "device_info": {"family": "i_safe", "device_id": "safe-1"},
            "fields_by_key": {},
            "system_status": {"online": True},
        }
    )
    hass = SimpleNamespace(data={DOMAIN: {entry.entry_id: coordinator}})
    created = []

    await async_setup_entry(hass, entry, created.extend)

    assert len(created) == 1
    button = created[0]
    assert button.name == "Start Sleep"
    assert "cmd_54_" in button.unique_id

    await button.async_press()

    coordinator.api.execute_command.assert_awaited_once_with(
        device_id="safe-1",
        command=0x54,
        value=None,
        transport="auto",
    )


@pytest.mark.asyncio
async def test_button_setup_generates_default_value_capability_actions() -> None:
    """Capabilities with curated defaults should use that default payload."""
    entry = DummyConfigEntry()
    coordinator = DummyCoordinator(
        {
            "capabilities": [
                {
                    "command_id": 0x52,
                    "name": "Set Dosage",
                    "direction": "write",
                    "payload_length": 2,
                    "default_write_value": "0002",
                }
            ],
            "device_info": {"family": "i_dos", "device_id": "dos-1"},
            "fields_by_key": {},
            "system_status": {"online": True},
        }
    )
    hass = SimpleNamespace(data={DOMAIN: {entry.entry_id: coordinator}})
    created = []

    await async_setup_entry(hass, entry, created.extend)

    assert len(created) == 1
    button = created[0]
    assert button.name == "Set Dosage"

    await button.async_press()

    coordinator.api.execute_command.assert_awaited_once_with(
        device_id="dos-1",
        command=0x52,
        value="0002",
        transport="auto",
    )


@pytest.mark.asyncio
async def test_button_setup_skips_generated_when_explicit_exists() -> None:
    """Explicit button entities should suppress generated duplicates by command id."""
    entry = DummyConfigEntry()
    coordinator = DummyCoordinator(
        {
            "capabilities": [
                {
                    "command_id": 0x35,
                    "name": "Start Regeneration",
                    "direction": "write",
                    "payload_length": 1,
                    "default_write_value": 0,
                }
            ],
            "device_info": {"family": "unknown", "device_id": "abc"},
            "fields_by_key": {},
            "system_status": {"online": True},
        }
    )
    hass = SimpleNamespace(data={DOMAIN: {entry.entry_id: coordinator}})
    created = []

    await async_setup_entry(hass, entry, created.extend)

    assert len(created) == 1
    assert created[0].name == "Start Regeneration"
    assert created[0].unique_id.endswith("cmd_35_button_start_regeneration")
