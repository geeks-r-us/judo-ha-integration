"""The Judo iSoft integration."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import JudoiSoftAPI
from .judo_client.protocol.families.isoft import salt_level_pct
from .const import (
    ATTR_COMMAND,
    ATTR_DEVICE_ID,
    ATTR_TRANSPORT,
    ATTR_VALUE,
    CONF_HOST,
    CONF_PORT,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SERVICE_EXECUTE_COMMAND,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
]

SERVICE_SCHEMA_EXECUTE_COMMAND = vol.Schema(
    {
        vol.Optional(ATTR_DEVICE_ID, default=""): str,
        vol.Required(ATTR_COMMAND): vol.Any(int, str),
        vol.Optional(ATTR_VALUE): object,
        vol.Optional(ATTR_TRANSPORT, default="auto"): vol.In(
            ["auto", "local", "cloud"]
        ),
    }
)


def _force_cloud_mode(host: str | None, username: str | None, password: str | None) -> bool:
    """Return whether integration should operate in cloud-only mode."""
    if not (username and password):
        return False
    normalized_host = str(host or "").strip().lower()
    return normalized_host in {"", "cloud.device"}


def _inject_legacy_field_aliases(
    fields: list[dict[str, Any]], fields_by_key: dict[str, dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Inject compatibility aliases for legacy entity ids."""
    result_fields = list(fields)
    result_by_key = dict(fields_by_key)

    salt_field = result_by_key.get("salt_level_pct")
    salt_value = salt_field.get("value") if salt_field else None
    source_command = salt_field.get("source_command") if salt_field else 0x56

    if salt_value is None:
        salt_weight = result_by_key.get("salt_weight_g", {}).get("value")
        if isinstance(salt_weight, (int, float)):
            salt_value = salt_level_pct(int(salt_weight))

    if "judo_isoft_salt_level" not in result_by_key:
        legacy_salt = {
            "key": "judo_isoft_salt_level",
            "name": "Judo iSoft Salt Level (Estimated)",
            "value": salt_value,
            "unit": "%",
            "source_command": source_command,
        }
        result_fields.append(legacy_salt)
        result_by_key["judo_isoft_salt_level"] = legacy_salt

    return result_fields, result_by_key


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up integration services that are not bound to one entry."""
    await _async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Judo iSoft from a config entry."""
    host = entry.data.get(CONF_HOST, "cloud.device")
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)
    scan_interval = entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)
    force_cloud = _force_cloud_mode(host, username, password)

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
    except Exception as err:
        _LOGGER.error("Failed to connect to Judo iSoft system: %s", err)
        await api.close()
        raise ConfigEntryNotReady(f"Failed to connect to Judo iSoft: {err}") from err

    coordinator = JudoiSoftUpdateCoordinator(
        hass,
        entry,
        api=api,
        scan_interval=timedelta(seconds=scan_interval),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await _async_register_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        domain_data = hass.data.get(DOMAIN, {})
        coordinator: JudoiSoftUpdateCoordinator | None = domain_data.pop(
            entry.entry_id, None
        )
        if coordinator is not None:
            await coordinator.api.close()
        if DOMAIN in hass.data and not hass.data[DOMAIN]:
            _async_remove_services(hass)
            hass.data.pop(DOMAIN)

    return unload_ok


async def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services."""
    if hass.services.has_service(DOMAIN, SERVICE_EXECUTE_COMMAND):
        return

    async def handle_execute_command(call: ServiceCall) -> dict[str, Any]:
        coordinator = _coordinator_for_call(hass, call)
        if coordinator is None:
            raise HomeAssistantError("No loaded Judo iSoft configuration entry")

        device_id = call.data.get(ATTR_DEVICE_ID, "")
        command = call.data[ATTR_COMMAND]
        value = call.data.get(ATTR_VALUE)
        transport = call.data.get(ATTR_TRANSPORT, "auto")

        try:
            result = await coordinator.api.execute_command(
                device_id=device_id,
                command=command,
                value=value,
                transport=transport,
            )
        except Exception as err:
            _LOGGER.error("execute_command failed: %s", err)
            raise HomeAssistantError(f"execute_command failed: {err}") from err

        if result.get("status") != "ok":
            _LOGGER.error("execute_command failed: %s", result)
            raise HomeAssistantError(
                f"execute_command failed: {result.get('error') or result}"
            )

        if value is not None:
            await coordinator.async_request_refresh()

        return result

    hass.services.async_register(
        DOMAIN,
        SERVICE_EXECUTE_COMMAND,
        handle_execute_command,
        schema=SERVICE_SCHEMA_EXECUTE_COMMAND,
        supports_response=SupportsResponse.OPTIONAL,
    )


def _coordinator_for_call(
    hass: HomeAssistant, call: ServiceCall
) -> "JudoiSoftUpdateCoordinator | None":
    """Resolve coordinator for a service call."""
    domain_data = hass.data.get(DOMAIN)
    if not isinstance(domain_data, dict) or not domain_data:
        return None

    requested_id = str(call.data.get(ATTR_DEVICE_ID, "")).strip()
    if not requested_id:
        return next(iter(domain_data.values()))

    for coordinator in domain_data.values():
        device_info = coordinator.data.get("device_info", {}) if coordinator.data else {}
        known_ids = {
            str(device_info.get("device_id", "")).strip(),
            str(device_info.get("serial_number", "")).strip(),
        }
        if requested_id in known_ids:
            return coordinator

    return next(iter(domain_data.values()))


def _async_remove_services(hass: HomeAssistant) -> None:
    """Remove integration services."""
    if hass.services.has_service(DOMAIN, SERVICE_EXECUTE_COMMAND):
        hass.services.async_remove(DOMAIN, SERVICE_EXECUTE_COMMAND)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


class JudoiSoftUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: JudoiSoftAPI,
        scan_interval: timedelta,
    ) -> None:
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=scan_interval,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via API client."""
        try:
            async with asyncio.timeout(45):
                snapshot = await self.api.get_snapshot_data()
                fields_by_key = snapshot.get("fields_by_key", {})
                fields = snapshot.get("fields", [])
                fields, fields_by_key = _inject_legacy_field_aliases(
                    fields, fields_by_key
                )

                water_data = {
                    "hardness": fields_by_key.get("target_hardness", {}).get("value"),
                    "consumption": fields_by_key.get("water_total_l", {}).get("value"),
                    "flow_rate": fields_by_key.get("flow_lph", {}).get("value"),
                    "pressure": fields_by_key.get("pressure", {}).get("value"),
                    "temperature": fields_by_key.get("temperature", {}).get("value"),
                }
                maintenance_data = {
                    "salt_level": fields_by_key.get("salt_level_pct", {}).get("value"),
                    "filter_remaining": fields_by_key.get("salt_days_remaining", {}).get(
                        "value"
                    ),
                }
                health_data = await self.api.get_system_health()

                return {
                    "device_info": snapshot.get("device_info", {}),
                    "system_status": snapshot.get("system_status", {}),
                    "water_data": water_data,
                    "maintenance_data": maintenance_data,
                    "health": health_data,
                    "connection": {
                        "access_mode": self.api.connection_source,
                        "using_cloud": self.api.is_using_cloud,
                        "transport": snapshot.get("transport", "auto"),
                    },
                    "fields": fields,
                    "fields_by_key": fields_by_key,
                    "capabilities": snapshot.get("capabilities", []),
                    "updated_at": snapshot.get("updated_at"),
                }
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
