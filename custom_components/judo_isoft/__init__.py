"""The Judo iSoft integration."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import JudoiSoftAPI, JudoiSoftCommandError
from .const import (
    ATTR_FLOW_RATE,
    ATTR_SALT_LEVEL,
    ATTR_WATER_HARDNESS,
    CONF_HOST,
    CONF_PORT,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SERVICE_CLEAR_ALARM,
    SERVICE_CLEAR_MAINTENANCE,
    SERVICE_RESET_SYSTEM,
    SERVICE_SET_FLOW_RATE,
    SERVICE_SET_SALT_LEVEL,
    SERVICE_SET_WATER_HARDNESS,
    SERVICE_START_REGENERATION,
    SERVICE_STOP_REGENERATION,
    SERVICE_TRIGGER_MAINTENANCE,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Judo iSoft from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)
    scan_interval = entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)

    # Initialize the API client
    api = JudoiSoftAPI(host, port, username=username, password=password)

    # Test connection
    try:
        await api.test_connection()
    except Exception as err:
        _LOGGER.error("Failed to connect to Judo iSoft system: %s", err)
        return False

    # Create update coordinator
    coordinator = JudoiSoftUpdateCoordinator(
        hass,
        api=api,
        scan_interval=timedelta(seconds=scan_interval),
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator in hass data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    await _async_register_services(hass, coordinator)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Unregister services if this is the last entry
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            _async_remove_services(hass)
            hass.data.pop(DOMAIN)

    return unload_ok


# Service schemas
SERVICE_SCHEMA_SALT_LEVEL = vol.Schema(
    {
        vol.Required(ATTR_SALT_LEVEL): vol.Coerce(float),
    }
)

SERVICE_SCHEMA_FLOW_RATE = vol.Schema(
    {
        vol.Required(ATTR_FLOW_RATE): vol.Coerce(float),
    }
)

SERVICE_SCHEMA_WATER_HARDNESS = vol.Schema(
    {
        vol.Required(ATTR_WATER_HARDNESS): vol.Coerce(float),
    }
)


async def _async_register_services(
    hass: HomeAssistant, coordinator: JudoiSoftUpdateCoordinator
) -> None:
    """Register services for the Judo iSoft integration."""

    # Simple services (no parameters)
    async def handle_simple_service(call: ServiceCall, command: str) -> None:
        """Handle simple service calls."""
        try:
            if command == "start_regeneration":
                success = await coordinator.api.start_regeneration()
            elif command == "stop_regeneration":
                success = await coordinator.api.stop_regeneration()
            elif command == "clear_alarm":
                success = await coordinator.api.clear_alarm()
            elif command == "trigger_maintenance":
                success = await coordinator.api.trigger_maintenance()
            elif command == "clear_maintenance":
                success = await coordinator.api.clear_maintenance()
            elif command == "reset_system":
                success = await coordinator.api.reset_system()
            else:
                _LOGGER.error("Unknown service command: %s", command)
                return

            if success:
                _LOGGER.info("Successfully executed service: %s", command)
                # Trigger coordinator refresh to update states
                await coordinator.async_request_refresh()
            else:
                _LOGGER.error("Failed to execute service: %s", command)

        except JudoiSoftCommandError as err:
            _LOGGER.error("Service %s failed: %s", command, err)
        except Exception as err:
            _LOGGER.error("Unexpected error in service %s: %s", command, err)

    # Service with salt level parameter
    async def handle_set_salt_level(call: ServiceCall) -> None:
        """Handle set salt level service."""
        salt_level = call.data[ATTR_SALT_LEVEL]
        try:
            success = await coordinator.api.set_salt_level(salt_level)
            if success:
                _LOGGER.info("Successfully set salt level to %s%%", salt_level)
                await coordinator.async_request_refresh()
            else:
                _LOGGER.error("Failed to set salt level")
        except (JudoiSoftCommandError, ValueError) as err:
            _LOGGER.error("Failed to set salt level: %s", err)

    # Service with flow rate parameter
    async def handle_set_flow_rate(call: ServiceCall) -> None:
        """Handle set flow rate service."""
        flow_rate = call.data[ATTR_FLOW_RATE]
        try:
            success = await coordinator.api.set_flow_rate(flow_rate)
            if success:
                _LOGGER.info("Successfully set flow rate to %s L/min", flow_rate)
                await coordinator.async_request_refresh()
            else:
                _LOGGER.error("Failed to set flow rate")
        except (JudoiSoftCommandError, ValueError) as err:
            _LOGGER.error("Failed to set flow rate: %s", err)

    # Service with water hardness parameter
    async def handle_set_water_hardness(call: ServiceCall) -> None:
        """Handle set water hardness service."""
        water_hardness = call.data[ATTR_WATER_HARDNESS]
        try:
            success = await coordinator.api.set_water_hardness(water_hardness)
            if success:
                _LOGGER.info(
                    "Successfully set water hardness to %s °dH", water_hardness
                )
                await coordinator.async_request_refresh()
            else:
                _LOGGER.error("Failed to set water hardness")
        except (JudoiSoftCommandError, ValueError) as err:
            _LOGGER.error("Failed to set water hardness: %s", err)

    # Register all services
    hass.services.async_register(
        DOMAIN,
        SERVICE_START_REGENERATION,
        lambda call: handle_simple_service(call, "start_regeneration"),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_STOP_REGENERATION,
        lambda call: handle_simple_service(call, "stop_regeneration"),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_ALARM,
        lambda call: handle_simple_service(call, "clear_alarm"),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_TRIGGER_MAINTENANCE,
        lambda call: handle_simple_service(call, "trigger_maintenance"),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_MAINTENANCE,
        lambda call: handle_simple_service(call, "clear_maintenance"),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESET_SYSTEM,
        lambda call: handle_simple_service(call, "reset_system"),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SALT_LEVEL,
        handle_set_salt_level,
        schema=SERVICE_SCHEMA_SALT_LEVEL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_FLOW_RATE,
        handle_set_flow_rate,
        schema=SERVICE_SCHEMA_FLOW_RATE,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_WATER_HARDNESS,
        handle_set_water_hardness,
        schema=SERVICE_SCHEMA_WATER_HARDNESS,
    )

    _LOGGER.info("Registered %s services for Judo iSoft integration", 9)


def _async_remove_services(hass: HomeAssistant) -> None:
    """Remove services for the Judo iSoft integration."""
    services = [
        SERVICE_START_REGENERATION,
        SERVICE_STOP_REGENERATION,
        SERVICE_CLEAR_ALARM,
        SERVICE_TRIGGER_MAINTENANCE,
        SERVICE_CLEAR_MAINTENANCE,
        SERVICE_RESET_SYSTEM,
        SERVICE_SET_SALT_LEVEL,
        SERVICE_SET_FLOW_RATE,
        SERVICE_SET_WATER_HARDNESS,
    ]

    for service in services:
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)

    _LOGGER.info("Removed Judo iSoft services")


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


class JudoiSoftUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: JudoiSoftAPI,
        scan_interval: timedelta,
    ) -> None:
        """Initialize."""
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=scan_interval,
        )

    async def _async_update_data(self) -> dict:
        """Update data via library."""
        try:
            async with asyncio.timeout(30):
                # Fetch data from the API
                system_status = await self.api.get_system_status()
                water_data = await self.api.get_water_data()
                maintenance_data = await self.api.get_maintenance_data()

                # Get system health if available
                try:
                    health_data = await self.api.get_system_health()
                except Exception:
                    # Health data is optional, don't fail if not available
                    health_data = {}

                # Add connection information
                connection_info = {
                    "access_mode": self.api.connection_source,
                    "using_cloud": self.api.is_using_cloud,
                }

                return {
                    "system_status": system_status,
                    "water_data": water_data,
                    "maintenance_data": maintenance_data,
                    "health": health_data,
                    "connection": connection_info,
                }
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
