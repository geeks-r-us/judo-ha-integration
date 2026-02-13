"""Test the Judo iSoft integration setup."""

from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.judo_isoft.const import DOMAIN


@pytest.fixture
def config_entry_data():
    """Fixture for config entry data."""
    return {
        CONF_HOST: "192.168.1.100",
        CONF_PORT: 80,
    }


async def test_setup_entry_success(hass: HomeAssistant, config_entry_data, mock_api):
    """Test successful setup of config entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Judo iSoft Test",
        data=config_entry_data,
    )
    config_entry.add_to_hass(hass)

    with patch("custom_components.judo_isoft.api.JudoiSoftAPI") as mock_api_class:
        mock_api_instance = mock_api_class.return_value
        mock_api_instance.test_connection.return_value = True
        mock_api_instance.get_system_status.return_value = mock_api["system_status"]
        mock_api_instance.get_water_data.return_value = mock_api["water_data"]
        mock_api_instance.get_maintenance_data.return_value = mock_api[
            "maintenance_data"
        ]
        mock_api_instance.get_system_health.return_value = {"overall_health": 95}
        mock_api_instance.close.return_value = None
        mock_api_instance.is_using_cloud = False
        mock_api_instance.connection_source = "local"

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert config_entry.state == ConfigEntryState.LOADED
    assert DOMAIN in hass.data


async def test_setup_entry_connection_failed(hass: HomeAssistant, config_entry_data):
    """Test setup fails when connection test fails."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Judo iSoft Test",
        data=config_entry_data,
    )
    config_entry.add_to_hass(hass)

    with patch("custom_components.judo_isoft.api.JudoiSoftAPI") as mock_api_class:
        mock_api_instance = mock_api_class.return_value
        mock_api_instance.test_connection.side_effect = Exception("Connection failed")
        mock_api_instance.close.return_value = None

        assert not await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert config_entry.state == ConfigEntryState.SETUP_ERROR


async def test_unload_entry(hass: HomeAssistant, config_entry_data, mock_api):
    """Test unloading a config entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Judo iSoft Test",
        data=config_entry_data,
    )
    config_entry.add_to_hass(hass)

    with patch("custom_components.judo_isoft.api.JudoiSoftAPI") as mock_api_class:
        mock_api_instance = mock_api_class.return_value
        mock_api_instance.test_connection.return_value = True
        mock_api_instance.get_system_status.return_value = mock_api["system_status"]
        mock_api_instance.get_water_data.return_value = mock_api["water_data"]
        mock_api_instance.get_maintenance_data.return_value = mock_api[
            "maintenance_data"
        ]
        mock_api_instance.get_system_health.return_value = {"overall_health": 95}
        mock_api_instance.close.return_value = None
        mock_api_instance.is_using_cloud = False
        mock_api_instance.connection_source = "local"

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        assert await hass.config_entries.async_unload(config_entry.entry_id)
        await hass.async_block_till_done()

    assert config_entry.state == ConfigEntryState.NOT_LOADED
    assert DOMAIN not in hass.data or not hass.data[DOMAIN]
