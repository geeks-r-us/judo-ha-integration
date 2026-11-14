"""Test the Judo iSoft integration setup."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.judo_isoft.const import DOMAIN, SERVICE_EXECUTE_COMMAND


@pytest.fixture
def config_entry_data():
    """Fixture for config entry data."""
    return {
        CONF_HOST: "192.168.1.100",
        CONF_PORT: 80,
    }


def _snapshot_fixture() -> dict:
    return {
        "fields": [
            {
                "key": "water_total_l",
                "name": "Water Total L",
                "value": 1057516,
                "unit": "L",
                "source_command": 0x28,
            },
            {
                "key": "alarm_active",
                "name": "Alarm Active",
                "value": False,
                "source_command": 0x43,
            },
        ],
        "fields_by_key": {
            "water_total_l": {"value": 1057516},
            "target_hardness": {"value": 6.0},
            "flow_lph": {"value": 0},
            "pressure": {"value": 3.2},
            "temperature": {"value": 12.3},
            "salt_level_pct": {"value": 80},
            "salt_days_remaining": {"value": 17},
        },
        "capabilities": [],
        "transport": "local",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "device_info": {
            "model": "iSoft",
            "serial_number": "123456",
            "manufacturer": "Judo Wasseraufbereitung GmbH",
        },
        "system_status": {"online": True},
    }


async def test_setup_entry_success(hass: HomeAssistant, config_entry_data):
    """Test successful setup of config entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Judo iSoft Test",
        data=config_entry_data,
    )
    config_entry.add_to_hass(hass)

    with patch("custom_components.judo_isoft.JudoiSoftAPI") as mock_api_class:
        mock_api_instance = mock_api_class.return_value
        mock_api_instance.test_connection = AsyncMock(return_value=True)
        mock_api_instance.get_snapshot_data = AsyncMock(return_value=_snapshot_fixture())
        mock_api_instance.get_system_health = AsyncMock(return_value={"overall_health": 95})
        mock_api_instance.close = AsyncMock(return_value=None)
        mock_api_instance.is_using_cloud = False
        mock_api_instance.connection_source = "local"

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert config_entry.state == ConfigEntryState.LOADED
    assert DOMAIN in hass.data
    assert hass.services.has_service(DOMAIN, SERVICE_EXECUTE_COMMAND)


async def test_setup_entry_connection_failed(hass: HomeAssistant, config_entry_data):
    """Test setup fails when connection test fails."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Judo iSoft Test",
        data=config_entry_data,
    )
    config_entry.add_to_hass(hass)

    with patch("custom_components.judo_isoft.JudoiSoftAPI") as mock_api_class:
        mock_api_instance = mock_api_class.return_value
        mock_api_instance.test_connection = AsyncMock(
            side_effect=Exception("Connection failed")
        )
        mock_api_instance.close = AsyncMock(return_value=None)

        assert not await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert config_entry.state == ConfigEntryState.SETUP_RETRY


async def test_unload_entry(hass: HomeAssistant, config_entry_data):
    """Test unloading a config entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Judo iSoft Test",
        data=config_entry_data,
    )
    config_entry.add_to_hass(hass)

    with patch("custom_components.judo_isoft.JudoiSoftAPI") as mock_api_class:
        mock_api_instance = mock_api_class.return_value
        mock_api_instance.test_connection = AsyncMock(return_value=True)
        mock_api_instance.get_snapshot_data = AsyncMock(return_value=_snapshot_fixture())
        mock_api_instance.get_system_health = AsyncMock(return_value={"overall_health": 95})
        mock_api_instance.close = AsyncMock(return_value=None)
        mock_api_instance.is_using_cloud = False
        mock_api_instance.connection_source = "local"

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        assert await hass.config_entries.async_unload(config_entry.entry_id)
        await hass.async_block_till_done()

    assert config_entry.state == ConfigEntryState.NOT_LOADED
    assert DOMAIN not in hass.data or not hass.data[DOMAIN]


async def test_setup_entry_with_host_and_credentials_uses_local_first(
    hass: HomeAssistant,
):
    """Credentials plus host should use local-first mode (not cloud-only)."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Judo iSoft Test",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_PORT: 80,
            CONF_USERNAME: "user",
            CONF_PASSWORD: "pass",
        },
    )
    config_entry.add_to_hass(hass)

    with patch("custom_components.judo_isoft.JudoiSoftAPI") as mock_api_class:
        mock_api_instance = mock_api_class.return_value
        mock_api_instance.test_connection = AsyncMock(return_value=True)
        mock_api_instance.test_cloud_only = AsyncMock(return_value=True)
        mock_api_instance.get_snapshot_data = AsyncMock(return_value=_snapshot_fixture())
        mock_api_instance.get_system_health = AsyncMock(return_value={"overall_health": 95})
        mock_api_instance.close = AsyncMock(return_value=None)
        mock_api_instance.is_using_cloud = False
        mock_api_instance.connection_source = "local"

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    mock_api_class.assert_called_once_with(
        "192.168.1.100",
        80,
        username="user",
        password="pass",
        force_cloud=False,
    )
    mock_api_instance.test_connection.assert_awaited_once()
    mock_api_instance.test_cloud_only.assert_not_awaited()


async def test_setup_entry_without_host_and_with_credentials_uses_cloud_only(
    hass: HomeAssistant,
):
    """Credentials without host should keep cloud-only mode."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Judo iSoft Cloud",
        data={
            CONF_USERNAME: "user",
            CONF_PASSWORD: "pass",
        },
    )
    config_entry.add_to_hass(hass)

    with patch("custom_components.judo_isoft.JudoiSoftAPI") as mock_api_class:
        mock_api_instance = mock_api_class.return_value
        mock_api_instance.test_connection = AsyncMock(return_value=True)
        mock_api_instance.test_cloud_only = AsyncMock(return_value=True)
        mock_api_instance.get_snapshot_data = AsyncMock(return_value=_snapshot_fixture())
        mock_api_instance.get_system_health = AsyncMock(return_value={"overall_health": 95})
        mock_api_instance.close = AsyncMock(return_value=None)
        mock_api_instance.is_using_cloud = True
        mock_api_instance.connection_source = "cloud"

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    mock_api_class.assert_called_once_with(
        "cloud.device",
        80,
        username="user",
        password="pass",
        force_cloud=True,
    )
    mock_api_instance.test_cloud_only.assert_awaited_once()
