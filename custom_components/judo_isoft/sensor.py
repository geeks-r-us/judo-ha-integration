"""Support for Judo iSoft sensors."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL, SENSOR_TYPES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Judo iSoft sensor based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for sensor_type in SENSOR_TYPES:
        entities.append(JudoiSoftSensor(coordinator, entry, sensor_type))

    async_add_entities(entities)


class JudoiSoftSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Judo iSoft sensor."""

    def __init__(
        self, coordinator, config_entry: ConfigEntry, sensor_type: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._sensor_type = sensor_type
        self._attr_name = f"{MODEL} {SENSOR_TYPES[sensor_type]['name']}"
        self._attr_unique_id = f"{config_entry.entry_id}_{sensor_type}"
        self._attr_icon = SENSOR_TYPES[sensor_type]["icon"]
        self._attr_native_unit_of_measurement = SENSOR_TYPES[sensor_type]["unit"]

        # Set device class if available
        if SENSOR_TYPES[sensor_type]["device_class"]:
            self._attr_device_class = SensorDeviceClass(
                SENSOR_TYPES[sensor_type]["device_class"]
            )

        # Set state class for numeric sensors
        if self._attr_native_unit_of_measurement:
            self._attr_state_class = SensorStateClass.MEASUREMENT

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
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None

        # Map sensor types to data sources
        if self._sensor_type == "water_hardness":
            return self.coordinator.data.get("water_data", {}).get("hardness")
        elif self._sensor_type == "water_consumption":
            return self.coordinator.data.get("water_data", {}).get("consumption")
        elif self._sensor_type == "salt_level":
            return self.coordinator.data.get("maintenance_data", {}).get("salt_level")
        elif self._sensor_type == "flow_rate":
            return self.coordinator.data.get("water_data", {}).get("flow_rate")
        elif self._sensor_type == "system_pressure":
            return self.coordinator.data.get("water_data", {}).get("pressure")
        elif self._sensor_type == "filter_remaining":
            return self.coordinator.data.get("maintenance_data", {}).get(
                "filter_remaining"
            )
        elif self._sensor_type == "system_health":
            health_data = self.coordinator.data.get("health", {})
            return health_data.get("overall_health")
        elif self._sensor_type == "error_code":
            return self.coordinator.data.get("system_status", {}).get("error_code")
        elif self._sensor_type == "last_regeneration":
            return self.coordinator.data.get("maintenance_data", {}).get(
                "last_regeneration"
            )
        elif self._sensor_type == "next_maintenance":
            return self.coordinator.data.get("maintenance_data", {}).get(
                "next_maintenance"
            )
        elif self._sensor_type == "connection_mode":
            return self.coordinator.data.get("connection", {}).get(
                "access_mode", "unknown"
            )

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs = {}

        # Add last update time if available
        system_data = self.coordinator.data.get("system_status", {})
        if last_update := system_data.get("last_update"):
            attrs["last_update"] = last_update

        # Add sensor-specific attributes
        if self._sensor_type == "water_consumption":
            maintenance_data = self.coordinator.data.get("maintenance_data", {})
            if last_regen := maintenance_data.get("last_regeneration"):
                attrs["last_regeneration"] = last_regen

        elif self._sensor_type == "filter_remaining":
            maintenance_data = self.coordinator.data.get("maintenance_data", {})
            if next_maintenance := maintenance_data.get("next_maintenance"):
                attrs["next_maintenance"] = next_maintenance

        return attrs

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self.coordinator.data.get("system_status", {}).get("online", False)
        )
