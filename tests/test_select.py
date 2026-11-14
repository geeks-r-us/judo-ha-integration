"""Tests for Judo iSoft writable select entities."""

from dataclasses import dataclass, field
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.judo_isoft.const import DOMAIN
from custom_components.judo_isoft.select import (
    JudoiSoftHardnessUnitSelect,
    async_setup_entry,
)


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
async def test_select_setup_uses_softener_fallback_when_capabilities_missing() -> None:
    """Hardness unit select should be created for softener snapshots."""
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

    assert len(created) == 1
    assert isinstance(created[0], JudoiSoftHardnessUnitSelect)


@pytest.mark.asyncio
async def test_select_set_executes_command_and_refreshes() -> None:
    """Writing hardness unit should dispatch command 0x24."""
    entry = DummyConfigEntry()
    coordinator = DummyCoordinator(
        {
            "device_info": {"device_id": "abc", "device_type": "0x58"},
            "system_status": {"online": True},
            "fields_by_key": {
                "hardness_unit": {"value": "dH"},
                "salt_level_pct": {"value": 77.0},
            },
        }
    )
    entity = JudoiSoftHardnessUnitSelect(coordinator, entry)

    assert entity.options == ["°dH", "°fH"]
    assert entity.current_option == "°dH"

    await entity.async_select_option("°fH")

    coordinator.api.execute_command.assert_awaited_once_with(
        device_id="abc",
        command=0x24,
        value=2,
        transport="auto",
    )
    coordinator.async_request_refresh.assert_awaited_once()


def test_select_current_option_defaults_when_missing() -> None:
    """Current option should not be unknown when snapshot has no hardness_unit."""
    entry = DummyConfigEntry()
    coordinator = DummyCoordinator(
        {
            "device_info": {"device_id": "abc", "device_type": "0x58"},
            "system_status": {"online": True},
            "fields_by_key": {"salt_level_pct": {"value": 77.0}},
        }
    )
    entity = JudoiSoftHardnessUnitSelect(coordinator, entry)

    assert entity.current_option == "°dH"


def test_select_unique_id_uses_normalized_command_format() -> None:
    """Writable select unique id should be normalized to entry/device/cmd format."""
    entry = DummyConfigEntry()
    coordinator = DummyCoordinator(
        {
            "device_info": {"device_id": "ABC-123", "device_type": "0x58"},
            "system_status": {"online": True},
            "fields_by_key": {"hardness_unit": {"value": "dH"}},
        }
    )
    entity = JudoiSoftHardnessUnitSelect(coordinator, entry)

    assert entity.unique_id.startswith("entry_1_abc_123_")
    assert entity.unique_id.endswith("cmd_24_hardness_unit")


@pytest.mark.asyncio
async def test_select_populates_option_from_command_23_when_missing() -> None:
    """Select should read 0x23 to populate current option after restart."""
    entry = DummyConfigEntry()
    coordinator = DummyCoordinator(
        {
            "device_info": {"device_id": "abc", "device_type": "0x58"},
            "system_status": {"online": True},
            "fields_by_key": {"salt_level_pct": {"value": 77.0}},
        }
    )
    coordinator.api.execute_command = AsyncMock(
        return_value={
            "status": "ok",
            "fields": [
                {
                    "key": "hardness_unit",
                    "value": "fH",
                }
            ],
        }
    )
    entity = JudoiSoftHardnessUnitSelect(coordinator, entry)
    entity.async_write_ha_state = Mock()

    await entity._async_populate_option_from_command()

    coordinator.api.execute_command.assert_awaited_once_with(
        device_id="abc",
        command=0x23,
        value=None,
        transport="auto",
    )
    assert entity.current_option == "°fH"
