"""Support for Judo iSoft binary sensors."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BINARY_SENSOR_TYPES, DOMAIN, MANUFACTURER, MODEL

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Judo iSoft binary sensor based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for sensor_type in BINARY_SENSOR_TYPES:
        entities.append(JudoiSoftBinarySensor(coordinator, entry, sensor_type))

    async_add_entities(entities)


class JudoiSoftBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a Judo iSoft binary sensor."""

    def __init__(
        self, coordinator, config_entry: ConfigEntry, sensor_type: str
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._sensor_type = sensor_type
        self._attr_name = f"{MODEL} {BINARY_SENSOR_TYPES[sensor_type]['name']}"
        self._attr_unique_id = f"{config_entry.entry_id}_{sensor_type}"
        self._attr_icon = BINARY_SENSOR_TYPES[sensor_type]["icon"]

        # Set device class if available
        if BINARY_SENSOR_TYPES[sensor_type]["device_class"]:
            self._attr_device_class = BinarySensorDeviceClass(
                BINARY_SENSOR_TYPES[sensor_type]["device_class"]
            )

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        device_data = self.coordinator.data.get("system_status", {})
        return {
            "identifiers": {(DOMAIN, self.config_entry.entry_id)},
            "name": f"{MANUFACTURER} {MODEL}",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": device_data.get("firmware_version"),
            "hw_version": device_data.get("hardware_version"),
            "serial_number": device_data.get("serial_number"),
        }

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if not self.coordinator.data:
            return None

        system_data = self.coordinator.data.get("system_status", {})
        maintenance_data = self.coordinator.data.get("maintenance_data", {})

        if self._sensor_type == "online":
            return system_data.get("online", False)
        elif self._sensor_type == "alarm":
            return system_data.get("alarm", False)
        elif self._sensor_type == "maintenance_required":
            return system_data.get("maintenance_required", False)
        elif self._sensor_type == "regeneration_active":
            return system_data.get("regeneration_active", False)
        elif self._sensor_type == "low_salt":
            salt_level = maintenance_data.get("salt_level", 100)
            return salt_level < 20  # Consider low if below 20%
        elif self._sensor_type == "filter_replacement":
            days_remaining = maintenance_data.get("filter_remaining", 365)
            return days_remaining <= 7  # Warning when 7 days or less remaining

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs = {}

        system_data = self.coordinator.data.get("system_status", {})

        # Add last update time if available
        if last_update := system_data.get("last_update"):
            attrs["last_update"] = last_update

        # Add error code for alarm sensor
        if self._sensor_type == "alarm":
            if error_code := system_data.get("error_code"):
                attrs["error_code"] = error_code

        # Add maintenance info for maintenance sensor
        if self._sensor_type == "maintenance_required":
            maintenance_data = self.coordinator.data.get("maintenance_data", {})
            if next_maintenance := maintenance_data.get("next_maintenance"):
                attrs["next_maintenance"] = next_maintenance

        return attrs

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # Online sensor should always be available to show connection status
        if self._sensor_type == "online":
            return (
                self.coordinator.last_update_success
                and self.coordinator.data is not None
            )

        # Other sensors require system to be online
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self.coordinator.data.get("system_status", {}).get("online", False)
        )
