"""Tests for Judo iSoft writable number entities."""

from dataclasses import dataclass, field
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.judo_isoft.const import DOMAIN
from custom_components.judo_isoft.number import (
    JudoiSoftTargetHardnessNumber,
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


def _write_values(call_mock: AsyncMock) -> list[object]:
    """Collect command 0x30 write payloads in call order."""
    return [
        call.kwargs.get("value")
        for call in call_mock.await_args_list
        if call.kwargs.get("command") == 0x30 and call.kwargs.get("value") is not None
    ]


@pytest.mark.asyncio
async def test_number_setup_uses_softener_fallback_when_capabilities_missing() -> None:
    """Target hardness number should be created for softener snapshots."""
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
    assert isinstance(created[0], JudoiSoftTargetHardnessNumber)


@pytest.mark.asyncio
async def test_number_set_executes_command_and_refreshes() -> None:
    """Writing target hardness should dispatch command 0x30."""
    entry = DummyConfigEntry()
    coordinator = DummyCoordinator(
        {
            "device_info": {"device_id": "abc"},
            "system_status": {"online": True},
            "fields_by_key": {
                "target_hardness": {"value": 6.0},
                "hardness_unit": {"value": "dH"},
                "salt_level_pct": {"value": 77.0},
            },
        }
    )
    coordinator.api.execute_command = AsyncMock(
        side_effect=[
            {"status": "ok", "transport": "local"},
            {
                "status": "ok",
                "fields": [{"key": "target_hardness", "value": 10.0}],
            },
        ]
    )
    entity = JudoiSoftTargetHardnessNumber(coordinator, entry)

    assert entity.native_value == 6.0
    assert entity.native_unit_of_measurement == "°dH"

    await entity.async_set_native_value(10.4)

    assert coordinator.api.execute_command.await_count == 2
    coordinator.async_request_refresh.assert_awaited_once()


def test_number_native_unit_stays_dh_even_when_device_unit_differs() -> None:
    """Target-hardness writes/readbacks are handled in dH for i-soft devices."""
    entry = DummyConfigEntry()
    coordinator = DummyCoordinator(
        {
            "device_info": {"device_id": "abc"},
            "system_status": {"online": True},
            "fields_by_key": {
                "target_hardness": {"value": 6.0},
                "hardness_unit": {"value": "ppm"},
            },
        }
    )
    entity = JudoiSoftTargetHardnessNumber(coordinator, entry)

    assert entity.native_unit_of_measurement == "°dH"


def test_number_range_is_1_to_12_dh() -> None:
    """Entity limits should match supported target hardness range."""
    entry = DummyConfigEntry()
    coordinator = DummyCoordinator(
        {
            "device_info": {"device_id": "abc"},
            "system_status": {"online": True},
            "fields_by_key": {"target_hardness": {"value": 6.0}},
        }
    )
    entity = JudoiSoftTargetHardnessNumber(coordinator, entry)

    assert entity.native_min_value == 1
    assert entity.native_max_value == 12


def test_number_unique_id_uses_normalized_command_format() -> None:
    """Writable number unique id should be normalized to entry/device/cmd format."""
    entry = DummyConfigEntry()
    coordinator = DummyCoordinator(
        {
            "device_info": {"device_id": "ABC-123"},
            "system_status": {"online": True},
            "fields_by_key": {"target_hardness": {"value": 6.0}},
        }
    )
    entity = JudoiSoftTargetHardnessNumber(coordinator, entry)

    assert entity.unique_id.startswith("entry_1_abc_123_")
    assert entity.unique_id.endswith("cmd_30_target_hardness")


@pytest.mark.asyncio
async def test_number_set_rejects_out_of_range_values() -> None:
    """Writing outside 1..12 °dH should fail before dispatching command."""
    entry = DummyConfigEntry()
    coordinator = DummyCoordinator(
        {
            "device_info": {"device_id": "abc"},
            "system_status": {"online": True},
            "fields_by_key": {"target_hardness": {"value": 6.0}},
        }
    )
    entity = JudoiSoftTargetHardnessNumber(coordinator, entry)

    with pytest.raises(HomeAssistantError, match="1-12"):
        await entity.async_set_native_value(13)

    coordinator.api.execute_command.assert_not_awaited()
    coordinator.async_request_refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_number_set_retries_with_two_byte_payload_on_mismatch() -> None:
    """If readback mismatches, write should retry using 2-byte payload."""
    entry = DummyConfigEntry()
    coordinator = DummyCoordinator(
        {
            "device_info": {"device_id": "abc"},
            "system_status": {"online": True},
            "fields_by_key": {
                "target_hardness": {"value": 8.0},
                "hardness_unit": {"value": "dH"},
            },
        }
    )
    coordinator.api.execute_command = AsyncMock(
        side_effect=[
            {"status": "ok", "transport": "local"},  # write 1-byte
            {"status": "ok", "fields": [{"key": "target_hardness", "value": 8.0}]},  # mismatch
            {"status": "ok", "transport": "local"},  # write 2-byte retry
            {"status": "ok", "fields": [{"key": "target_hardness", "value": 7.0}]},  # match
        ]
    )
    entity = JudoiSoftTargetHardnessNumber(coordinator, entry)

    await entity.async_set_native_value(7)

    assert _write_values(coordinator.api.execute_command) == [7, "0700"]
    assert coordinator.async_request_refresh.await_count == 2


@pytest.mark.asyncio
async def test_number_set_retries_with_two_byte_payload_even_when_unit_not_dh() -> None:
    """i-soft retries should still use the documented 2-byte payload shape."""
    entry = DummyConfigEntry()
    coordinator = DummyCoordinator(
        {
            "device_info": {"device_id": "abc"},
            "system_status": {"online": True},
            "fields_by_key": {
                "target_hardness": {"value": 8.0},
                "hardness_unit": {"value": "ppm"},
            },
        }
    )
    coordinator.api.execute_command = AsyncMock(
        side_effect=[
            {"status": "ok", "transport": "local"},  # write 1-byte
            {"status": "ok", "fields": [{"key": "target_hardness", "value": 8.0}]},  # mismatch
            {"status": "ok", "transport": "local"},  # write 2-byte retry
            {"status": "ok", "fields": [{"key": "target_hardness", "value": 7.0}]},  # match
        ]
    )
    entity = JudoiSoftTargetHardnessNumber(coordinator, entry)

    await entity.async_set_native_value(7)

    assert _write_values(coordinator.api.execute_command) == [7, "0700"]
    assert coordinator.async_request_refresh.await_count == 2


@pytest.mark.asyncio
async def test_number_set_retries_with_device_unit_two_byte_payload_when_needed() -> None:
    """If the standard 2-byte retry fails, try the current device-unit encoding."""
    entry = DummyConfigEntry()
    coordinator = DummyCoordinator(
        {
            "device_info": {"device_id": "abc"},
            "system_status": {"online": True},
            "fields_by_key": {
                "target_hardness": {"value": 8.0},
                "hardness_unit": {"value": "ppm"},
            },
        }
    )
    coordinator.api.execute_command = AsyncMock(
        side_effect=[
            {"status": "ok", "transport": "local"},  # write 1-byte
            {"status": "ok", "fields": [{"key": "target_hardness", "value": 8.0}]},  # mismatch
            {"status": "ok", "transport": "local"},  # write 2-byte dH retry
            {"status": "ok", "fields": [{"key": "target_hardness", "value": 8.0}]},  # mismatch
            {"status": "ok", "transport": "local"},  # write 2-byte ppm retry
            {"status": "ok", "fields": [{"key": "target_hardness", "value": 7.0}]},  # match
        ]
    )
    entity = JudoiSoftTargetHardnessNumber(coordinator, entry)

    await entity.async_set_native_value(7)

    assert _write_values(coordinator.api.execute_command) == [7, "0700", "7D00"]
    assert coordinator.async_request_refresh.await_count == 3


@pytest.mark.asyncio
async def test_number_set_cloud_mismatch_keeps_optimistic_value() -> None:
    """Persistent cloud readback lag should not hard-fail an accepted write."""
    entry = DummyConfigEntry()
    coordinator = DummyCoordinator(
        {
            "device_info": {"device_id": "abc"},
            "system_status": {"online": True},
            "fields_by_key": {
                "target_hardness": {"value": 8.0},
                "hardness_unit": {"value": "dH"},
            },
        }
    )
    async def _execute(**kwargs):
        command = kwargs.get("command")
        if command == 0x30:
            return {"status": "ok", "transport": "cloud"}
        if command == 0x51:
            return {"status": "ok", "fields": [{"key": "target_hardness", "value": 8.0}]}
        return {"status": "ok"}

    coordinator.api.execute_command = AsyncMock(side_effect=_execute)
    entity = JudoiSoftTargetHardnessNumber(coordinator, entry)

    with patch("custom_components.judo_isoft.number.asyncio.sleep", new=AsyncMock()):
        await entity.async_set_native_value(7)

    assert _write_values(coordinator.api.execute_command)[:4] == [7, "0700", "0007", "000700"]
    assert entity.native_value == 7.0


@pytest.mark.asyncio
async def test_number_set_cloud_retries_docs_separator_payload_shape() -> None:
    """Cloud write should retry with docs-style 00-prefixed payload shape."""
    entry = DummyConfigEntry()
    coordinator = DummyCoordinator(
        {
            "device_info": {"device_id": "abc"},
            "system_status": {"online": True},
            "fields_by_key": {
                "target_hardness": {"value": 8.0},
                "hardness_unit": {"value": "dH"},
            },
        }
    )
    read_count = 0

    async def _execute(**kwargs):
        nonlocal read_count
        command = kwargs.get("command")
        if command == 0x30:
            return {"status": "ok", "transport": "cloud"}
        if command == 0x51:
            read_count += 1
            read_value = 7.0 if read_count >= 9 else 8.0
            return {"status": "ok", "fields": [{"key": "target_hardness", "value": read_value}]}
        return {"status": "ok"}

    coordinator.api.execute_command = AsyncMock(side_effect=_execute)
    entity = JudoiSoftTargetHardnessNumber(coordinator, entry)

    with patch("custom_components.judo_isoft.number.asyncio.sleep", new=AsyncMock()):
        await entity.async_set_native_value(7)

    assert _write_values(coordinator.api.execute_command)[:3] == [7, "0700", "0007"]


@pytest.mark.asyncio
async def test_number_set_cloud_waits_for_eventual_consistency() -> None:
    """Cloud write should tolerate delayed readback without unnecessary rewrites."""
    entry = DummyConfigEntry()
    coordinator = DummyCoordinator(
        {
            "device_info": {"device_id": "abc"},
            "system_status": {"online": True},
            "fields_by_key": {
                "target_hardness": {"value": 8.0},
                "hardness_unit": {"value": "dH"},
            },
        }
    )
    coordinator.api.execute_command = AsyncMock(
        side_effect=[
            {"status": "ok", "transport": "cloud"},  # write
            {"status": "ok", "fields": [{"key": "target_hardness", "value": 8.0}]},  # stale
            {"status": "ok", "fields": [{"key": "target_hardness", "value": 7.0}]},  # applied
        ]
    )
    entity = JudoiSoftTargetHardnessNumber(coordinator, entry)

    with patch("custom_components.judo_isoft.number.asyncio.sleep", new=AsyncMock()) as sleep_mock:
        await entity.async_set_native_value(7)

    assert _write_values(coordinator.api.execute_command) == [7]
    sleep_mock.assert_awaited_once()
