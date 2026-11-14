"""Shared coordinator entity helpers for writable Judo entities."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL


class JudoiSoftCommandEntity(CoordinatorEntity):
    """Shared coordinator-backed behavior for writable command entities."""

    def __init__(self, coordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self.config_entry = config_entry

    def _snapshot(self) -> dict[str, Any]:
        data = self.coordinator.data
        return data if isinstance(data, dict) else {}

    def _device_id(self) -> str:
        snapshot = self._snapshot()
        return str(snapshot.get("device_info", {}).get("device_id", "")).strip()

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        snapshot = self._snapshot()
        device_data = snapshot.get("device_info", {})
        system_data = snapshot.get("system_status", {})
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

    @property
    def available(self) -> bool:
        """Return whether entity is available."""
        snapshot = self._snapshot()
        return (
            self.coordinator.last_update_success
            and snapshot is not None
            and snapshot.get("system_status", {}).get("online", False)
        )

    async def _async_execute_command(
        self,
        *,
        command: int | str,
        value: Any | None = None,
        transport: str = "auto",
    ) -> dict[str, Any]:
        """Execute one command for this entity's device."""
        return await self.coordinator.api.execute_command(
            device_id=self._device_id(),
            command=command,
            value=value,
            transport=transport,
        )

    async def _async_execute_write(
        self,
        *,
        command: int | str,
        value: Any | None,
        error_prefix: str,
        transport: str = "auto",
    ) -> dict[str, Any]:
        """Execute one write command and raise a HA error on failure."""
        result = await self._async_execute_command(
            command=command,
            value=value,
            transport=transport,
        )
        if result.get("status") != "ok":
            raise HomeAssistantError(f"{error_prefix}: {result.get('error') or result}")
        return result
