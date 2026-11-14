"""Config flow for Judo iSoft integration."""

from __future__ import annotations

import logging
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
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
from .const import (
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_USERNAME): str,
        vol.Optional(CONF_PASSWORD): str,
    }
)


def _force_cloud_mode(host: str | None, username: str | None, password: str | None) -> bool:
    """Return whether validation should use cloud-only mode."""
    if not (username and password):
        return False
    normalized_host = str(host or "").strip().lower()
    return normalized_host in {"", "cloud.device"}


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    host = data.get(CONF_HOST)
    port = data.get(CONF_PORT, DEFAULT_PORT)
    username = data.get(CONF_USERNAME)
    password = data.get(CONF_PASSWORD)

    force_cloud = _force_cloud_mode(host, username, password)

    if not force_cloud and not host:
        raise JudoiSoftConnectionError(
            "Host required for local access when not using cloud credentials"
        )

    if force_cloud:
        host = host or "cloud.device"
        if not data.get(CONF_HOST):
            data[CONF_HOST] = host

    api = JudoiSoftAPI(
        host,
        port,
        username=username,
        password=password,
        force_cloud=force_cloud,
    )

    try:
        if force_cloud:
            await api.test_cloud_only()
        else:
            await api.test_connection()

        device_info = await api.get_device_info()

        return {
            "title": f"Judo iSoft ({host if not force_cloud else 'Cloud'})",
            "serial_number": device_info.get("serial_number", "unknown"),
        }
    except JudoiSoftConnectionError:
        raise
    except Exception as err:
        raise JudoiSoftConnectionError(f"Setup failed: {str(err)}") from err
    finally:
        await api.close()


class JudoiSoftConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Judo iSoft."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input.get(CONF_USERNAME, "").strip()
            password = user_input.get(CONF_PASSWORD, "").strip()
            host = user_input.get(CONF_HOST, "").strip()

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

                    if (
                        "empty response" in error_msg
                        or "cloud service returned empty" in error_msg
                        or "no devices in cloud response" in error_msg
                    ):
                        errors["base"] = "cloud_service_empty_response"
                    elif (
                        "authentication failed" in error_msg
                        or "invalid token" in error_msg
                        or "unauthorized" in error_msg
                        or "forbidden" in error_msg
                    ):
                        errors["base"] = "invalid_auth"
                    elif "timeout" in error_msg:
                        errors["base"] = "timeout_connect"
                    elif "ssl" in error_msg or "certificate" in error_msg:
                        errors["base"] = "ssl_error"
                    elif (
                        "dns" in error_msg
                        or "name resolution" in error_msg
                        or "name or service not known" in error_msg
                        or "temporary failure in name resolution" in error_msg
                        or "nodename nor servname" in error_msg
                    ):
                        errors["base"] = "dns_error"
                    elif "cloud request failed" in error_msg:
                        errors["base"] = "cloud_unavailable"
                    else:
                        errors["base"] = "cannot_connect"
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
    ) -> "JudoiSoftOptionsFlow":
        """Create the options flow."""
        return JudoiSoftOptionsFlow()


class JudoiSoftOptionsFlow(config_entries.OptionsFlow):
    """Judo iSoft options flow."""

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
