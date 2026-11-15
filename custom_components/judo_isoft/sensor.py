"""Support for Judo iSoft sensors."""

from __future__ import annotations

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
from homeassistant.util import dt as dt_util

from .const import DOMAIN, MANUFACTURER, MODEL


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Judo iSoft dynamic sensors based on decoded snapshot fields."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []
    for field in coordinator.data.get("fields", []):
        if isinstance(field.get("value"), bool):
            continue
        entities.append(JudoiSoftDynamicSensor(coordinator, entry, field))
    async_add_entities(entities)


class _BaseSensor(CoordinatorEntity, SensorEntity):
    """Common behavior for sensor entities."""

    def __init__(self, coordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self.config_entry = config_entry

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        device_data = self.coordinator.data.get("device_info", {})
        system_data = self.coordinator.data.get("system_status", {})
        serial = (
            device_data.get("serial_number")
            or system_data.get("serial_number")
            or "Unknown"
        )
        model = device_data.get("model", MODEL)
        return {
            "identifiers": {(DOMAIN, self.config_entry.entry_id)},
            "name": f"{MANUFACTURER} {model}",
            "manufacturer": device_data.get("manufacturer", MANUFACTURER),
            "model": model,
            "sw_version": device_data.get("firmware_version")
            or system_data.get("firmware_version"),
            "hw_version": device_data.get("hardware_version")
            or system_data.get("hardware_version"),
            "serial_number": serial,
        }


class JudoiSoftDynamicSensor(_BaseSensor):
    """Dynamic sensor for decoded protocol fields."""

    def __init__(
        self, coordinator, config_entry: ConfigEntry, field: dict[str, Any]
    ) -> None:
        super().__init__(coordinator, config_entry)
        self._field_key = field["key"]
        self._source_command = field.get("source_command")
        self._attr_name = field.get("name") or self._field_key.replace("_", " ").title()
        self._attr_unique_id = (
            f"{config_entry.entry_id}_{config_entry.data.get('host', 'device')}_"
            f"{self._field_key}_{self._source_command}"
        )
        self._attr_icon = field.get("icon")
        self._attr_native_unit_of_measurement = field.get("unit")

        device_class = field.get("device_class")
        if device_class:
            try:
                self._attr_device_class = SensorDeviceClass(device_class)
            except ValueError:
                self._attr_device_class = None

        state_class = field.get("state_class")
        if state_class == "measurement":
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif state_class == "total_increasing":
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def native_value(self) -> Any:
        """Return state value from latest snapshot."""
        value = (
            self.coordinator.data.get("fields_by_key", {})
            .get(self._field_key, {})
            .get("value")
        )
        if self._attr_device_class == SensorDeviceClass.TIMESTAMP:
            return dt_util.parse_datetime(value) if isinstance(value, str) else None
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        field = self.coordinator.data.get("fields_by_key", {}).get(self._field_key, {})
        return {
            "source_command": field.get("source_command"),
            "raw_hex": field.get("raw_hex"),
            "transport": self.coordinator.data.get("connection", {}).get("transport"),
        }

    @property
    def available(self) -> bool:
        """Return whether entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self.coordinator.data.get("system_status", {}).get("online", False)
        )
