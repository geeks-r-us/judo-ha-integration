"""Config flow for Judo iSoft integration."""

from __future__ import annotations

import logging
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .api import JudoiSoftAPI, JudoiSoftConnectionError
from .const import DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_HOST): str,  # Host is now optional for cloud-only devices
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_USERNAME): str,
        vol.Optional(CONF_PASSWORD): str,
    }
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=30, max=300)
        ),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    host = data.get(CONF_HOST)  # Host is now optional
    port = data.get(CONF_PORT, DEFAULT_PORT)
    username = data.get(CONF_USERNAME)
    password = data.get(CONF_PASSWORD)

    _LOGGER.info(
        "Validating connection - host: %s, port: %s, username: %s",
        host or "[cloud-only]",
        port,
        "***" if username else "None",
    )

    # Determine connection mode
    force_cloud = bool(username and password)

    if not force_cloud and not host:
        raise JudoiSoftConnectionError(
            "Host required for local access when not using cloud credentials"
        )

    if force_cloud:
        _LOGGER.info("Cloud-only mode detected (username/password provided)")
        # Use a placeholder host for cloud-only mode
        host = host or "cloud.device"

    _LOGGER.info("Connection mode: %s", "cloud-only" if force_cloud else "local-first")

    api = JudoiSoftAPI(
        host, port, username=username, password=password, force_cloud=force_cloud
    )

    try:
        if force_cloud:
            # Test cloud access directly for newer devices
            await api.test_cloud_only()
        else:
            # Normal test for older devices
            await api.test_connection()

        device_info = await api.get_device_info()

        return {
            "title": f"Judo iSoft ({host if not force_cloud else 'Cloud'})",
            "serial_number": device_info.get("serial_number", "unknown"),
        }
    except JudoiSoftConnectionError as err:
        _LOGGER.error("Connection validation failed: %s", err)
        raise
    except Exception as err:
        _LOGGER.error("Unexpected error during validation: %s", err, exc_info=True)
        # Convert generic exceptions to connection errors for better error handling
        raise JudoiSoftConnectionError(f"Setup failed: {str(err)}") from err
    finally:
        await api.close()


class JudoiSoftConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Judo iSoft."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate required fields based on connection type
            username = user_input.get(CONF_USERNAME, "").strip()
            password = user_input.get(CONF_PASSWORD, "").strip()
            host = user_input.get(CONF_HOST, "").strip()

            # Cloud mode: username + password required, host optional
            # Local mode: host required, username + password optional
            cloud_mode = bool(username and password)

            if not cloud_mode and not host:
                errors["base"] = "host_or_credentials_required"
            else:
                try:
                    info = await validate_input(self.hass, user_input)
                    return self.async_create_entry(title=info["title"], data=user_input)
                except JudoiSoftConnectionError as err:
                    error_msg = str(err).lower()
                    _LOGGER.warning("Connection error: %s", err)

                    # Map connection errors to appropriate user messages
                    if (
                        "empty response" in error_msg
                        or "cloud service returned empty" in error_msg
                    ):
                        errors["base"] = "cloud_service_empty_response"
                    elif "authentication failed" in error_msg:
                        if "judo" in error_msg or "cloud" in error_msg:
                            errors["base"] = "cloud_service_empty_response"
                        else:
                            errors["base"] = "invalid_auth"
                    elif "timeout" in error_msg:
                        errors["base"] = "timeout_connect"
                    elif "ssl" in error_msg or "certificate" in error_msg:
                        errors["base"] = "ssl_error"
                    elif "dns" in error_msg or "name resolution" in error_msg:
                        errors["base"] = "dns_error"
                    else:
                        errors["base"] = "cannot_connect"

                    _LOGGER.warning(
                        "Connection failed with error: %s (mapped to: %s)",
                        err,
                        errors["base"],
                    )
                except Exception as err:
                    _LOGGER.error("Unexpected setup error: %s", err, exc_info=True)
                    errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "default_port": str(DEFAULT_PORT),
            },
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> JudoiSoftOptionsFlow:
        """Create the options flow."""
        return JudoiSoftOptionsFlow(config_entry)


class JudoiSoftOptionsFlow(config_entries.OptionsFlow):
    """Judo iSoft options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=30, max=300)),
                }
            ),
        )
