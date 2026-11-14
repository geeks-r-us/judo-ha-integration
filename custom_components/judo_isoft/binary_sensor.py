"""Support for Judo iSoft binary sensors."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL


ONLINE_FIELD_KEY = "device_online"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Judo iSoft dynamic binary sensors from decoded snapshot fields."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[BinarySensorEntity] = []
    for field in coordinator.data.get("fields", []):
        if not isinstance(field.get("value"), bool):
            continue
        if field.get("key") == ONLINE_FIELD_KEY:
            continue
        entities.append(JudoiSoftDynamicBinarySensor(coordinator, entry, field))
    entities.append(JudoiSoftOnlineBinarySensor(coordinator, entry))
    async_add_entities(entities)


class _BaseBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Common binary sensor behavior."""

    def __init__(self, coordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self.config_entry = config_entry

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        device_data = self.coordinator.data.get("device_info", {})
        system_data = self.coordinator.data.get("system_status", {})
        return {
            "identifiers": {(DOMAIN, self.config_entry.entry_id)},
            "name": f"{MANUFACTURER} {device_data.get('model', MODEL)}",
            "manufacturer": device_data.get("manufacturer", MANUFACTURER),
            "model": device_data.get("model", MODEL),
            "sw_version": device_data.get("firmware_version")
            or system_data.get("firmware_version"),
            "hw_version": device_data.get("hardware_version")
            or system_data.get("hardware_version"),
            "serial_number": device_data.get("serial_number")
            or system_data.get("serial_number"),
        }


class JudoiSoftDynamicBinarySensor(_BaseBinarySensor):
    """Dynamic binary sensor for boolean decoded fields."""

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

        device_class = field.get("device_class")
        if device_class:
            try:
                self._attr_device_class = BinarySensorDeviceClass(device_class)
            except ValueError:
                self._attr_device_class = None

    @property
    def is_on(self) -> bool | None:
        """Return boolean state."""
        value = (
            self.coordinator.data.get("fields_by_key", {})
            .get(self._field_key, {})
            .get("value")
        )
        if value is None:
            return None
        return bool(value)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
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
            self.coordinator.last_update_success and self.coordinator.data is not None
        )


class JudoiSoftOnlineBinarySensor(_BaseBinarySensor):
    """Connectivity of the Judo device (cloud status or successful local read)."""

    _attr_name = "Online"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_online"

    @property
    def available(self) -> bool:
        """Always available: a failed update is reported as offline."""
        return True

    @property
    def is_on(self) -> bool:
        """Return whether the device is reachable."""
        if not self.coordinator.last_update_success or not self.coordinator.data:
            return False
        field = self.coordinator.data.get("fields_by_key", {}).get(ONLINE_FIELD_KEY, {})
        value = field.get("value")
        return True if value is None else bool(value)
