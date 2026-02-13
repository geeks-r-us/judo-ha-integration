"""Test the Judo iSoft config flow."""

from unittest.mock import patch

from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant

from custom_components.judo_isoft.const import DOMAIN


async def test_form_user_success(hass: HomeAssistant):
    """Test user config form with successful connection."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["errors"] == {}

    with patch(
        "custom_components.judo_isoft.config_flow.validate_input"
    ) as mock_validate:
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

    assert result2["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
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
        mock_validate.side_effect = Exception("Connection failed")

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_PORT: 80,
            },
        )

    assert result2["type"] == data_entry_flow.RESULT_TYPE_FORM
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

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"scan_interval": 120},
    )

    assert result2["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result2["data"] == {"scan_interval": 120}


class MockConfigEntry:
    """Mock config entry for testing."""

    def __init__(self, domain, title, data, entry_id="test"):
        """Initialize mock config entry."""
        self.domain = domain
        self.title = title
        self.data = data
        self.entry_id = entry_id
        self.options = {}

    def add_to_hass(self, hass):
        """Add to hass for testing."""
        pass
