"""Test the Judo iSoft config flow."""

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.judo_isoft.api import JudoiSoftConnectionError
from custom_components.judo_isoft.config_flow import validate_input
from custom_components.judo_isoft.const import DOMAIN


async def test_form_user_success(hass: HomeAssistant):
    """Test user config form with successful connection."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "custom_components.judo_isoft.config_flow.validate_input"
    ) as mock_validate, patch(
        "custom_components.judo_isoft.async_setup_entry", return_value=True
    ):
        mock_validate.return_value = {
            "title": "Judo iSoft (192.168.1.100)",
            "serial_number": "12345678",
        }

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_PORT: 80,
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Judo iSoft (192.168.1.100)"
    assert result2["data"] == {
        CONF_HOST: "192.168.1.100",
        CONF_PORT: 80,
    }


async def test_form_user_connection_error(hass: HomeAssistant):
    """Test user config form with connection error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.judo_isoft.config_flow.validate_input"
    ) as mock_validate:
        mock_validate.side_effect = JudoiSoftConnectionError("Connection failed")

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_PORT: 80,
            },
        )

    assert result2["type"] == data_entry_flow.FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_options_flow(hass: HomeAssistant):
    """Test options flow."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Judo iSoft Test",
        data={CONF_HOST: "192.168.1.100", CONF_PORT: 80},
    )
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"scan_interval": 120},
    )

    assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result2["data"] == {"scan_interval": 120}


async def test_validate_input_host_and_credentials_uses_local_first(
    hass: HomeAssistant,
):
    """Validation should not force cloud-only when host is provided."""
    with patch("custom_components.judo_isoft.config_flow.JudoiSoftAPI") as mock_api_class:
        api = mock_api_class.return_value
        api.test_connection = AsyncMock(return_value=True)
        api.test_cloud_only = AsyncMock(return_value=True)
        api.get_device_info = AsyncMock(return_value={"serial_number": "123"})
        api.close = AsyncMock(return_value=None)

        result = await validate_input(
            hass,
            {
                CONF_HOST: "192.168.1.100",
                CONF_PORT: 80,
                CONF_USERNAME: "user",
                CONF_PASSWORD: "pass",
            },
        )

    assert result["title"] == "Judo iSoft (192.168.1.100)"
    mock_api_class.assert_called_once_with(
        "192.168.1.100",
        80,
        username="user",
        password="pass",
        force_cloud=False,
    )
    api.test_connection.assert_awaited_once()
    api.test_cloud_only.assert_not_awaited()
