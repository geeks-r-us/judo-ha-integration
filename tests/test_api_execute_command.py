"""Tests for generic execute_command API."""

from unittest.mock import AsyncMock, patch

import pytest

from custom_components.judo_isoft.api import JudoiSoftAPI
from custom_components.judo_isoft.judo_client.models import (
    CommandCapability,
    CommandDirection,
    CommandResult,
    DecodedCommandResult,
    DecodedField,
    DeviceDescriptor,
    DeviceFamily,
    DeviceSnapshot,
    TransportMode,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations():
    """Override global autouse fixture for pure unit tests."""
    yield


@pytest.mark.asyncio
async def test_execute_command_read() -> None:
    """Generic read command should return decoded field payload."""
    api = JudoiSoftAPI(
        host="cloud.device",
        username="user",
        password="pass",
        force_cloud=True,
    )

    descriptor = DeviceDescriptor(device_id="123", family=DeviceFamily.ISOFT)
    decoded = DecodedCommandResult(
        command_id=0x28,
        fields=[
            DecodedField(
                key="water_total_l",
                value=1057516,
                name="Water Total L",
                source_command=0x28,
                unit="L",
            )
        ],
        raw_hex="EC221000",
    )

    with patch.object(
        api._client, "discover_devices", new=AsyncMock(return_value=[descriptor])
    ):
        with patch.object(
            api._client, "read_command", new=AsyncMock(return_value=decoded)
        ):
            result = await api.execute_command("", "28", None, "cloud")

    assert result["status"] == "ok"
    assert result["command_id"] == 0x28
    assert result["command_hex"] == "28"
    assert result["fields"][0]["key"] == "water_total_l"
    assert "raw_response" in result

    await api.close()


@pytest.mark.asyncio
async def test_execute_command_write() -> None:
    """Generic write command should return command result."""
    api = JudoiSoftAPI(
        host="cloud.device",
        username="user",
        password="pass",
        force_cloud=True,
    )

    descriptor = DeviceDescriptor(device_id="123", family=DeviceFamily.ISOFT)
    command_result = CommandResult(
        command_id=0x30,
        transport=TransportMode.CLOUD,
        status="ok",
        raw={"status": "ok"},
    )

    with patch.object(
        api._client, "discover_devices", new=AsyncMock(return_value=[descriptor])
    ):
        with patch.object(
            api._client, "write_command", new=AsyncMock(return_value=command_result)
        ):
            result = await api.execute_command("", "30", 8, "cloud")

    assert result["status"] == "ok"
    assert result["command_id"] == 0x30
    assert result["command_hex"] == "30"
    assert result["transport"] == "cloud"

    await api.close()


@pytest.mark.asyncio
async def test_get_snapshot_data_includes_capability_metadata() -> None:
    """Snapshot capabilities should include payload metadata for HA platforms."""
    api = JudoiSoftAPI(host="127.0.0.1")
    descriptor = DeviceDescriptor(device_id="123", family=DeviceFamily.ISOFT)
    snapshot = DeviceSnapshot(
        device=descriptor,
        fields=[],
        updated_at="2026-02-26T00:00:00+00:00",
        transport=TransportMode.LOCAL,
        capabilities=[
            CommandCapability(
                command_id=0x35,
                name="Start Regeneration",
                direction=CommandDirection.WRITE,
                payload_length=1,
                default_write_value=0,
            )
        ],
        raw={},
    )

    with patch.object(
        api._client, "discover_devices", new=AsyncMock(return_value=[descriptor])
    ):
        with patch.object(
            api._client, "read_snapshot", new=AsyncMock(return_value=snapshot)
        ):
            result = await api.get_snapshot_data()

    capabilities = result["capabilities"]
    assert len(capabilities) == 1
    assert capabilities[0]["command_id"] == 0x35
    assert capabilities[0]["payload_length"] == 1
    assert capabilities[0]["default_write_value"] == 0

    await api.close()
